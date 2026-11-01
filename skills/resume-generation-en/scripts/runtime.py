"""Offline document mechanics. Selection and writing are supplied by Codex/human."""
import argparse,datetime,hashlib,importlib.metadata,json,os,platform,shutil,subprocess,sys,tempfile,time
from pathlib import Path
import onepage as w
import review_rules

GUARD_COUNTS={'blocked_python_network_events':0}

class WorkflowError(ValueError): pass

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,x):w.save(p,x)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def inside(p,root):
    p=Path(p).resolve()
    if not p.is_relative_to(root):raise WorkflowError('output must stay inside configured workdir')
    return p

def validate_workdir(c):
    # Resolve both real paths before any output or input copy, including direct callers.
    install=Path(__file__).resolve().parent.parent
    configured=Path(c['workdir'])
    if not configured.is_absolute():raise WorkflowError('workdir must be an explicit absolute local path')
    root=configured.resolve()
    if root==install or root.is_relative_to(install) or install.is_relative_to(root):
        raise WorkflowError('workdir and skill installation must be separate real directories; neither may contain the other')
    c['workdir']=str(root)
    return root

def configuration(path):
    c=load(path)
    required=('workdir','renderer','fontconfig_file','fonts')
    for k in required:
        if not c.get(k):raise WorkflowError('missing runtime configuration: '+k)
    for k in ('workdir','renderer','fontconfig_file'):
        if not Path(c[k]).is_absolute():raise WorkflowError(k+' must be an explicit absolute local path')
    if not isinstance(c['fonts'],dict):raise WorkflowError('fonts must be an explicit object with regular, bold and wingdings paths')
    validate_workdir(c)
    return c

def environment(c,profile):
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','HOME':str(profile),'SAL_USE_VCLPLUGIN':'svp','SAL_DISABLE_OPENCL':'1','SAL_DISABLE_SKIA':'1','FONTCONFIG_FILE':c['fontconfig_file'],'XDG_CONFIG_HOME':str(profile/'config'),'XDG_CACHE_HOME':str(profile/'cache'),'XDG_RUNTIME_DIR':str(profile/'runtime'),'TMPDIR':str(profile)}
    for k in ('config','cache','runtime'): (profile/k).mkdir(exist_ok=True,mode=0o700)
    libs=c.get('renderer_library_dirs',[])
    if libs:
        if any(not Path(p).is_absolute() or not Path(p).is_dir() for p in libs):raise WorkflowError('renderer_library_dirs must contain existing absolute directories')
        env['LD_LIBRARY_PATH']=os.pathsep.join(libs)
    return env

def checked_run(cmd,env,cwd,timeout=20):
    return subprocess.run(cmd,env=env,cwd=cwd,capture_output=True,text=True,timeout=timeout)

def preflight(c):
    root=validate_workdir(c)
    root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root,prefix='.preflight-') as temp:
        profile=Path(temp);env=environment(c,profile)
        renderer=Path(c['renderer'])
        if not renderer.is_file() or not os.access(renderer,os.X_OK):raise WorkflowError('renderer missing or not executable: configure LibreOffice soffice')
        if not Path(c['fontconfig_file']).is_file():raise WorkflowError('fontconfig_file missing; provide an explicit font configuration')
        fc=shutil.which('fc-match',path=env['PATH'])
        if not fc:raise WorkflowError('fontconfig fc-match is required')
        matched={}
        for key,query in (('regular','Times New Roman:style=Regular'),('bold','Times New Roman:style=Bold'),('wingdings','Wingdings:style=Regular')):
            configured=Path(c['fonts'].get(key) or '')
            if not configured.is_absolute() or not configured.is_file():raise WorkflowError('missing required font file: '+key+'; substitution is forbidden')
            r=checked_run([fc,'-f','%{file}\n%{family}\n%{style}\n',query],env,profile)
            lines=r.stdout.splitlines()
            if r.returncode or len(lines)<3 or Path(lines[0]).resolve()!=configured.resolve():raise WorkflowError('font resolution mismatch for '+key+'; substitution is forbidden')
            expected='Wingdings' if key=='wingdings' else 'Times New Roman'
            if expected not in lines[1].split(','):raise WorkflowError('wrong font family for '+key)
            matched[key]={'family':lines[1],'style':lines[2],'sha256':digest(configured)}
        r=checked_run([str(renderer),'--headless','--version'],env,profile)
        if r.returncode or 'LibreOffice' not in r.stdout:raise WorkflowError('renderer version probe failed: '+r.stderr.strip())
        renderer_version=r.stdout.strip()
    w.configure_fonts(c['fonts']['regular'],c['fonts']['bold'])
    return {'observed_os':platform.platform(),'python':sys.version,'dependencies':{k:importlib.metadata.version(k) for k in ('python-docx','lxml','PyMuPDF','Pillow')},'renderer':renderer_version,'resolved_fonts':matched,'workdir_write_probe':True,'network_policy_declaration':'offline; Python socket audit hook only, not OS or subprocess network isolation','blocked_python_network_events_so_far':GUARD_COUNTS['blocked_python_network_events'],'native_word_verified':False,'cross_engine_verified':False,'ats_verified':False}


