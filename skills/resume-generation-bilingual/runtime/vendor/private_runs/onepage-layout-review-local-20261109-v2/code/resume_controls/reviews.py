"""Program-computed factual coverage; citation identity and semantic verdict stay distinct."""
from . import document as d
from .common import digest
from .schemas import REVIEW,BILINGUAL,validate,VERSION,protocol_hash
from .citations import resolve_all,locate
from .errors import ContractError,issue,schema_errors
from .bilingual_semantics import validate_language_bindings,language_advisories
def context_fingerprint(doc,node_id):
 ns=d.units(doc);n=ns[node_id];ancestors=[];parent=n['parent']
 while parent is not None:ancestors.append(ns[parent]);parent=ns[parent]['parent']
 return digest({'node':n,'ancestors':ancestors})


def audit_review(doc,review,source_text,changed_ids=(),jd_text=''):
 d.validate(doc);errors=schema_errors(REVIEW,review)
 if errors:raise ContractError(errors)
 if review['candidate_version']!=d.version(doc):raise ContractError([issue('$.candidate_version','review_version_mismatch')])
 d.validate_intent_context(doc,jd_text);typing=d.classification(doc);facts=typing['facts'];ids={n['id'] for n in facts};ns=d.units(doc);checks=review['checks'];by={};errors=[];evidence=[];nonpersonal={n['id']for key in ['decorations','intents']for n in typing[key]};nonpersonal_checks=[]
 for i,c in enumerate(checks):
  path=f'$.checks[{i}]';ident=c['id']
  if ident in by:errors.append(issue(path+'.id','duplicate_conflicting_judgment' if by[ident]['judgment']!=c['judgment'] else 'duplicate_judgment',id=ident))
  by[ident]=c
  if ident in nonpersonal:
   located=[locate(source_text,ref,jd_text,personal=False)for ref in c['evidence']]
   for ri,l in enumerate(located):
    if l['status']!='unique':errors.append(issue(f'{path}.evidence[{ri}]',l['status'],id=ident))
   nonpersonal_checks.append({'original_check':c,'personal_proof_required':False,'locations':located,'not_personal_support_verdict':True});continue
  if ident not in ids:
   errors.append(issue(path+'.id','unknown_or_nonfact_check_ID',id=ident));continue
  if c['judgment']=='supported' and not c['evidence']:errors.append(issue(path+'.evidence','supported_claim_requires_evidence'))
  if c['judgment']!='supported' and not c['note'].strip():errors.append(issue(path+'.note','nonpositive_judgment_needs_reason'))
  located=[]
  for ri,ref in enumerate(c['evidence']):
   l=locate(source_text,ref,jd_text);located.append(l)
   if l['status']!='unique':errors.append(issue(f'{path}.evidence[{ri}]',l['status'],id=ident))
  evidence.append({'id':ident,'locations':located})
 for i,x in enumerate(review['language_advice']):
  if x['id']not in ns:errors.append(issue(f'$.language_advice[{i}].id','advice_id_missing'))
 if set(review['unresolved_claim_ids'])-ids-nonpersonal:errors.append(issue('$.unresolved_claim_ids','unresolved_nonfact_or_missing_ID'))
 omissions=[]
 for i,o in enumerate(review['important_omissions']):
  located=locate(source_text,o['source_ref'],jd_text)
  if located['status']!='unique':errors.append(issue(f'$.important_omissions[{i}].source_ref',located['status']))
  omissions.append({**o,'located':[located]})
 for i,g in enumerate(review['job_fit_gaps']):
  location=locate(source_text,g['jd_ref'],jd_text,personal=False)
  if not g['jd_ref']['source_id'].startswith('JD:') or location['status']!='unique':errors.append(issue(f'$.job_fit_gaps[{i}].jd_ref','job_gap_requires_valid_JD_block'))
 if errors:raise ContractError(errors)
 missing=sorted(ids-set(by));complete=bool(review['complete'] and not missing and not review['incomplete_reason'])
 if not review['complete'] and not review['incomplete_reason'].strip():raise ContractError([issue('$.incomplete_reason','explicit_incomplete_reason_required')])
 judgments={k:c['judgment'] for k,c in by.items() if k in ids};defects=[i for i,v in judgments.items() if v in ['contradicted','missing_support']];ambiguous=[i for i,v in judgments.items() if v=='ambiguous']
 return {'candidate_version':d.version(doc),'protocol_version':VERSION,'protocol_sha256':protocol_hash(),'classification_sha256':digest(d.classification(doc)),'program_intents':d.classification(doc)['intents'],'typing_ambiguities':d.classification(doc)['typing_ambiguities'],'protocol_usable':True,'coverage_complete':complete,'checked_ids':sorted(set(by)&ids),'uncompleted_ids':missing,'program_computed_coverage':True,'review_claimed_complete':review['complete'],'incomplete_reason':review['incomplete_reason'] or ('missing_required_facts' if missing else ''),'decorations':d.classification(doc)['decorations'],'changed_claims_reviewed':complete and not ((set(changed_ids)&ids)-set(by)),'unreviewed_changed_ids':sorted((set(changed_ids)&ids)-set(by)),'citations_locatable':True,'citation_locations':evidence,'source_judgment':'unreviewed' if not complete else 'reported_unsupported' if defects else 'reported_ambiguous' if ambiguous else 'reviewer_reports_supported','checks_by_id':judgments,'defect_ids':defects,'ambiguous_ids':ambiguous,'material_omissions':[o for o in omissions if o['material']],'awaiting_user':bool(review['awaiting_user_questions']),'unresolved_claim_ids':[i for i in review['unresolved_claim_ids']if i in ids],'nonpersonal_unresolved_ids':[i for i in review['unresolved_claim_ids']if i in nonpersonal],'nonpersonal_checks':nonpersonal_checks,'intent_alignment':'requires_resolution'if any(c['original_check']['judgment']!='supported'and c['original_check']['id']in {i['id']for i in typing['intents']}for c in nonpersonal_checks)else'no_reported_blocker','semantic_truth_automatically_certified':False,'reviewer_judgments_are_not_HR_gold_standard':True,'language_advice':review['language_advice'],'job_fit_gaps':review['job_fit_gaps'],'program_language_advisories':language_advisories(doc)}

