"""Complete deliverable source-review seam. No transport or automatic truth claim.

Caller owns the generation/patch callbacks. All source, runtime and document
bindings are exact; source citations certify location, not entailment.
"""
from collections import defaultdict, Counter
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import re

# Bind the loaded implementation, not a later on-disk edit in a long-running process.
_MODULE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

VERSION = 'complete-deliverable-review-v1'
AUX_PATCH_VERSION = 'deliverable-auxiliary-patch-v1'
AUX_FIELDS = ('selection_notes', 'necessary_questions', 'optional_questions')
AUX_KINDS = {'selection_notes': 'selection_note', 'necessary_questions': 'necessary_question',
             'optional_questions': 'optional_question'}
GENERATION_CONSISTENCY_GUIDANCE = (
    'Review the whole deliverable, including identity, school/employer/project titles, labels, dates, '
    'selection_notes and questions. Keep actor, approval object and counted carrier/stage with their '
    'own evidence; do not move a sibling deliverable under a different task. Unreported credentials '
    'or skills do not establish their absence. Do not infer native language, leadership, pay or placement '
    'status. Calibrate strength against demonstrated use; an adjective such as Proficient is not by '
    'itself a contradiction. Unresolved start dates stay unresolved in the body, not just in notes. '
    'Notes claiming a detail was omitted or retained must match the actual output. Questions must not '
    'smuggle in an unsupported premise; optional questions are not required blockers. Use only the '
    'supplied runtime date for calendar comparisons, and never infer enrollment, completion or future '
    'status from a calendar alone. Text-only notes cannot establish layout or visual acceptance.'
)
CLASSIFICATION_GUIDANCE = (
    '\nClassification matrix: nonempty name, entry and date units must be personal_fact. '
    'A nonempty body must be personal_fact or genuine application_intent, never process_claim. '
    'A supported personal fact requires original M: material evidence. Every evidence reference '
    'for a personal_fact check or a nonempty name/entry/date/label must be M:, not JD:, including '
    'mixed M:/JD: lists. A nonempty topic label may be non_assertive only if it makes no factual '
    'assertion, but it still needs M: evidence supporting its topic; generic-looking labels are '
    'not evidence-exempt. Cite the underlying source-supported owner activity; the generic label '
    'words need not occur verbatim in the material, but any supplied quote must locate exactly. '
    'Do not invent personal support from job requirements. '
    'Use process_claim for actual workflow or output-selection assertions, not resume body facts. '
    'A supported process_claim needs source evidence or related_unit_ids identifying its current '
    'output basis; its source_judgment cannot be non_assertive. A genuinely nonassertive state '
    'or decoration uses assertion_type=non_assertive and source_judgment=non_assertive, with an '
    'explanation. Genuine questions may use question/non_assertive only after checking premises. '
    'For every selection_note, necessary_question, optional_question and state, explicitly judge '
    'context_consistency as consistent, contradicted or ambiguous, never not_applicable. '
    'Internal notes are not new evidence: personal assertions in notes and question premises '
    'still require original personal-material support. Calling a claim internal or process_claim '
    'does not exempt its personal facts; JD: may establish job relevance, not those facts. '
    'A safely empty date makes no date assertion: explain it as non_assertive rather than '
    'missing_support merely because it is empty. Independently assess any genuinely important '
    'source omission against the whole visible resume, without inventing dates. '
    'Return exactly one check for each required_unit_ids entry, including empty dates, labels, '
    'notes, questions and state; copy each matching unit ID and text_sha256 exactly. Do not '
    'merge units, reuse a hash from another unit, substitute a sibling ID, or skip apparent '
    'metadata. Check the exact ID set and per-unit hashes before declaring complete=true. '
    'If work is unfinished, use complete=false with a nonempty string incomplete_reason and '
    'report the checks actually completed; never fabricate checks just to meet a count. '
    'For complete=true, use an empty string or null incomplete_reason. Null is not allowed '
    'when complete=false; complete describes review completion, not candidate correctness.'
)
READY_STATE_GUIDANCE = (
    'Generation state ready means that no necessary user question is pending. '
    'It is not certification that all candidate statements passed factual review. '
    'Assess body defects separately; do not classify ready as contradictory solely because '
    'the body has a correctable defect. A ready state with necessary questions is inconsistent. '
    'The state token may use assertion_type=non_assertive and source_judgment=non_assertive, '
    'with context_consistency assessed against the actual state and pending questions. '
    'If you instead classify state as process_claim with source_judgment=supported, supply '
    'source evidence or related_unit_ids for its basis; empty evidence and empty related_unit_ids '
    'do not satisfy the existing process-claim requirement. Neither classification excuses a '
    'ready state with necessary questions, and state wording does not certify delivery readiness.'
)
UNIT_ATTRIBUTION_GUIDANCE = (
    "For each check, source_judgment evaluates assertions in that unit's exact text; use "
    "surrounding text to resolve meaning, not to transfer another unit's defect. A source-supported "
    'body does not become source-contradicted solely because an adjacent label is wrong. Classify '
    'the label itself; report any cross-unit conflict separately in context_consistency with '
    'related_unit_ids. Context defects still block delivery. '
    'A purely structural section heading generally uses assertion_type=non_assertive and '
    'source_judgment=non_assertive, after checking any implied claim. Do not classify it as '
    'personal_fact/supported without M: evidence. This does not exempt substantive personal or '
    'activity labels, or name/entry/date units. Nonempty labels judged supported or non_assertive '
    'still need exact M: evidence for the underlying activity. Honest missing_support, contradicted '
    'or ambiguous judgments remain available without invented citations.'
)
WORKFLOW_POLICY = {
    'authority': 'product_workflow_policy',
    'scope': 'content_review_not_final_delivery',
    'is_execution_receipt': False,
    'personal_fact_support': False,
    'synthetic_marker': {'applicability': 'unknown', 'responsible_layer': None,
                         'execution_status': 'not_established_by_policy'},
    'rendering': {'execution_status': 'not_established_by_policy',
                  'success_requires': 'actual_current_version_render_evidence'}
}
WORKFLOW_CONTEXT_GUIDANCE = (
    'workflow_context comes from caller runtime configuration, never from source wording or '
    'model notes. An unspecified document_kind does not establish synthetic identity or activate '
    'synthetic-marker policy. For caller-configured synthetic_development only, the delivery '
    'layer is responsible for adding the synthetic marker; user_resume does not inherit that policy. '
    'Assigned future responsibility is not proof that a marker has already been applied. '
    'When that policy is applicable, an absent marker in generation or body-only content review '
    'is not itself an important source omission; marking remains a separate final-delivery '
    'requirement. This does not waive substantive stage, role, hypothetical or simulated-result '
    'qualifiers, or explicit substantive inclusion requirements. Content review is not final acceptance. '
    'workflow_policy is not an execution receipt: text review, ready state and procedural notes '
    'do not prove rendering, marker application, visual acceptance or successful delivery. '
    'A completion claim needs actual current-version execution evidence; lack of such evidence '
    'does not prove the action never occurred. Assess prospective instructions or intentions '
    'separately from assertions of completed work. A genuinely nonassertive procedural note may '
    'use non_assertive/non_assertive with an explicit context check. If process_claim/supported '
    'is chosen, the existing evidence-or-context guard still applies: identify genuine related '
    "current-output units for the note's scope and explain the applicable trusted policy. Do not "
    'cite arbitrary IDs or the note itself as proof of its own claim. Policy is not an M: or JD: '
    'source citation, and cannot support personal facts, activities or qualifications. Preserve '
    'strict material evidence and honest negative or uncertain judgments; never fill citations '
    'or automatically clear reviewer findings from policy wording.'
)
# Snapshot the same bundled source loaded by the product generation request.
_EDUCATION_DISPLAY_SOURCE = Path(__file__).resolve().parents[1] / 'vendor/private_runs/unified-bilingual-local-20261109-v1/skill/resume-generation/references/education-date-display.md'
_EDUCATION_DISPLAY_TEXT = _EDUCATION_DISPLAY_SOURCE.read_text(encoding='utf-8')
_EDUCATION_DATE_SECTION, _EDUCATION_SECTION_BOUNDARY, _ = _EDUCATION_DISPLAY_TEXT.partition('\n## 模块顺序')
if not _EDUCATION_SECTION_BOUNDARY:
    raise ValueError('education_display_policy_section_boundary_missing')
