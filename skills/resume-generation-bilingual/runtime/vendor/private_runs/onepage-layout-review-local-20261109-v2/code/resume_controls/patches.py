"""Limited operations, exact original hashes; program-computed impact and located errors."""
from copy import deepcopy
import difflib
from . import document as d
from .common import digest,text_hash,save
from .citations import resolve_all
from .schemas import PATCH,validate
from .errors import ContractError,issue,schema_errors

def _transform(base,operations):
 original=d.units(base);deletions=set().union(*(d.descendants(base,o['target_id'])for o in operations if o['op']=='delete'))
 result=deepcopy(base);result['revision']+=1
 for op in operations:
  if op['op']=='replace':next(n for n in result['nodes'] if n['id']==op['target_id'])['text']=op['text']
 result['nodes']=[n for n in result['nodes'] if n['id']not in deletions]
 for op in operations:
  if op['op']!='move':continue
  subtree=d.descendants(result,op['target_id']);moving=[n for n in result['nodes'] if n['id']in subtree];result['nodes']=[n for n in result['nodes'] if n['id']not in subtree];moving[0]['parent']=op['new_parent_id']
  if op['after_id']:
   anchor_ids=d.descendants(result,op['after_id']);at=max(i for i,n in enumerate(result['nodes']) if n['id']in anchor_ids)+1
  else:
   at=next(i for i,n in enumerate(result['nodes']) if n['id']==op['new_parent_id'])+1
   if moving[0]['kind']=='sentence':at=next(i for i,n in enumerate(result['nodes']) if n['parent']==op['new_parent_id'] and n['kind']=='date')+1
  result['nodes'][at:at]=moving
 return result

def diagnose_patch(base,patch,source_text,jd_text=''):
 d.validate(base);errors=schema_errors(PATCH,patch)
 if errors and not (isinstance(patch,dict) and isinstance(patch.get('operations'),list) and all(isinstance(o,dict) and o.get('op')in ['replace','delete','move'] and isinstance(o.get('target_id'),str) and isinstance(o.get('original_hash'),str) and isinstance(o.get('source_refs'),list) and (o['op']!='replace' or isinstance(o.get('text'),str)) and (o['op']!='move' or all(k in o for k in ['new_parent_id','after_id','purpose'])) for o in patch['operations'])):return {'first_blocker':errors[0],'additional_errors':errors[1:],'errors':errors,'operations':[]}
 original=d.units(base);targets=[o['target_id'] for o in patch['operations']];affected=set();deletions=set();locations=[];destinations=[];op_audit=[]
 try:
  preview=_transform(base,patch['operations']);d.validate(preview);personal_ids={f['id']for f in d.claim_manifest(base)}|{f['id']for f in d.claim_manifest(preview)}
 except (ValueError,KeyError,IndexError,StopIteration):personal_ids=set(original)
 if patch.get('base_version')!=d.version(base):errors.append(issue('$.base_version','stale_document_version'))
 for i,op in enumerate(patch['operations']):
  path=f'$.operations[{i}]';ident=op['target_id'];n=original.get(ident)
  if ident in targets[:i]:errors.append(issue(path+'.target_id','duplicate_or_conflicting_target',id=ident))
  if not n:errors.append(issue(path+'.target_id','target_missing',id=ident));continue
  hash_ok=op['original_hash']==text_hash(n['text']);op_audit.append({'index':i,'target_id':ident,'original_hash_matches':hash_ok})
  if not hash_ok:errors.append(issue(path+'.original_hash','stale_original_text_hash'))
  if n['kind']=='name':errors.append(issue(path+'.target_id','identity_not_patchable'))
  reference_ids={ident}if op['op']=='replace'and n['kind']!='section'else d.descendants(base,ident)
  personal=bool(reference_ids&personal_ids)
  if personal and not op['source_refs']:errors.append(issue(path+'.source_refs','personal_patch_requires_source_reference'))
  located=[]
  for ri,ref in enumerate(op['source_refs']):
   try:
    l=resolve_all(source_text,[ref],jd_text,personal=personal)[0];located.append(l)
    if l['status']!='unique':errors.append(issue(f'{path}.source_refs[{ri}]',l['status']))
   except ValueError as exc:errors.append(issue(f'{path}.source_refs[{ri}]',str(exc)))
  locations.append({'target_id':ident,'references':located,'personal_evidence_required':personal,'semantic_support':'unreviewed'})
  ids=d.descendants(base,ident) if op['op']in ['delete','move'] else {ident};affected.update(ids)
  if op['op']=='delete':
   if n['kind']=='date':errors.append(issue(path,'date_cannot_be_deleted_alone'))
   if ids & set(base['protected_ids']):errors.append(issue(path,'protected_evidence_cannot_be_dropped_for_tail_position'))
   deletions.update(ids)
  elif op['op']=='replace':
   if op['text']==n['text']:errors.append(issue(path+'.text','no_op_not_a_repair'))
   if not op['text'].strip() and n['text'].strip():errors.append(issue(path+'.text','replace_with_empty_use_explicit_deletion'))
  else:
   if n['kind']not in ['entry','sentence']:errors.append(issue(path,'only_entry_or_sentence_can_move'))
   parent=original.get(op['new_parent_id']);anchor=op['after_id']
   if parent is None or parent['kind']!=('section' if n['kind']=='entry' else 'entry'):errors.append(issue(path+'.new_parent_id','move_destination_kind'))
   if op['new_parent_id']in ids:errors.append(issue(path+'.new_parent_id','move_cycle'))
   if anchor is not None and (anchor not in original or original[anchor]['parent']!=op['new_parent_id'] or original[anchor]['kind']!=n['kind'] or anchor in ids):errors.append(issue(path+'.after_id','move_anchor_invalid'))
   dest=(op['new_parent_id'],anchor)
   if dest in destinations:errors.append(issue(path,'move_destination_collision'))
   destinations.append(dest)
 for i,op in enumerate(patch['operations']):
  if op['target_id']not in original:continue
  path=f'$.operations[{i}]';desc=d.descendants(base,op['target_id'])-{op['target_id']}
  if op['target_id']in deletions and op['op']!='delete':errors.append(issue(path,'ancestor_delete_conflict'))
  if op['op']in ['delete','move'] and desc & set(targets):errors.append(issue(path,'ancestor_delete_conflict' if op['op']=='delete' else 'overlapping_move_operation'))
  if op['op']=='move' and (op['new_parent_id']in deletions or op['after_id']in deletions or op['new_parent_id']in targets or op['after_id']in targets):errors.append(issue(path,'unstable_move_destination'))
 return {'first_blocker':errors[0] if errors else None,'additional_errors':errors[1:],'errors':errors,'operations':op_audit,'affected_ids':sorted(affected),'deleted_ids':sorted(deletions),'citation_locations':locations,'semantic_support_certified':False}

