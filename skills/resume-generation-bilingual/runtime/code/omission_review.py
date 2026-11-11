"""Explicit source-to-output omission review over the strict v1 unit contract.

A reviewer reports important omissions; code checks binding, citations and target
scope, never truth or whether a real person has a qualification. No model calls.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import deliverable_review as legacy
from resume_controls.citations import locate

VERSION='complete-deliverable-review-v2'
EXTRA_KEYS={'important_omissions','source_coverage_note','omission_contract_sha256'}
OMISSION_KEYS={'target_id','target_text_sha256','source_evidence','importance_basis',
 'importance_evidence','importance_reason','current_coverage_explanation',
 'reviewed_context_unit_ids','target_fit_reason'}
REPAIRABLE={'entry','date','body'}
REF={'type':'object','additionalProperties':False,'properties':{
 'source_id':{'type':'string'},'quote':{'type':'string','minLength':1}},'required':['source_id','quote']}
OMISSION_SCHEMA={'type':'object','additionalProperties':False,'properties':{
 'target_id':{'oneOf':[{'type':'string'},{'type':'null'}]},'target_text_sha256':{'oneOf':[{'type':'string'},{'type':'null'}]},
 'source_evidence':{'type':'array','minItems':1,'items':REF},
 'importance_basis':{'enum':['job_relevance','explicit_material_requirement'],'description':'Use job_relevance for JD: evidence, including explicit requirements in the job description. Use explicit_material_requirement only for an explicit request in personal M: material.'},
 'importance_evidence':{'type':'array','minItems':1,'items':REF,'description':'Exact evidence domain must match importance_basis: job_relevance requires JD: references; explicit_material_requirement requires M: references. Job-description requirements are JD:, not personal material.'},
 'importance_reason':{'type':'string','minLength':1},
 'current_coverage_explanation':{'type':'string','minLength':1},
 'reviewed_context_unit_ids':{'type':'array','minItems':1,'items':{'type':'string'},'uniqueItems':True},
 'target_fit_reason':{'type':'string','minLength':1}},'required':sorted(OMISSION_KEYS)}
REVIEW_SCHEMA=deepcopy(legacy.REVIEW_SCHEMA)
REVIEW_SCHEMA['properties']['schema_version']={'const':VERSION}
REVIEW_SCHEMA['properties'].update(important_omissions={'type':'array','items':OMISSION_SCHEMA},
 source_coverage_note={'type':'string','minLength':1},omission_contract_sha256={'type':'string'})
REVIEW_SCHEMA['required']=sorted(legacy.RECEIPT_KEYS|EXTRA_KEYS)
GUIDANCE=(
 'Review source to current visible resume as well as every existing output unit. '
 'Report only material omissions: source-supported information relevant to the job or explicitly '
 'required by supplied material, or a qualifier whose removal strengthens a retained claim. '
 'Do not require all source details. Safe selection, irrelevant details and facts already conveyed '
 'elsewhere in the visible resume are not omissions. Notes alone do not satisfy important body coverage. '
 'Compare against the whole visible resume, including headings, dates and body text. Equivalent '
 'accurate coverage in any suitable visible field satisfies coverage: do not demand duplication '
 'in a dedicated date field, label or other preferred placement. Preserve which event a date '
 'describes; a safe empty date field is not missing_support solely because it is empty. '
 'The presence or explicit statement of a source fact is not an explicit requirement to include '
 'it. explicit_material_requirement needs an actual inclusion request in M:, not merely the '
 'fact itself. Independently explain job relevance or necessary disambiguation of a retained '
 'claim using the existing evidence fields. Do not require every optional date, including a '
 'conferral date, merely because it is known. A materially important omitted qualifier can '
 'still be a finding; judge the actual claim in context. Accurate proposal or planning wording '
 'does not assert implementation or results, so do not demand an extra nonimplementation or '
 'outcome disclaimer unless needed to correct a specific misleading claim. '
 'Optional or permissive inclusion language, such as may include, is permission rather than '
 'an instruction to include. For an optional detail, explain a specific misleading consequence '
 'of leaving it out or cite a separate explicit inclusion requirement; source presence and a '
 'JD mention alone do not suffice. Preserve genuinely required dates and qualifiers. '
 'For optional or may-include dates, generic completeness or speculative background-check '
 'concerns do not establish importance. Identify a concrete erroneous implication in retained '
 'text or an actual explicit inclusion requirement; preserve findings for genuinely required '
 'dates and qualifiers. '
 'Read proposed or planned work at its stated stage. Do not demand a nonimplementation '
 'disclaimer merely because the source also states that implementation did not occur. Still '
 'flag wrong quantities, actors, or retained wording that actually claims implementation or completion. '
 'Keep entry, study completion, graduation and degree conferral as distinct events; retain a useful '
 'known endpoint without inventing the other. Conflicting dates are not resolved by asking a question. '
 'Missing information is not evidence of absence. Check each actor/action and quantity/carrier separately. '
 'For each important omission, quote exact M: evidence for the fact and separate exact JD: or M: '
 'evidence for its importance. The enum maps strictly to the evidence source: job_relevance requires '
 'JD: citations, including any explicit requirement stated in the job description; '
 'explicit_material_requirement requires M: citations of an explicit request in personal material. '
 'Do not classify an explicit JD requirement as explicit_material_requirement. Explain comparison with the whole current visible resume, including '
 'where else you checked, and why the target is the same source-supported entry/activity. '
 'Use an existing entry/date/body target and its raw-text hash. Related units are context only. '
 'Distinct omission findings may share one target; retain each finding and its own fact, importance '
 'evidence and explanation. Do not repeat an identical finding. Repair all findings for a target '
 'with one coherent replacement, then perform a fresh full review. Shared source lines do not '
 'prove that different actors, events or entries are semantically related. '
 'If no suitable same-source target exists or new structure is needed, use null target/hash and explain; '
 'do not repurpose an unrelated employer, school, label or section. '
 'Return an empty important_omissions list only after this check finds none. source_coverage_note '
 'must explain the coverage judgment; complete=false/incomplete_reason remains mandatory if either '
 'unit or source-coverage review is unfinished. This is reviewer judgment, not automatic truth. '
 'Never supply a rewritten answer in an omission finding. After any body PATCH, re-review all units '
 'and source coverage including notes against the new version; use the existing auxiliary route for '
 'stale notes. No automatic closure by matching words.'
)
_MODULE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
def contract_hash():
 return legacy.digest({'module_sha256':_MODULE_SHA256,'schema':REVIEW_SCHEMA,'guidance':GUIDANCE})

def expected_receipt_bindings(deliverable):
 return {'schema_version':VERSION,'deliverable_version':deliverable['version'],
  'source_sha256':deliverable['source_sha256'],'jd_sha256':deliverable['jd_sha256'],
  'runtime_sha256':deliverable['runtime_sha256'],'omission_contract_sha256':contract_hash()}

BINDING_COPY_GUIDANCE=(
 'Copy every expected_receipt_bindings value exactly into the corresponding top-level receipt field. '
 'These are opaque identifiers: never recompute, shorten, reformat or substitute another hash. '
 'In particular deliverable_version is deliverable.version, NOT deliverable.document_version. '
 'Copy each checks[].id and checks[].text_sha256 exactly from the corresponding deliverable.units '
 'record. required_unit_bindings is the exact ID/hash checklist, and required_unit_check_count is '
 'the number of checks in a completed review. Cover each listed ID exactly once, even empty '
 'date fields and auxiliary state, then compare the complete ID set and each paired hash. '
 'Use exact supplied IDs for related units and omission targets. Do not hash displayed '
 'text yourself or infer IDs. Bindings identify the input only; independently determine all '
 'judgments, omissions, complete and incomplete_reason. Never mark a review complete merely '
 'because all binding fields were copied. A completed review may report contradictions, unsupported '
 'claims or important omissions: complete describes whether review work is finished, not whether '
 'the candidate is clean. Use complete=false only when review is unfinished, and explain the '
 'unfinished work. A detected defect alone is not unfinished review. For every evidence source_id, '
 'copy only a provided M: or JD: source catalogue ID; candidate unit IDs are not source citations. '
 'Use candidate unit IDs only in checks.id, related_unit_ids, reviewed_context_unit_ids and target_id. '
 'Use every enum value exactly as listed in output_schema, without inventing synonyms. '
 'For nonempty name, entry, date and label units, supported or non_assertive judgments require '
 'M: evidence. Honest contradicted, missing_support or ambiguous judgments may leave evidence '
 'empty when none is available; never invent citations to satisfy a schema.')

def material_evidence_check_schema(check_schema,units,source_ids):
 """Constant-size ID groups, not one full schema per unit; audit remains authoritative."""
 required=[u['id'] for u in units if u['kind'] in ('name','entry','date','label') and u['text'].strip()]
 other=[u['id'] for u in units if u['id'] not in required]
 groups=[]
 if required:
  material=deepcopy(check_schema)
  material['properties']['id']['enum']=required
  material['properties']['evidence']['items']['properties']['source_id']['enum']=[i for i in source_ids if i.startswith('M:')]
  positive=deepcopy(material);negative=deepcopy(material)
  positive['properties']['source_judgment']['enum']=['supported','non_assertive']
  positive['properties']['evidence']['minItems']=max(1,positive['properties']['evidence'].get('minItems',0))
  negative['properties']['source_judgment']['enum']=[j for j in material['properties']['source_judgment']['enum'] if j not in ('supported','non_assertive')]
  # oneOf returns early in the lightweight validator: every leaf is the full
  # original check schema, retaining all required fields, types and enums.
  # Negative/uncertain judgments retain the original empty-evidence allowance.
  groups.append({'oneOf':[positive,negative]})
 if other:
  remaining=deepcopy(check_schema);remaining['properties']['id']['enum']=other
  groups.append(remaining)
 return {'oneOf':groups} if groups else deepcopy(check_schema)

def build_review_request(deliverable,source,runtime_date_basis):
 request=legacy.build_review_request(deliverable,source,runtime_date_basis)
 request.pop('input_sha256');context=request['context']
 context['rules']+='\n'+GUIDANCE
 context['output_schema']=deepcopy(REVIEW_SCHEMA)
 bindings=expected_receipt_bindings(deliverable)
 context['expected_receipt_bindings']=deepcopy(bindings)
 unit_ids=[u['id'] for u in deliverable['units']]
 context['required_unit_bindings']=[{'id':u['id'],'text_sha256':u['text_sha256']} for u in deliverable['units']]
 context['required_unit_check_count']=len(unit_ids)
 checks_schema=context['output_schema']['properties']['checks']
 checks_schema['items']['properties']['id']['enum']=list(unit_ids)
 # Both supported oneOf branches below retain this full strict schema. Partial
 # reviews remain representable; exact ID/hash coverage is still audited.
 checks_schema['maxItems']=len(unit_ids)
 source_ids=[block['id'] for block in context['source_blocks']]
 def bind_citation_schema(value):
  if isinstance(value,dict):
   props=value.get('properties',{})
   if 'source_id' in props:props['source_id']['enum']=list(source_ids)
   for child in value.values():bind_citation_schema(child)
  elif isinstance(value,list):
   for child in value:bind_citation_schema(child)
 bind_citation_schema(context['output_schema'])
 checks_schema['items']=material_evidence_check_schema(checks_schema['items'],deliverable['units'],source_ids)
 for key,value in bindings.items():context['output_schema']['properties'][key]={'type':'string','const':value}
 # This validator returns after oneOf, so every branch must carry the ENTIRE
 # bound schema, never just the conditional fields. Do not relax any sibling
 # fields, citation domains, required keys, enums or additionalProperties.
 complete_schema=deepcopy(context['output_schema'])
 complete_schema['properties']['complete']={'type':'boolean','const':True}
 complete_schema['properties']['checks']['minItems']=len(unit_ids)
 incomplete_schema=deepcopy(context['output_schema'])
 incomplete_schema['properties']['complete']={'type':'boolean','const':False}
 incomplete_schema['properties']['checks']['minItems']=0
 incomplete_schema['properties']['incomplete_reason']={'type':'string','minLength':1,'pattern':r'[\s\S]*\S[\s\S]*'}
 context['output_schema']['oneOf']=[complete_schema,incomplete_schema]
 context['rules']+='\n'+BINDING_COPY_GUIDANCE
 context['omission_contract_sha256']=contract_hash()
 context['complete_review_protocol']=VERSION
 context['repairable_omission_targets']=[{'id':u['id'],'kind':u['kind'],
  'raw_text_sha256':legacy.text_hash(next(n['text'] for n in deliverable['raw_document']['nodes'] if n['id']==u['id'])),
  'owner_id':u['owner_id']} for u in deliverable['units'] if u['kind'] in REPAIRABLE]
 return {**request,'input_sha256':legacy.digest(request)}

def _refs(refs,source,*,personal,required_prefix=None):
 if not isinstance(refs,list) or not refs:raise ValueError('omission_exact_evidence_required')
 locations=[]
 for ref in refs:
  if not isinstance(ref,dict) or set(ref)!={'source_id','quote'} or not isinstance(ref['quote'],str) or not ref['quote'].strip():
   raise ValueError('omission_exact_quote_required')
  if required_prefix and not ref['source_id'].startswith(required_prefix):raise ValueError('omission_importance_evidence_domain')
  loc=locate(source['material_text'],ref,source['jd_text'],personal=personal)
  if loc['status']!='unique':raise ValueError('omission_unlocatable_or_disallowed_reference:'+loc['status'])
  locations.append({'reference':deepcopy(ref),'location':loc})
 return locations

def audit_review(deliverable,receipt,source,runtime_date_basis,*,require_v2=False):
 if receipt is None:
  result=legacy.audit_review(deliverable,None,source,runtime_date_basis)
  return {**result,'review_report_version':VERSION,'source_coverage_reviewed':False,
   'source_coverage_status':'not_reviewed','important_omissions':[]}
 if not isinstance(receipt,dict):raise ValueError('review_receipt_fields')
 if receipt.get('schema_version')==legacy.VERSION:
  if require_v2:raise ValueError('new_workflow_requires_source_coverage_review_v2')
  result=legacy.audit_review(deliverable,receipt,source,runtime_date_basis)
  return {**result,'review_report_version':legacy.VERSION,'source_coverage_reviewed':False,
   'source_coverage_status':'not_in_legacy_contract','important_omissions':[],
   'legacy_completed_review_not_upgraded':True}
 if receipt.get('schema_version')!=VERSION or set(receipt)!=legacy.RECEIPT_KEYS|EXTRA_KEYS:raise ValueError('omission_review_receipt_fields')
 if receipt['omission_contract_sha256']!=contract_hash():raise ValueError('stale_omission_review_contract')
 if not isinstance(receipt['source_coverage_note'],str) or not receipt['source_coverage_note'].strip():raise ValueError('source_coverage_judgment_required')
 old={k:deepcopy(v) for k,v in receipt.items() if k not in EXTRA_KEYS};old['schema_version']=legacy.VERSION
 result=legacy.audit_review(deliverable,old,source,runtime_date_basis)
 if not isinstance(receipt['important_omissions'],list):raise ValueError('important_omissions_list_required')
 units={u['id']:u for u in deliverable['units']};nodes={n['id']:n for n in deliverable['raw_document']['nodes']};checks={c['id']:c for c in receipt['checks']}
 omissions=[];seen=set()
 for index,item in enumerate(receipt['important_omissions']):
  if not isinstance(item,dict) or set(item)!=OMISSION_KEYS:raise ValueError('important_omission_fields')
  finding_key=legacy.digest(item)
  if finding_key in seen:raise ValueError('duplicate_omission_finding')
  seen.add(finding_key)
  for key in ['importance_reason','current_coverage_explanation','target_fit_reason']:
   if not isinstance(item[key],str) or not item[key].strip():raise ValueError('omission_reason_required:'+key)
  if item['importance_basis'] not in ['job_relevance','explicit_material_requirement']:raise ValueError('omission_importance_basis')
  fact_locations=_refs(item['source_evidence'],source,personal=True,required_prefix='M:')
  importance_locations=_refs(item['importance_evidence'],source,personal=False,
   required_prefix='JD:' if item['importance_basis']=='job_relevance' else 'M:')
  rel=item['reviewed_context_unit_ids']
  if not isinstance(rel,list) or not rel or any(not isinstance(i,str) or i not in units for i in rel) or len(rel)!=len(set(rel)):
   raise ValueError('omission_current_context_units_required')
  target=item['target_id'];scope_reason=None
  if target is None:
   if item['target_text_sha256'] is not None:raise ValueError('omission_null_target_hash_required')
   scope_reason='no_existing_same_source_repair_target'
  else:
   if target not in units or units[target]['kind'] not in REPAIRABLE or target not in nodes:raise ValueError('omission_target_not_existing_repairable_unit')
   if item['target_text_sha256']!=legacy.text_hash(nodes[target]['text']):raise ValueError('stale_omission_target_text')
   if target not in rel:raise ValueError('omission_target_not_in_reviewed_context')
   # Guard against selecting another entry as a convenient carrier. This is
   # same-source-block linkage only, not proof that the target is semantically right.
   owners={target,units[target]['owner_id']}
   target_blocks={ref['source_id'] for i in owners if i in checks for ref in checks[i]['evidence'] if ref['source_id'].startswith('M:')}
   if not target_blocks.intersection(ref['source_id'] for ref in item['source_evidence']):
    scope_reason='omission_target_lacks_reviewed_same_source_context'
  omissions.append({**deepcopy(item),'index':index,'citation_locations':fact_locations,
   'importance_locations':importance_locations,'scope_resolved':scope_reason is None,
   'scope_unresolved_reason':scope_reason,'reviewer_judgment_not_automatic_truth':True})
 if omissions:
  result['passed']=False;result['delivery_ready']=False;result['status']='needs_deliverable_review'
  result['blocking_findings']+= [{'unit_id':x['target_id'],'reason':'important_source_omission',
   'omission_index':x['index'],'next_step':'Review the explicit omission and its source/target scope; propose a bounded PATCH only if scope is resolved, then re-review the whole updated candidate.'} for x in omissions]
 return {**result,'review_sha256':legacy.digest(receipt),'review_report_version':VERSION,
  'source_coverage_reviewed':result['coverage_complete'],
  'source_coverage_status':'incomplete' if not result['coverage_complete'] else 'important_omissions_reported' if omissions else 'reviewer_reports_no_important_omissions',
  'source_coverage_note':receipt['source_coverage_note'],'important_omissions':omissions,
  'omission_contract_sha256':contract_hash(),'automatic_source_truth_certified':False}