EDUCATION_DISPLAY_POLICY = {
    'authority': 'product_format_policy',
    'scope': 'education_date_display_only',
    'source_file': 'references/education-date-display.md',
    'source_file_sha256': hashlib.sha256(_EDUCATION_DISPLAY_SOURCE.read_bytes()).hexdigest(),
    'source_text_sha256': hashlib.sha256(_EDUCATION_DISPLAY_TEXT.encode('utf-8')).hexdigest(),
    'date_display_text': _EDUCATION_DATE_SECTION.strip(),
    'personal_fact_support': False,
    'is_personal_user_preference': False,
    'is_execution_receipt': False
}
EDUCATION_DISPLAY_GUIDANCE = (
    'education_display_policy is the actual product formatting default from the same bundled '
    'source used for generation, not personal material or a claim about this user. For a '
    'source-confirmed graduate, separately displaying an award or graduation date is optional '
    'under that default. Source-supported study ranges may remain. Explicit user, JD or '
    'application-form requirements for a date override the optional display default and still '
    'require evidence for that exact event. The policy proves no degree, graduation, enrollment, '
    'date or conferral fact, and never permits substituting one date event for another. '
    'Expected graduation display requires source-confirmed current enrollment and an actually '
    'provided expected date; do not infer status from a calendar or fabricate missing dates. '
    'Assess a procedural note about following the product default against the actual whole '
    'visible output and genuine related unit IDs. Do not require personal M: evidence merely '
    'to establish this product rule, but every personal assertion still needs its existing '
    'material support. The rule is not evidence that the user personally requested a preference, '
    'that a claimed omission/edit actually happened, or that rendering/delivery succeeded. '
    'Do not broaden it into a ban on all education dates or remove meaningful qualification '
    'limits. Keep the supported-process evidence-or-context guard; policy is not a new citation '
    'domain. Independently judge source facts, explicit requirements and actual coverage; never '
    'automatically clear an existing reviewer finding because policy words are present.'
)
REVIEW_GUIDANCE = GENERATION_CONSISTENCY_GUIDANCE + (
    '\nIndependently review every required unit ID, even empty dates, identity/education headings and '
    'generic topic labels. Inspect all assertions and their actor, action, status, quantity/carrier, '
    'time, qualification and context. Mark genuine questions or pure decoration non_assertive only '
    'after checking their implicit premises. Review each note/question against both original material '
    'and the complete current body; notes are not new evidence. Supply related unit IDs for claims '
    'about the current output. Distinguish unsupported strengthening, contradiction, ambiguity, safe '
    'omission and nonblocking wording advice. A school/identity title is not exempt because it looks '
    'like a label. Personal support must cite M: material, not JD requirements. Explain nonpositive '
    'judgments and non_assertive classifications. Report incomplete review explicitly rather than '
    'dropping units. A complete supported reviewer report still is not automatic factual truth.'
) + CLASSIFICATION_GUIDANCE + '\n' + READY_STATE_GUIDANCE + '\n' + UNIT_ATTRIBUTION_GUIDANCE + '\n' + WORKFLOW_CONTEXT_GUIDANCE + '\n' + EDUCATION_DISPLAY_GUIDANCE

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()