def render_identity(c,evidence):
    return {'runtime_config_sha256':hashlib.sha256(w.canon(c)).hexdigest(),
            'renderer_sha256':digest(c['renderer']),'renderer_version':evidence['renderer'],
            'fontconfig_sha256':digest(c['fontconfig_file']),'resolved_fonts':evidence['resolved_fonts'],
            'template_sha256':digest(Path(__file__).resolve().parent.parent/'assets/blank-english-template.docx'),
            'mechanics_sha256':{p.name:digest(p) for p in (Path(__file__),Path(w.__file__),Path(w.style.__file__))}}

def verify_embedded_fonts(folder,evidence):
    """Inspect actual embedded font programs, not just PDF base-font labels."""
    fonts=[]
    with w.fitz.open(folder/'resume.pdf') as pdf:
        for xref in sorted({f[0] for page in pdf for f in page.get_fonts(full=True)}):
            name,extension,kind,data=pdf.extract_font(xref)
            record={'xref':xref,'base_font':name,'extension':extension,'type':kind,
                    'embedded_bytes':len(data),'embedded_sha256':hashlib.sha256(data).hexdigest() if data else None}
            fonts.append(record)
    result={'pdf_base_fonts':sorted({f['base_font'] for f in fonts}),'embedded_fonts':fonts,
            'resolved_font_files':evidence['resolved_fonts'],'substitution_allowed':False,
            'validation_passed':bool(fonts) and all(f['embedded_bytes']>0 and any(n in f['base_font'] for n in ('TimesNewRoman','Wingdings')) for f in fonts)}
    write(folder/'font-evidence.json',result)
    if not result['validation_passed']:raise WorkflowError('unexpected or nonembedded PDF font; correct runtime and retry within bound')
    return result

def accepted_render(latest,c,evidence):
    """A measurement alone (including legacy results) never authorizes progression."""
    root=validate_workdir(c);latest=inside(latest,root)
    path=latest/'accepted-render.json'
    if not path.is_file():raise WorkflowError('current version has no accepted render; inspect render attempts and retry within bound')
    receipt=load(path)
    if receipt.get('schema')!='accepted-render-v1' or receipt.get('identity')!=render_identity(c,evidence):raise WorkflowError('accepted render identity is stale; restore original verified configuration; do not reset attempts')
    folder=inside(latest/receipt['attempt_directory'],latest)
    if folder.parent!=latest or not folder.name.startswith('render-attempt-'):raise WorkflowError('invalid accepted render attempt path')
    files=receipt.get('files',{})
    required={'resume.docx','resume.pdf','content.json','resume.txt','measurement.json','font-evidence.json','result.json'}
    if not required.issubset(files):raise WorkflowError('accepted render receipt is incomplete')
    for name,sha in files.items():
        file=inside(folder/name,folder)
        if not file.is_file() or digest(file)!=sha:raise WorkflowError('accepted render artifact changed: '+name)
    for name in ('resume.docx','content.json','resume.txt'):
        if digest(latest/name)!=files[name]:raise WorkflowError('accepted render does not match current version: '+name)
    result=load(folder/'result.json');m=load(folder/'measurement.json');fonts=load(folder/'font-evidence.json')
    if result.get('status')!='accepted' or result.get('returncode')!=0 or fonts.get('validation_passed') is not True or not m.get('all_content_words_preserved') or not m.get('style_unchanged'):raise WorkflowError('accepted render evidence failed validation')
    return folder

