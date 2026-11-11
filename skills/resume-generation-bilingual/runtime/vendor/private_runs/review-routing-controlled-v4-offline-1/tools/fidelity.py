"""Offline review contract. Structural validation does not prove semantic truth."""
from pathlib import Path
import copy,json,re,hashlib
R=Path(__file__).resolve().parents[1]
LENSES=['career_stage_and_grade','completed_counts_and_scope','personal_vs_team','causality','named_tools_and_level','language_and_credentials','proposal_pilot_completion']
def read(p):return json.loads(Path(p).read_text())
def write(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise ValueError('Preserve prior artifact: '+str(p))
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def flatten(resume):
 out=[]
 for si,s in enumerate(resume['sections']):
  out.append({'id':f's{si}','kind':'section','text':s['heading'],'section':si})
  for ii,it in enumerate(s['items']):
   if it.get('heading') or it.get('date'):out.append({'id':f's{si}.i{ii}.role_date','kind':'entry','text':it.get('heading',''),'date':it.get('date',''),'section':si,'item':ii})
   for bi,b in enumerate(it.get('bullets',[])):out.append({'id':f's{si}.i{ii}.b{bi}','kind':'bullet','text':b,'section':si,'item':ii})
 return out

def source_paragraphs(text):
 out=[];start=0
 for i,p in enumerate(text.split('\n\n')):
  pos=text.find(p,start);out.append({'id':f'P{i:02d}','start':pos,'end':pos+len(p),'text':p});start=pos+len(p)
 return out

def apply(rows,operations):
 out=copy.deepcopy(rows);changes=[]
 for op in operations:
  key=op['id'];matches=[i for i,x in enumerate(out) if x['id']==key]
  if len(matches)!=1:raise ValueError('Missing or ambiguous stable assertion ID '+key)
  index=matches[0];before=copy.deepcopy(out[index]);kind=op['op']
  if kind=='replace':out[index].update(op['set']);after=copy.deepcopy(out[index])
  elif kind=='remove':out.pop(index);after=None
  elif kind=='move_after':
   selected=[next((x for x in out if x['id']==uid),None) for uid in op['ids']]
   if any(x is None for x in selected) or key in op['ids']:raise ValueError('Invalid move block')
   out=[x for x in out if x['id'] not in op['ids']]
   index=next(i for i,x in enumerate(out) if x['id']==key)
   for x in selected:x.update(op.get('context',{}))
   out[index+1:index+1]=selected;after=copy.deepcopy(selected)
  elif kind=='add_after':
   values=copy.deepcopy(op['rows'])
   if any(x['id'] in {y['id'] for y in out} for x in values):raise ValueError('Duplicate assertion ID')
   out[index+1:index+1]=values;after=values
  else:raise ValueError('Unsupported edit operation')
  if not op.get('reason') or not op.get('source_paragraphs'):raise ValueError('Edit needs reason and original-source positions')
  changes.append({'operation':kind,'id':key,'before':before,'after':after,'reason':op['reason'],'source_paragraphs':op['source_paragraphs'],'execution':'Codex-assisted semantic/source editing; not API output or deterministic truth inference'})
 # Remove an actually empty section, never blank employment history.
 for i in range(len(out)-1,-1,-1):
  if out[i]['kind']=='section' and (i+1==len(out) or out[i+1]['kind']=='section'):
   changes.append({'operation':'remove_empty_section','id':out[i]['id'],'before':out[i],'after':None,'execution':'automatic structure, no remaining child content'});out.pop(i)
 return out,changes

def content_status(assessments):
 if any(x.get('defect_confirmed') is True and not x.get('resolved_after_source_review') for x in assessments):return 'confirmed_defect_open'
 if any(x.get('after_judgment') in ['unsupported','contradicted'] for x in assessments):return 'needs_source_revision'
 if any(x.get('after_judgment')=='ambiguous' and not x.get('omitted_from_resume') for x in assessments):return 'content_awaiting_user'
 return 'Codex_source_review_completed_no_open_confirmed_defect'

def make_review(number,mapping,operations=None,findings=None,notes=None):
 rows=read(R/'inputs-manifest.json')['groups'];row=next(x for x in rows if x['person']==f'case-{number}');inst=row['instance'];source=read(R/'inputs'/inst/'source.json')['material_text'];paras=source_paragraphs(source)
 record={'instance':inst,'review_lenses':LENSES,'source_only_personal_fact_basis':True,'JD_used_only_for_selection_not_as_personal_evidence':True,'reviewer':'Codex-assisted direct original-source review, not HR gold standard','model_evaluations_not_overwritten_or_used_as_facts':True,'notes':notes or [],'languages':{}}
 for lang in ['en','zh']:
  resume=read(R/'drafts'/inst/lang/'v00-editorial-base.json');before=flatten(resume);ops=(operations or {}).get(lang,[]);after,changes=apply(before,ops);flags=(findings or {}).get(lang,{});assessments=[]
  for unit in [x for x in before if x['kind'] in ['entry','bullet']]:
   uid=unit['id'];prefix=uid.rsplit('.',1)[0] if unit['kind']=='bullet' else uid[:-len('.role_date')];refs=mapping[lang].get(uid,mapping[lang].get(prefix))
   if not refs:raise ValueError('Unreviewed assertion '+inst+'/'+lang+'/'+uid)
   refs=[f'P{x:02d}' if isinstance(x,int) else x for x in refs]
   if any(not any(p['id']==ref for p in paras) for ref in refs):raise ValueError('Nonexistent source reference')
   current=next((x for x in after if x['id']==uid),None);flag=flags.get(uid,{});judgment=flag.get('before_judgment','supported_or_reasonable_paraphrase');after_judgment=flag.get('after_judgment','supported_or_reasonable_paraphrase' if current is not None else 'reasonable_omission');confirmed=flag.get('defect_confirmed',False)
   if confirmed and current==unit and flag.get('resolved_after_source_review'):raise ValueError('Cannot close confirmed factual defect without editing/removal')
   if confirmed and current is not None and not flag.get('resolution_rationale'):raise ValueError('Confirmed repair needs new full-claim source assessment, not keyword absence')
   assessments.append({'assertion_id':uid,'candidate_before':unit,'candidate_after':current,'source_paragraphs':refs,'before_judgment':judgment,'after_judgment':after_judgment,'defect_confirmed':confirmed,'resolved_after_source_review':flag.get('resolved_after_source_review',False) if confirmed else None,'human_judgment_required':flag.get('human_judgment_required',False),'original_model_detection':'Not inferred from old labels; raw model evaluation retained separately','reason':flag.get('reason','Original paragraph context directly checked for actor, stage, number/scope, causality and tool/language credentials; professional compression/selection allowed.'),'resolution_rationale':flag.get('resolution_rationale'),'omitted_from_resume':current is None,'semantic_judgment_source':'Codex source comparison, not automatic keyword/quote validation'})
  # Any new row is explicit sourced editorial content; never treated as an API-first claim.
  for unit in [x for x in after if x['kind'] in ['entry','bullet'] and x['id'] not in {y['id'] for y in before}]:
   op=next(o for o in ops if any(r['id']==unit['id'] for r in o.get('rows',[])));assessments.append({'assertion_id':unit['id'],'candidate_before':None,'candidate_after':unit,'source_paragraphs':[f'P{x:02d}' if isinstance(x,int) else x for x in op['source_paragraphs']],'before_judgment':None,'after_judgment':'supported_or_reasonable_paraphrase','defect_confirmed':False,'human_judgment_required':False,'reason':op['reason'],'semantic_judgment_source':'Codex source comparison'})
  status=content_status(assessments);target=R/'drafts'/inst/lang;write(target/'v01-reviewed-rows.json',{'name':resume['name'],'rows':after,'language':lang,'target_role':row['target_role']});write(target/'EDIT_RECORD.json',changes);record['languages'][lang]={'status':status,'assertions':assessments,'changed':bool(changes),'open_questions_separate':True}
 record['source_paragraphs']=paras;write(R/'facts'/f'{inst}.json',record)
 print(json.dumps({'reviewed':inst,'units':sum(len(v['assertions']) for v in record['languages'].values()),'edits':sum(len((operations or {}).get(lang,[])) for lang in ['en','zh'])},ensure_ascii=False))