def audit_bilingual(docs,review,source,jd_text=''):
 try:validate_language_bindings(docs,bilingual=True)
 except ValueError as exc:raise ContractError([issue('$.candidates',str(exc))]) from exc
 errors=schema_errors(BILINGUAL,review)
 if errors:raise ContractError(errors)
 if review['candidate_versions']!={k:d.version(v) for k,v in docs.items()}:raise ContractError([issue('$.candidate_versions','review_version_mismatch')])
 audits={};all_errors=[]
 for lang,doc in docs.items():
  r={'schema_version':review['schema_version'],'candidate_version':review['candidate_versions'][lang],'checks':[{k:v for k,v in c.items() if k!='language'} for c in review['checks'] if c['language']==lang],'complete':review['complete'],'incomplete_reason':review['incomplete_reason'],'important_omissions':[{k:v for k,v in c.items() if k!='language'} for c in review['important_omissions'] if c['language']==lang],'language_advice':[{k:v for k,v in c.items() if k!='language'} for c in review['language_advice'] if c['language']==lang],'unresolved_claim_ids':[c['id'] for c in review['unresolved_claims'] if c['language']==lang],'awaiting_user_questions':[c['question'] for c in review['awaiting_user_questions'] if c['language']==lang],'job_fit_gaps':review['job_fit_gaps']}
  try:audits[lang]=audit_review(doc,r,source,jd_text=jd_text)
  except ContractError as exc:
   import re
   for error in exc.errors:
    e={**error,'language':lang};path=e['path'];m=re.match(r'^\$\.(checks|important_omissions|language_advice)\[(\d+)\](.*)$',path)
    if m:
     key,local,suffix=m.groups();indices=[i for i,x in enumerate(review[key]) if x['language']==lang];idx=int(local)
     if idx<len(indices):e['path']=f'$.{key}[{indices[idx]}]'+suffix
    elif path=='$.candidate_version':e['path']='$.candidate_versions.'+lang
    elif path=='$.unresolved_claim_ids':e['path']='$.unresolved_claims'
    all_errors.append(e)
 comparisons=[];nonpersonal_comparisons=[]
 for i,p in enumerate(review['comparisons']):
  personal=[p[l+'_id']in {f['id']for f in d.claim_manifest(docs[l])}for l in ['en','zh']]
  nonpersonal=[p[l+'_id']in {f['id']for key in ['decorations','intents']for f in d.classification(docs[l])[key]}for l in ['en','zh']]
  if all(nonpersonal):nonpersonal_comparisons.append({'index':i,**p,'not_personal_support_verdict':True});continue
  if not all(personal):
   all_errors.append(issue(f'$.comparisons[{i}]','comparison_personal_intent_type_mismatch'if any(personal)and any(nonpersonal)else'comparison_nonfact_or_missing_ID'));continue
  comparisons.append({'index':i,**p})
 if all_errors:raise ContractError(all_errors)
 blocking={'contradiction','unsupported_addition','source_ambiguity'}
 for lang,a in audits.items():
  a['single_language_source_judgment']=a['source_judgment']
  a['comparisons']=comparisons
  a['nonpersonal_comparisons']=nonpersonal_comparisons
  a['intent_alignment']='requires_resolution'if a.get('intent_alignment')=='requires_resolution'or any(p['category']in ['contradiction','unsupported_addition','source_ambiguity']for p in nonpersonal_comparisons)else'no_reported_blocker'
  conflicts=[p for p in comparisons if p['category']in blocking]
  a['comparison_conflicts']=conflicts
  a['comparison_state']='requires_resolution' if any(p['category']in ['contradiction','unsupported_addition'] for p in conflicts) else 'awaiting_source_clarification' if conflicts else 'no_reported_blocker'
  a['comparison_vs_single_language_conflicts']=[{'comparison_index':p['index'],'id':p[lang+'_id'],'single_language_judgment':a['checks_by_id'].get(p[lang+'_id']),'category':p['category']} for p in conflicts if a['checks_by_id'].get(p[lang+'_id'])=='supported']
  if conflicts:
   a['unresolved_claim_ids']=sorted(set(a['unresolved_claim_ids'])|{p[lang+'_id'] for p in conflicts})
   if a['source_judgment']=='reviewer_reports_supported':a['source_judgment']='reported_cross_language_issue'
   if any(p['category']=='source_ambiguity' for p in conflicts):a['awaiting_user']=True
  a['comparison_judgments_not_independent_truth']=True
 return audits