def render_version(latest,c,evidence):
    root=validate_workdir(c);latest=inside(latest,root)
    if (latest/'accepted-render.json').exists():return accepted_render(latest,c,evidence),True
    # Legacy receipts consume their original slots; abandoned directories also count.
    numbers=[]
    for path in latest.glob('render-attempt-*'):
        try:numbers.append(int(path.name.removeprefix('render-attempt-').removesuffix('.json')))
        except ValueError:raise WorkflowError('unrecognized render attempt; preserve and inspect manually')
    attempt=max(numbers,default=0)+1
    if attempt>3:raise WorkflowError('initial attempt plus two local recoveries exhausted; preserve incomplete draft and failure evidence')
    folder=latest/('render-attempt-%02d'%attempt);folder.mkdir(exist_ok=False)
    receipt={'attempt':attempt,'utc':utc(),'status':'running','version':str(latest.relative_to(root)),
             'identity':render_identity(c,evidence),'unique_profile':True,'environment_inherited':False}
    write(folder/'started.json',receipt)
    try:
        for name in ('resume.docx','content.json','resume.txt','style-check.json'):shutil.copy2(latest/name,folder/name)
        with tempfile.TemporaryDirectory(dir=root,prefix='.renderer-profile-') as p:
            profile=Path(p);env=environment(c,profile)
            cmd=[c['renderer'],'--headless','--norestore','--nodefault','--nologo','-env:UserInstallation='+profile.as_uri(),'--convert-to','pdf:writer_pdf_Export','--outdir',str(folder),str(folder/'resume.docx')]
            r=checked_run(cmd,env,profile,60)
            receipt.update({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        if r.returncode!=0 or not (folder/'resume.pdf').is_file():raise WorkflowError('local renderer failed or produced no PDF')
        m=w.measure(folder)
        verify_embedded_fonts(folder,evidence)
        if not m['all_content_words_preserved'] or not m['style_unchanged']:raise WorkflowError('measurement mapping/style validation failed')
        receipt.update({'status':'accepted','completed_utc':utc()});write(folder/'result.json',receipt)
        files={p.name:digest(p) for p in folder.iterdir() if p.is_file()}
        write(latest/'accepted-render.json',{'schema':'accepted-render-v1','accepted_utc':utc(),
              'attempt_directory':folder.name,'identity':receipt['identity'],'files':files})
    except Exception as exc:
        if not (folder/'result.json').exists():
            receipt.update({'status':'failed','completed_utc':utc(),'error_type':type(exc).__name__,'message':str(exc)})
            if isinstance(exc,subprocess.TimeoutExpired):
                receipt.update({'timeout_seconds':exc.timeout,'stdout':str(exc.stdout or ''),'stderr':str(exc.stderr or '')})
            write(folder/'result.json',receipt)
        raise WorkflowError('render attempt '+str(attempt)+' failed; evidence: '+str(folder.relative_to(root))+'; '+str(exc)) from exc
    return accepted_render(latest,c,evidence),False

def recovery_status(root,state,c,evidence):
    result={'frozen':state['frozen'],'semantic_passes_used':state['semantic_passes'],'semantic_passes_limit':4,
            'complete':state['frozen'],'note':'Incomplete drafts and overflow remain recoverable only within the same finite limits.'}
    if state['versions']:
        latest=inside(root/state['versions'][-1]['directory'],root)
        result['version']=str(latest.relative_to(root))
        result['attempt_evidence']=[str(p.relative_to(root)) for p in sorted(latest.glob('render-attempt-*'))]
        try:
            accepted=accepted_render(latest,c,evidence);m=load(accepted/'measurement.json')
            result.update({'accepted_render':str((latest/'accepted-render.json').relative_to(root)),
                           'one_page':m['pages']==1,'body_bounds_ok':not any(p['outside_body_words'] for p in m['pages_detail'])})
        except (WorkflowError,OSError,KeyError,ValueError) as exc:result['render_blocker']=str(exc)
    return result

def source_check(root,state):
    if digest(root/'input.json')!=state['source_sha256']:raise WorkflowError('input changed; resume this task with its original input or create a new workdir')

def citations(analysis,source):
    """Check literal spans and reference integrity, never semantic entailment."""
    if not isinstance(analysis,dict) or analysis.get('editor')!='Codex-assisted semantic editing':raise WorkflowError('analysis must declare Codex-assisted semantic editing')
    for key in ('facts','selection','questions','claim_map'):
        if not isinstance(analysis.get(key),list) or any(not isinstance(x,dict) for x in analysis[key]):raise WorkflowError('analysis '+key+' must be a list of objects')
    ids=[]
    for fact in analysis['facts']:
        value=fact.get('id')
        if not isinstance(value,str) or not value.strip():raise WorkflowError('fact ID must be a nonempty string')
        ids.append(value)
    if len(ids)!=len(set(ids)):raise WorkflowError('duplicate fact IDs')
    known=set(ids)
    def references(item,key,where,allow_empty=False):
        refs=item.get(key)
        if not isinstance(refs,list) or any(not isinstance(i,str) or not i.strip() for i in refs):raise WorkflowError(where+'.'+key+' must be a list of fact ID strings')
        if not refs and not allow_empty:raise WorkflowError(where+'.'+key+' must name at least one fact')
        missing=[i for i in refs if i not in known]
        if missing:raise WorkflowError(where+'.'+key+' refers to missing facts: '+', '.join(missing))
    for fact in analysis['facts']:
        fragments=fact.get('source_fragments')
        if not isinstance(fragments,list) or not fragments or any(not isinstance(f,dict) for f in fragments):raise WorkflowError('fact lacks source fragments')
        for f in fragments:
            if f.get('field')!='material_text' or type(f.get('start')) is not int or type(f.get('end')) is not int or f['start']<0 or f['end']<=f['start'] or f['end']>len(source['material_text']) or source['material_text'][f['start']:f['end']]!=f.get('quote'):raise WorkflowError('fact citation mismatch')
    for index,item in enumerate(analysis['selection']):references(item,'fact_ids','selection['+str(index)+']')
    for index,item in enumerate(analysis['questions']):
        if 'affected_facts' in item:raise WorkflowError('questions['+str(index)+'].affected_facts is legacy; use affected_fact_ids')
        references(item,'affected_fact_ids','questions['+str(index)+']',allow_empty=True)
    for index,item in enumerate(analysis['claim_map']):references(item,'fact_ids','claim_map['+str(index)+']')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--config',required=True)
    sub=ap.add_subparsers(dest='mode',required=True)
    sub.add_parser('preflight');sub.add_parser('status')
    q=sub.add_parser('init');q.add_argument('input')
    q=sub.add_parser('first');q.add_argument('draft');q.add_argument('--analysis',required=True)
    sub.add_parser('structure')
    q=sub.add_parser('edit');q.add_argument('decision')
    sub.add_parser('render')
    q=sub.add_parser('freeze');q.add_argument('--review',required=True)
    a=ap.parse_args();c=configuration(a.config);root=Path(c['workdir'])
    evidence=preflight(c)
    if a.mode=='preflight':print(json.dumps(evidence,indent=2));return
    if a.mode=='init':
        if (root/'state.json').exists():raise WorkflowError('already initialized; use status to resume')
        source=load(a.input)
        if not isinstance(source.get('synthetic'),bool):raise WorkflowError('input must explicitly declare synthetic true or false')
        for k in ('material_text','jd_text','target_role'):
            if not isinstance(source.get(k),str) or not source[k].strip():raise WorkflowError('input missing '+k)
        write(root/'input.json',source);write(root/'preflight.json',evidence)
        write(root/'state.json',{'created_utc':utc(),'started_monotonic':time.monotonic(),'source_sha256':digest(root/'input.json'),'versions':[],'semantic_passes':0,'frozen':False});print('initialized');return
    state=load(root/'state.json');source_check(root,state)
    if a.mode=='status':print(json.dumps({'state':state,'recovery':recovery_status(root,state,c,evidence)},indent=2));return
    if state['frozen']:raise WorkflowError('delivery frozen; create another workdir for a new task')
    versions=state['versions'];latest=inside(root/versions[-1]['directory'],root) if versions else None
    accepted=accepted_render(latest,c,evidence) if latest and a.mode in ('structure','edit','freeze') else None
    if a.mode in ('first','structure','edit'):
        if a.mode=='first':
            if versions:raise WorkflowError('first draft already preserved; no restart or best-of')
            draft=load(a.draft);analysis=load(a.analysis);source=load(root/'input.json');citations(analysis,source)
            draft['synthetic']=source['synthetic'];draft['target_role']=source['target_role']
            rows=w.flatten(draft);claimed={x['paragraph_id'] for x in analysis['claim_map']}
            expected={p['id'] for p in rows if p['kind'] in ('entry','bullet','name')}
            if not expected.issubset(claimed):raise WorkflowError('claim_map must cover name, entries, dates and bullets')
            write(root/'draft-first.json',draft);write(root/'analysis-first.json',analysis);changes=[];stage='first_generation'
        elif a.mode=='structure':
            if any(v['stage']=='automatic_structure' for v in versions) or state['semantic_passes']:raise WorkflowError('structure must occur once, after first render and before semantic passes')
            rows,changes=w.automatic_structure(w.read(latest/'content.json')['paragraphs']);stage='automatic_structure'
        else:
            if not any(v['stage']=='automatic_structure' for v in versions):raise WorkflowError('run structure before semantic editing')
            if state['semantic_passes']>=4:raise WorkflowError('four semantic passes exhausted; preserve remaining issues')
            decision=load(a.decision)
            if not decision.get('operations'):raise WorkflowError('no effective semantic operations')
            for op in decision['operations']:
                if not any(f.get('field')=='material_text' for f in op.get('source_fragments',[])):raise WorkflowError('each edit needs material evidence; JD is selection data only')
            rows,changes=w.apply_semantic(w.read(latest/'content.json')['paragraphs'],decision,load(root/'input.json'));stage='Codex-assisted semantic editing'
            state['semantic_passes']+=1
        folder=root/'versions'/('v%02d'%len(versions));w.build(folder,rows);write(folder/'changes.json',changes);write(folder/'stage.json',{'stage':stage})
        if a.mode=='edit':write(folder/'decision.json',decision)
        versions.append({'directory':str(folder.relative_to(root)),'stage':stage});update(root,state);print(folder.relative_to(root));return
    if latest is None:raise WorkflowError('create first draft before rendering')
    if a.mode=='render':
        folder,reused=render_version(latest,c,evidence)
        m=load(folder/'measurement.json')
        print(json.dumps({'accepted_render':str(folder.relative_to(root)),'cached_accepted_reuse':reused,
                          'measurement':{k:m[k] for k in ('pages','all_content_words_preserved','style_unchanged','pages_detail')}}));return
    if a.mode=='freeze':
        review=load(a.review);m=load(accepted/'measurement.json')
        delivery_checks=review_rules.delivery_invariants(load(latest/'content.json')['paragraphs'],load(root/'input.json'))
        for k in ('images_inspected','source_review_completed','writing_review_completed'):
            if review.get(k) is not True:raise WorkflowError('human/Codex review declaration missing: '+k)
        if 'remaining_issues' not in review:raise WorkflowError('review must list remaining_issues')
        if 'observations' in review:
            if not isinstance(review['observations'],list):raise WorkflowError('review observations must be a list')
            for observation in review['observations']:review_rules.validate_observation(observation)
        fonts=load(accepted/'font-evidence.json')['pdf_base_fonts']
        if not fonts or any(not any(n in f for n in ('TimesNewRoman','Wingdings')) for f in fonts):raise WorkflowError('unexpected or unverified embedded PDF fonts')
        if m['pages']!=1 or not m['all_content_words_preserved'] or not m['style_unchanged'] or any(p['outside_body_words'] for p in m['pages_detail']):raise WorkflowError('mechanical delivery checks failed; retain safe draft and remaining issues')
        out=root/'delivery';out.mkdir(exist_ok=False)
        for ext in ('docx','pdf','txt'):shutil.copy2(accepted/('resume.'+ext),out/('resume.'+ext))
        write(root/'self-review.json',review)
        write(root/'FREEZE.json',{'final_version':str(latest.relative_to(root)),'accepted_render_receipt_sha256':digest(latest/'accepted-render.json'),'accepted_attempt':str(accepted.relative_to(root)),'versions':versions,'semantic_passes':state['semantic_passes'],'files':{p.name:digest(p) for p in out.iterdir()},'measured':{'pages':m['pages'],'content_words_preserved':m['all_content_words_preserved'],'style_unchanged':m['style_unchanged']},'review_declaration':review,'delivery_invariant_checks':delivery_checks,'semantic_truth_automatically_proven':False,'elapsed_seconds':time.monotonic()-state['started_monotonic'],'timing_basis':'single-machine monotonic from init, excludes input gathering before init','native_Word_ATS_cross_engine_verified':False})
        state['frozen']=True;update(root,state);print('frozen delivery');return

def update(root,state):
    temp=root/'state.next.json';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'state.json')

def offline(event,args):
    if event.startswith('socket.') or event in ('http.client.connect','http.client.send'):
        GUARD_COUNTS['blocked_python_network_events']+=1
        raise WorkflowError('network disabled by runtime audit hook')

if __name__=='__main__':
    sys.addaudithook(offline)
    try:main()
    except Exception as exc:
        print(json.dumps({'status':'error','type':type(exc).__name__,'message':str(exc)}),file=sys.stderr);sys.exit(2)
