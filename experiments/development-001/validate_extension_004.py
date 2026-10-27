import pathlib,json,re,hashlib,collections,sys
root=pathlib.Path(__file__).parent;b=root/'batch-004';errors=[];counts=collections.Counter();identity=set();lineage=set();files=[]
def check(ok,m):
 if not ok:errors.append(m)
def numbers(s):return collections.Counter(re.findall(r'\d+(?:\.\d+)?',s))
old=[]
for batch in ['batch-001','batch-002','batch-003']:
 for p in (root/batch).glob('case-*/profile.json'):old.append(json.loads(p.read_text()))
for d in sorted(b.glob('case-*')):
 p=json.loads((d/'profile.json').read_text());j=json.loads((d/'job.json').read_text());c=json.loads((d/'curation-notes.json').read_text());facts=p['facts'];ids={f['id'] for f in facts};cid=d.name
 check(len(facts)>=16 and len(facts)<=22,f'{cid}: fact count');check(len(ids)==len(facts),f'{cid}: fact IDs');check(3<=len(j['requirements'])<=5,f'{cid}: req count')
 check(p['case_id']==j['case_id']==c['case_id']==cid,f'{cid}: case IDs')
 check(p['synthetic'] and j['synthetic'],f'{cid}: synthetic labels')
 check(p['identity_id'] not in identity and p['identity_id'] not in {x['identity_id'] for x in old},f'{cid}: duplicate identity');identity.add(p['identity_id'])
 check(p['source_family'] not in lineage and p['source_family'] not in {x['source_family'] for x in old},f'{cid}: duplicate lineage');lineage.add(p['source_family'])
 for f in facts:
  check(numbers(f['en'])==numbers(f['zh']),f'{cid}/{f["id"]}: bilingual numbers')
  ds=re.findall(r'\b(20\d\d)-(\d\d)\b',f['en']);check(all(1<=int(m)<=12 for y,m in ds),f'{cid}/{f["id"]}: month')
  if f['kind']=='employment' and len(ds)==2:check(ds[0]<=ds[1],f'{cid}/{f["id"]}: date order')
  check(bool(f.get('provenance')),f'{cid}/{f["id"]}: provenance')
 for req in j['requirements']:
  check('evidence_status' not in req and 'supporting_fact_ids' not in req,f'{cid}: curation leaks into JD')
  check(numbers(req['en'])==numbers(req['zh']),f'{cid}/{req["id"]}: bilingual requirement numbers')
 labels=c.get('requirement_evidence',c.get('requirements',[]));check(len(labels)==len(j['requirements']),f'{cid}: curation coverage')
 for x in labels:
  status=x['evidence_status'];supp=x['supporting_fact_ids'];counts[status]+=1
  check(status in {'direct','transferable','missing'},f'{cid}: label');check(set(supp)<=ids,f'{cid}: bad support');check(not supp if status=='missing' else bool(supp),f'{cid}: label/support')
 for u in p.get('uncertainties',[]):
  if 'affected_fact_ids' in u:check(set(u['affected_fact_ids'])<=ids,f'{cid}: bad uncertainty reference')
  if 'en' in u and 'zh' in u:check(numbers(u['en'])==numbers(u['zh']),f'{cid}: uncertainty numeric mismatch')
 # Only frozen source records belong to the source manifest. Generated artifacts
 # (e.g. generation.json/evaluation.json) may coexist without becoming sources.
 files.extend(d/name for name in ('profile.json','job.json','curation-notes.json'))
m=b/'source-manifest-v1.sha256.json'
if m.exists():
 manifest=json.loads(m.read_text())
 for rel,h in manifest['files'].items():check(hashlib.sha256((b/rel).read_bytes()).hexdigest()==h,f'{rel}: hash mismatch')
 check(set(manifest['files'])=={str(p.relative_to(b)) for p in files},'manifest coverage')
print(json.dumps({'cases':len(identity),'files':len(files),'fact_counts':{d.name:len(json.loads((d/'profile.json').read_text())['facts']) for d in sorted(b.glob('case-*'))},'requirement_labels':dict(counts),'errors':errors,'limitations':['Structural and numeric checks do not prove semantic entailment. Contradictions are deliberately flagged, not automatically resolved.','Original 30-case frozen sources and manifest are unchanged; extension is development-only.']},ensure_ascii=False,indent=2));sys.exit(bool(errors))