def text_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def _source(source):
    if not isinstance(source, dict) or set(source) != {'case_id','source_language','material_text','jd_text'}:
        raise ValueError('four_key_source_required')
    if any(not isinstance(v,str) for v in source.values()) or not source['material_text'].strip():
        raise ValueError('source_text_required')
    return {'source_case_sha256':digest(source),'source_sha256':text_hash(source['material_text']),
            'jd_sha256':text_hash(source['jd_text'])}

def _runtime(value):
    keys={'as_of_date','timezone','authority','observed_at'}
    if not isinstance(value,dict) or set(value)!=keys: raise ValueError('complete_runtime_date_basis_required')
    if value['as_of_date'] is None:
        if value!={'as_of_date':None,'timezone':None,'authority':'unknown','observed_at':None}:
            raise ValueError('unknown_runtime_basis_mismatch')
    else:
        if value['authority']!='caller_supplied_runtime_clock': raise ValueError('runtime_authority_required')
        if not isinstance(value['as_of_date'],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value['as_of_date']):
            raise ValueError('iso_runtime_date_required')
        if not isinstance(value['observed_at'],str)or not isinstance(value['timezone'],str):
            raise ValueError('complete_runtime_clock_fields_required')
        try:
            date.fromisoformat(value['as_of_date'])
            dt=datetime.fromisoformat(value['observed_at'].replace('Z','+00:00'))
            if dt.tzinfo is None: raise ValueError('aware_runtime_instant_required')
            if dt.astimezone(ZoneInfo(value['timezone'])).date().isoformat()!=value['as_of_date']:
                raise ValueError('runtime_date_clock_mismatch')
        except (KeyError,TypeError)as exc:
            raise ValueError('invalid_runtime_clock_or_timezone')from exc
    return deepcopy(value)