def evaluate_output(stage, raw, docs, material, jd):
 """Same full gates for transport parsing and archived offline diagnostics."""
 try:validate_language_bindings(docs,bilingual=stage=='bilingual_review')
 except ValueError as exc:raise ContractError([issue('$.candidates',str(exc))]) from exc
 if stage in ['review','final_review']:
  if len(docs)!=1:raise ValueError('one_actual_candidate_required')
  a=audit_review(next(iter(docs.values())),raw,material,jd_text=jd)
  return {'review_audit':a,'usable':bool(a['coverage_complete']),
          **({}if a['coverage_complete']else{'error':'full_review_coverage_incomplete'})}
 if stage=='bilingual_review':
  a=audit_bilingual(docs,raw,material,jd)
  complete=all(v['coverage_complete']for v in a.values())
  return {'review_audits':a,'usable':complete,
          **({}if complete else{'error':'bilingual_full_review_coverage_incomplete'})}
 raise ValueError('review_stage_required')

def close_known_issues(before,after,issues,review_audit):
 old=d.units(before);new=d.units(after);out=[]
 for issue in issues:
  if set(issue)!={'id','target_ids','confirmed','reason'} or not issue['target_ids'] or set(issue['target_ids'])-set(old):raise ValueError('known_issue_contract')
  changed=all(i not in new or context_fingerprint(before,i)!=context_fingerprint(after,i) for i in issue['target_ids'])
  surviving=[i for i in issue['target_ids'] if i in new]
  supported=all(review_audit['checks_by_id'].get(i)=='supported' for i in surviving)
  closed=bool(changed and supported and not(set(surviving)&set(review_audit.get('unresolved_claim_ids',[]))) and review_audit['coverage_complete'] and review_audit['citations_locatable'] and review_audit['changed_claims_reviewed'])
  # A fresh positive verdict does not silently erase an unchanged confirmed defect.
  out.append({**issue,'closed':closed,'basis':'claim_removed_or_context_changed_and_full_source_reviewer_supported' if closed else 'unchanged_or_not_independently_supported','not_automatic_truth_proof':True})
 return out