def apply_patch(base,patch,source_text,jd_text=''):
 diag=diagnose_patch(base,patch,source_text,jd_text)
 if diag['errors']:raise ContractError(diag['errors'])
 original=d.units(base);targets=[o['target_id'] for o in patch['operations']];affected=set(diag['affected_ids']);deletions=set(diag['deleted_ids']);locations=diag['citation_locations']
 result=_transform(base,patch['operations'])
 d.validate(result)
 if result['nodes']==base['nodes']:raise ContractError([issue('$.operations','patch_has_no_actual_change')])
 if [n for n in base['nodes'] if n['id']not in affected]!=[n for n in result['nodes'] if n['id']not in affected]:raise ValueError('unmentioned_content_changed')
 before='\n'.join(n['id']+' '+n['text'] for n in base['nodes'])+'\n';after='\n'.join(n['id']+' '+n['text'] for n in result['nodes'])+'\n'
 return result,{'base_version':d.version(base),'result_version':d.version(result),'affected_ids':sorted(affected),'impact_computed_by_program':True,'authorized_operation_roots':targets,'deleted_ids':sorted(deletions),'operation_hash_audit':diag['operations'],'citation_locations':locations,'actual_full_candidate':result,'diff':''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='before',tofile='after')),'patch_syntax_valid':True,'semantic_support_certified':False,'source_review_required':True,'new_or_changed_claim_ids':sorted(affected-set(deletions))}

def save_application(directory,result,audit):
 from pathlib import Path
 root=Path(directory);save(root/'candidate.json',result);save(root/'application.json',audit)
 p=root/'actual.diff';content=audit['diff'].encode()
 if p.exists() and p.read_bytes()!=content:raise ValueError('diff_immutable')
 if not p.exists():p.write_bytes(content)