def _generation(generation, doc):
    from resume_controls import document as d
    keys={'schema_version','resume','state','necessary_questions','optional_questions','selection_notes'}
    if not isinstance(generation,dict) or set(generation)!=keys: raise ValueError('complete_generation_required')
    from resume_controls.schemas import VERSION as CONTROLLED_VERSION
    if generation['schema_version']!=CONTROLLED_VERSION: raise ValueError('generation_schema_mismatch')
    d.validate(doc)
    if generation['resume']!=d.to_resume(doc): raise ValueError('generation_document_mismatch')
    if generation['state']not in ('ready','awaiting_user'): raise ValueError('generation_state_invalid')
    for key in AUX_FIELDS:
        if not isinstance(generation[key],list) or any(not isinstance(x,str)for x in generation[key]):
            raise ValueError('auxiliary_string_list_required:'+key)

def _unit(ident,kind,text,path,owner=None):
    return {'id':ident,'kind':kind,'text':text,'text_sha256':text_hash(text),
            'path':path,'owner_id':owner}

def _units(generation,doc):
    result=[]
    for n in doc['nodes']:
        match=re.fullmatch(r'\*\*([^*\r\n]+?)[：:]\*\*\s*(.+)',n['text'],re.S)if n['kind']=='sentence'else None
        body=match.group(2)if match else n['text']
        result.append(_unit(n['id'],'body'if n['kind']=='sentence'else n['kind'],body,
            ['document',n['id'],'text'],n['parent']))
        if match:
            result.append(_unit('l_'+digest({'document':doc['document_id'],'owner':n['id']})[:20],
                'label',match.group(1),['label',n['id']],n['id']))
    # Content + duplicate ordinal makes unchanged auxiliary units stable across
    # reordering/body revisions. Edits receive new identity; stale receipts still
    # cannot be rebound because the complete deliverable version also changes.
    for field in AUX_FIELDS:
        seen=Counter()
        for index,text in enumerate(generation[field]):
            ordinal=seen[text];seen[text]+=1
            ident='a_'+digest({'document':doc['document_id'],'field':field,'text':text,'duplicate':ordinal})[:20]
            result.append(_unit(ident,AUX_KINDS[field],text,['generation',field,index]))
    result.append(_unit('a_'+digest({'document':doc['document_id'],'field':'state'})[:20],
        'state',generation['state'],['generation','state']))
    if len({x['id']for x in result})!=len(result):raise ValueError('unit_id_collision')
    return result