def acceptance(*,protocol_usable,citations_locatable,review_audit,known_issues,measurement,clarification,visual_preferences,pending_items=()):
 r=review_audit or {};m=measurement or {};mapping=m.get('word_pdf_mapping',{});page_pass=m.get('pages')==1
 dimensions={'protocol_usable':bool(protocol_usable),'citations_locatable':bool(citations_locatable and r.get('citations_locatable')),'source_judgment':r.get('source_judgment','unreviewed'),'bilingual_comparison':r.get('comparison_state','not_applicable'),'intent_alignment':r.get('intent_alignment','not_applicable'),'nonpersonal_checks':r.get('nonpersonal_checks',[]),'nonpersonal_unresolved_ids':r.get('nonpersonal_unresolved_ids',[]),'comparison_conflicts':r.get('comparison_conflicts',[]),'known_defects_closed':all(x.get('closed') for x in known_issues if x.get('confirmed')),'post_revision_review_complete':bool(r.get('coverage_complete') and r.get('changed_claims_reviewed')),'page_count':{'actual':m.get('pages'),'one_page':page_pass},'text_and_punctuation':bool(mapping.get('word_pdf_body_match_in_order')),'real_clipping':m.get('actual_clipping_detected'),'fonts':m.get('fonts_validated'),'awaiting_user':bool(clarification.get('awaiting_user') or r.get('awaiting_user')),'unresolved_claim_ids':sorted(set(clarification.get('unresolved_claim_ids',[]))|set(r.get('unresolved_claim_ids',[]))),'visual_preferences':visual_preferences,'pending_items':list(pending_items),'unresolved_routes':sorted({x['route']for x in pending_items if not x.get('closed')}),'markdown_remnants':m.get('balanced_markdown_remaining'),'sparse_layout':'review_selection_without_padding' if any(p.get('body_utilization_pct',100)<65 for p in m.get('pages_detail',[])) else 'not_flagged'}
 dimensions['awaiting_user']=dimensions['awaiting_user']or any(x.get('awaiting_user')for x in pending_items)
 passed=all([not any(x.get('blocks_current_draft',not x.get('closed'))for x in pending_items),not m.get('balanced_markdown_remaining',False),dimensions['intent_alignment']!='requires_resolution',dimensions['bilingual_comparison'] not in ['requires_resolution','awaiting_source_clarification'],dimensions['protocol_usable'],dimensions['citations_locatable'],dimensions['source_judgment']=='reviewer_reports_supported',dimensions['known_defects_closed'],dimensions['post_revision_review_complete'],page_pass,dimensions['text_and_punctuation'],dimensions['real_clipping']is False,dimensions['fonts']is True,not m.get('nonpunctuation_body_overflow',True),not m.get('date_month_orphan',True),not r.get('material_omissions'),not dimensions['unresolved_claim_ids']])
 return {'dimensions':dimensions,'complete_flow_pass':passed,'scope_of_pass':'Declared protocol/evidence/review/layout gates only; semantics remain reviewer judgments, not automatic factual certification.','delivery_status':('safe_draft_awaiting_user' if dimensions['awaiting_user'] else 'basic_gates_passed_editorial_review_pending') if passed else 'incomplete','final_editorial_acceptance':'pending','model_ready_cannot_override':True,'HTTP200_cannot_override':True,'quality_automatically_certified':False}