def build_deliverable(generation, raw_document, source, runtime_date_basis, *, previous=None, document_kind=None):
    from resume_controls import document as d
    _generation(generation,raw_document);bindings=_source(source);runtime=_runtime(runtime_date_basis)
    d.validate_intent_context(raw_document,source['jd_text'])
    if previous is not None and previous['raw_document']['document_id']!=raw_document['document_id']:
        raise ValueError('previous_document_identity_changed')
    if document_kind is None:
        document_kind=previous.get('workflow_context',{}).get('document_kind','unspecified') if previous is not None else 'unspecified'
    if document_kind not in ('unspecified','synthetic_development','user_resume'):
        raise ValueError('explicit_supported_document_kind_required')
    workflow_context={'authority':'caller_runtime_configuration','document_kind':document_kind}
    value={'schema_version':VERSION,'document_version':d.version(raw_document),
        'workflow_context':workflow_context,
        'generation_sha256':digest(generation),'review_contract_sha256':review_contract_hash(),
        **bindings,'runtime_date_basis':runtime,
        'runtime_sha256':digest(runtime),'raw_document':deepcopy(raw_document),
        'generation':deepcopy(generation),'units':_units(generation,raw_document)}
    return {**value,'version':digest(value)}

def _validate(deliverable,source,runtime):
    expected=build_deliverable(deliverable['generation'],deliverable['raw_document'],source,runtime,
        document_kind=deliverable.get('workflow_context',{}).get('document_kind'))
    if deliverable!=expected: raise ValueError('deliverable_source_runtime_or_content_changed')
    return expected

CHECK_KEYS={'id','text_sha256','assertion_type','source_judgment','context_consistency',
            'evidence','related_unit_ids','note'}
RECEIPT_KEYS={'schema_version','deliverable_version','source_sha256','jd_sha256','runtime_sha256',
              'checks','complete','incomplete_reason'}
JUDGMENTS=['supported','contradicted','missing_support','ambiguous','non_assertive']
CONSISTENCY=['consistent','contradicted','ambiguous','not_applicable']
ASSERTIONS=['personal_fact','process_claim','application_intent','question','non_assertive']
REF_SCHEMA={'type':'object','additionalProperties':False,'properties':{'source_id':{'type':'string','pattern':r'^(M|JD):L[0-9]{4,}$'},'quote':{'type':'string','minLength':1}},'required':['source_id']}
CHECK_SCHEMA={'type':'object','additionalProperties':False,'properties':{
    'id':{'type':'string'},'text_sha256':{'type':'string'},
    'assertion_type':{'type':'string','enum':ASSERTIONS},
    'source_judgment':{'type':'string','enum':JUDGMENTS},
    'context_consistency':{'type':'string','enum':CONSISTENCY},
    'evidence':{'type':'array','items':REF_SCHEMA},'related_unit_ids':{'type':'array','items':{'type':'string'}},
    'note':{'type':'string'}},'required':sorted(CHECK_KEYS)}
REVIEW_SCHEMA={'type':'object','additionalProperties':False,'properties':{
    'schema_version':{'const':VERSION},'deliverable_version':{'type':'string'},
    'source_sha256':{'type':'string'},'jd_sha256':{'type':'string'},'runtime_sha256':{'type':'string'},
    'checks':{'type':'array','items':CHECK_SCHEMA},'complete':{'type':'boolean'},
    'incomplete_reason':{'oneOf':[{'type':'string'},{'type':'null'}],
        'description':'Null is permitted only when complete=true; incomplete reviews require a nonempty string. The audit enforces this conditional constraint.'}},'required':sorted(RECEIPT_KEYS)}


def review_contract_hash():
    """Bind actual loaded code, schema and review guidance; no truth guarantee."""
    return digest({'module_sha256':_MODULE_SHA256,'review_schema':REVIEW_SCHEMA,
                   'review_guidance':REVIEW_GUIDANCE,'education_display_policy':EDUCATION_DISPLAY_POLICY})


def build_review_request(deliverable, source, runtime_date_basis):
    from resume_controls.citations import wire_blocks
    _validate(deliverable,source,runtime_date_basis)
    policy=deepcopy(WORKFLOW_POLICY)
    kind=deliverable['workflow_context']['document_kind']
    policy['synthetic_marker']['applicability']={'unspecified':'unknown','synthetic_development':'applicable','user_resume':'not_applicable'}[kind]
    if kind=='synthetic_development':policy['synthetic_marker']['responsible_layer']='delivery'
    context={'rules':REVIEW_GUIDANCE,'deliverable':deepcopy(deliverable),
        'workflow_context':deepcopy(deliverable['workflow_context']),'workflow_policy':policy,
        'education_display_policy':deepcopy(EDUCATION_DISPLAY_POLICY),
        'required_unit_ids':[x['id']for x in deliverable['units']],
        'source_blocks':wire_blocks(source['material_text'],source['jd_text']),
        'runtime_date_basis':deepcopy(runtime_date_basis),'output_schema':deepcopy(REVIEW_SCHEMA),
        'semantic_truth_automatically_certified':False}
    value={'stage':'deliverable_review','context':context}
    return {**value,'input_sha256':digest(value)}

def audit_review(deliverable, receipt, source, runtime_date_basis):
    from resume_controls.citations import locate
    _validate(deliverable,source,runtime_date_basis)
    units={x['id']:x for x in deliverable['units']}
    if receipt is None:
        return {'passed':False,'delivery_ready':False,'coverage_complete':False,
                'missing_ids':list(units),'missing_unit_ids':list(units),
                'blocking_findings':[{'unit_id':i,'reason':'not_reviewed','next_step':'Review this unit against source and current context.'}for i in units],
                'preview_allowed':True,'status':'needs_deliverable_review',
                'semantic_truth_automatically_certified':False}
    if not isinstance(receipt,dict)or set(receipt)!=RECEIPT_KEYS:raise ValueError('review_receipt_fields')
    bindings={'schema_version':VERSION,'deliverable_version':deliverable['version'],
        'source_sha256':deliverable['source_sha256'],'jd_sha256':deliverable['jd_sha256'],
        'runtime_sha256':deliverable['runtime_sha256']}
    if any(receipt[k]!=v for k,v in bindings.items()):raise ValueError('stale_or_mismatched_review_binding')
    if type(receipt['complete'])is not bool or not (isinstance(receipt['incomplete_reason'],str)or (receipt['complete'] is True and receipt['incomplete_reason'] is None)):raise ValueError('review_completeness_fields')
    if not receipt['complete']and not receipt['incomplete_reason'].strip():raise ValueError('incomplete_review_needs_reason')
    if not isinstance(receipt['checks'],list):raise ValueError('review_checks_list_required')
    seen=set();locations=[];defects=[];ambiguities=[]
    for check in receipt['checks']:
        if not isinstance(check,dict)or set(check)!=CHECK_KEYS:raise ValueError('review_check_fields')
        ident=check['id']
        if ident not in units:raise ValueError('unknown_review_unit')
        if ident in seen:raise ValueError('duplicate_review_unit')
        seen.add(ident);unit=units[ident]
        if check['text_sha256']!=unit['text_sha256']:raise ValueError('review_unit_text_changed')
        if check['assertion_type']not in ASSERTIONS or check['source_judgment']not in JUDGMENTS or check['context_consistency']not in CONSISTENCY:raise ValueError('review_judgment_invalid')
        if not isinstance(check['note'],str)or not check['note'].strip():raise ValueError('review_explanation_required')
        rel=check['related_unit_ids']
        if not isinstance(rel,list)or len(set(rel))!=len(rel)or any(x not in units for x in rel):raise ValueError('related_unit_missing_or_duplicate')
        if not isinstance(check['evidence'],list):raise ValueError('review_evidence_list_required')
        personal=check['assertion_type']=='personal_fact'
        if unit['text'].strip() and unit['kind']in ('name','entry','date') and not personal:
            raise ValueError('identity_heading_date_requires_personal_classification')
        if unit['text'].strip() and unit['kind']=='body' and check['assertion_type']not in ('personal_fact','application_intent'):
            raise ValueError('body_requires_personal_or_intent_classification')
        if unit['kind']in ('name','entry','date','body')and unit['text'].strip()and check['source_judgment']=='non_assertive':
            if unit['kind']!='body'or check['assertion_type']!='application_intent':raise ValueError('identity_or_body_fact_cannot_be_exempted')
        if check['source_judgment']=='non_assertive'and check['assertion_type']not in ('non_assertive','question','application_intent'):
            raise ValueError('nonassertive_classification_mismatch')
        if unit['kind']in ('selection_note','necessary_question','optional_question','state')and check['context_consistency']=='not_applicable':
            raise ValueError('auxiliary_context_check_required')
        needs_material=(personal or unit['kind']in ('name','entry','date','label'))and bool(unit['text'].strip())
        if check['source_judgment']in ('supported','non_assertive')and needs_material and not check['evidence']:
            raise ValueError('personal_support_requires_material_evidence')
        if check['assertion_type']=='process_claim'and check['source_judgment']=='supported'and not check['evidence']and not rel:
            raise ValueError('process_claim_requires_source_or_context_basis')
        for ref in check['evidence']:
            if not isinstance(ref,dict)or not {'source_id'}<=set(ref)<= {'source_id','quote'}:raise ValueError('source_reference_fields')
            if 'quote'in ref and (not isinstance(ref['quote'],str)or not ref['quote']):raise ValueError('empty_source_quote')
            loc=locate(source['material_text'],ref,source['jd_text'],personal=needs_material)
            if loc['status']!='unique':raise ValueError('unlocatable_or_disallowed_source_reference:'+loc['status'])
            locations.append({'unit_id':ident,'reference':deepcopy(ref),'location':loc})
        if check['source_judgment']in ('contradicted','missing_support')or check['context_consistency']=='contradicted':defects.append(ident)
        if check['source_judgment']=='ambiguous'or check['context_consistency']=='ambiguous':ambiguities.append(ident)
    missing=sorted(set(units)-seen);complete=bool(receipt['complete']and not receipt['incomplete_reason']and not missing)
    contract_issues=[];gen=deliverable['generation']
    if gen['state']=='ready'and gen['necessary_questions']:contract_issues.append('ready_with_necessary_questions')
    passed=bool(complete and not defects and not ambiguities and not contract_issues)
    awaiting=gen['state']=='awaiting_user'or bool(gen['necessary_questions'])
    return {'passed':passed,'delivery_ready':passed and not awaiting,'coverage_complete':complete,
        'status':'awaiting_user'if passed and awaiting else'reviewer_reports_supported'if passed else'needs_deliverable_review',
        'deliverable_version':deliverable['version'],'review_sha256':digest(receipt),
        'reviewed_ids':sorted(seen),'missing_ids':missing,'missing_unit_ids':missing,
        'blocking_findings':([{'unit_id':None,'reason':'review_declared_incomplete','next_step':'Finish the review; preview remains available.'}]if not receipt['complete']or receipt['incomplete_reason']else[])+([{'unit_id':i,'reason':'not_reviewed','next_step':'Review the missing unit.'}for i in missing]+
            [{'unit_id':i,'reason':'reported_source_or_context_defect','next_step':'Revise only the affected unit using original evidence, then review the new version.'}for i in sorted(set(defects))]+
            [{'unit_id':i,'reason':'reported_ambiguity','next_step':'Clarify or safely omit the unresolved claim while retaining supported content.'}for i in sorted(set(ambiguities))]+
            [{'unit_id':next(u['id']for u in units.values()if u['kind']=='state'),'reason':reason,'next_step':'Reconcile state with necessary questions, retaining a preview.'}for reason in contract_issues]),
        'preview_allowed':True,'defect_ids':sorted(set(defects)),
        'ambiguous_ids':sorted(set(ambiguities)),'contract_issues':contract_issues,
        'citation_locations':locations,'semantic_truth_automatically_certified':False,
        'reviewer_declarations_not_automatic_entailment':True,'layout_or_visual_pass':False}

AUX_OPERATION_SCHEMA={'type':'object','additionalProperties':False,'properties':{
    'op':{'enum':['replace','delete']},'target_id':{'type':'string'},'original_hash':{'type':'string'},
    'text':{'type':'string'},'reason':{'type':'string'},'source_refs':{'type':'array','minItems':1,'items':REF_SCHEMA}},
    'required':['op','target_id','original_hash','reason','source_refs']}
AUX_PATCH_SCHEMA={'type':'object','additionalProperties':False,'properties':{
    'schema_version':{'const':AUX_PATCH_VERSION},'base_version':{'type':'string'},
    'operations':{'type':'array','minItems':1,'items':AUX_OPERATION_SCHEMA}},
    'required':['schema_version','base_version','operations']}

def apply_auxiliary_patch(deliverable, patch, source, runtime_date_basis):
    from resume_controls.citations import locate
    _validate(deliverable,source,runtime_date_basis)
    if not isinstance(patch,dict)or set(patch)!={'schema_version','base_version','operations'}or patch['schema_version']!=AUX_PATCH_VERSION:raise ValueError('auxiliary_patch_fields')
    if patch['base_version']!=deliverable['version']:raise ValueError('stale_auxiliary_patch')
    if not isinstance(patch['operations'],list)or not patch['operations']:raise ValueError('empty_auxiliary_patch')
    units={x['id']:x for x in deliverable['units']};seen=set();edits=[];locations=[]
    for op in patch['operations']:
        if not isinstance(op,dict)or op.get('op')not in ('replace','delete'):raise ValueError('auxiliary_patch_operation')
        keys={'op','target_id','original_hash','reason','source_refs'}|({'text'}if op['op']=='replace'else set())
        if set(op)!=keys:raise ValueError('auxiliary_operation_fields')
        ident=op['target_id'];unit=units.get(ident)
        if ident in seen:raise ValueError('duplicate_auxiliary_target')
        seen.add(ident)
        if not unit or unit['path'][0]!='generation':raise ValueError('auxiliary_target_not_auxiliary')
        if op['original_hash']!=unit['text_sha256']:raise ValueError('stale_auxiliary_original_hash')
        if not isinstance(op['reason'],str)or not op['reason'].strip():raise ValueError('auxiliary_reason_required')
        if not isinstance(op['source_refs'],list)or not op['source_refs']:raise ValueError('auxiliary_source_references_required')
        for ref in op['source_refs']:
            loc=locate(source['material_text'],ref,source['jd_text'],personal=False)
            if loc['status']!='unique':raise ValueError('auxiliary_reference_not_locatable')
            locations.append({'unit_id':ident,'reference':deepcopy(ref),'location':loc})
        if op['op']=='replace':
            if not isinstance(op['text'],str)or not op['text'].strip():raise ValueError('auxiliary_replacement_text_required')
            if op['text']==unit['text']:raise ValueError('auxiliary_no_op')
            if unit['kind']=='state'and op['text']not in ('ready','awaiting_user'):raise ValueError('auxiliary_state_invalid')
        elif unit['kind']=='state':raise ValueError('cannot_delete_generation_state')
        edits.append((unit,op))
    generation=deepcopy(deliverable['generation'])
    # Apply replacements before descending-position deletes. Each operation is
    # bound to the same original snapshot; a prior delete cannot retarget another.
    for unit,op in edits:
        if op['op']=='replace':
            if unit['kind']=='state':generation['state']=op['text']
            else:generation[unit['path'][1]][unit['path'][2]]=op['text']
    for field in AUX_FIELDS:
        indices=sorted([u['path'][2]for u,o in edits if o['op']=='delete'and u['path'][1]==field],reverse=True)
        for index in indices:del generation[field][index]
    return {'generation':generation,'base_version':deliverable['version'],'changed_ids':sorted(seen),
        'citation_locations':locations,'requires_full_review':True,
        'semantic_truth_automatically_certified':False}

def build_auxiliary_revision_request(deliverable, source, runtime_date_basis, issues=()):
    request=build_review_request(deliverable,source,runtime_date_basis)
    request.pop('input_sha256');request['stage']='auxiliary_revision'
    request['context']['output_schema']=deepcopy(AUX_PATCH_SCHEMA)
    request['context']['issues']=deepcopy(list(issues))
    request['context']['rules']+='\nReturn only source-cited auxiliary replace/delete operations with exact IDs/hashes. Do not alter body or silently clear necessary questions. Full deliverable review is required after any change.'
    return {**request,'input_sha256':digest(request)}
