"""Route explicit, version-validated review findings, never infer factual truth.

Evidence is expanded without truncating the selected original source block. A
located citation is context for the next reviewer/editor, not proof of entailment.
No model calls, repairs, source changes, keyword judgments or external actions.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

VERSION = 'source-review-repair-plan-v1'
_MODULE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
AUX_KINDS = {'selection_note','necessary_question','optional_question','state'}
FACT_KINDS = {'name','entry','date','body','label'}

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
        separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()

def _text_hash(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

def _finish(binding,audit,body,aux,unresolved,*,force_pending=False):
    if force_pending or unresolved:route='needs_review'
    elif body and aux:route='both'
    elif body:route='body_only'
    elif aux:route='auxiliary_only'
    else:route='no_revision_needed'
    result={'schema_version':VERSION,'binding':binding,'route':route,
        'body_feedback':body,'auxiliary_feedback':aux,'unresolved':unresolved,
        'can_dispatch':route in ('body_only','auxiliary_only','both'),
        'audit':audit,'preview_allowed':True,
        'judgment_origin':'supplied_review_receipt','reviewer_identity':'not_specified_by_receipt_protocol',
        'related_units_are_edit_targets':False,'automatic_rewrite_permitted':False,
        'semantic_truth_automatically_certified':False,'final_acceptance':False,
        'dispatch_is_external_action_authorization':False}
    return {**result,'plan_version':digest(result)}

def _binding(deliverable,receipt,source,runtime):
    return {'deliverable_version':deliverable.get('version') if isinstance(deliverable,dict) else None,
        'raw_document_version':deliverable.get('document_version') if isinstance(deliverable,dict) else None,
        'complete_review_contract_sha256':deliverable.get('review_contract_sha256') if isinstance(deliverable,dict) else None,
        'receipt_sha256':digest(receipt),'source_case_sha256':digest(source),
        'runtime_sha256':digest(runtime),'routing_module_sha256':_MODULE_SHA256}

def _expand_evidence(refs,source,catalogue):
    from resume_controls.citations import locate
    result=[]
    for ref in refs:
        # audit_review already enforced whether this particular claim may cite JD.
        loc=locate(source['material_text'],ref,source['jd_text'],personal=False)
        if loc['status']!='unique':raise ValueError('reference_changed_after_review_validation')
        pos=next(i for i,b in enumerate(catalogue)if b['id']==ref['source_id'])
        block=catalogue[pos]
        neighbors=[deepcopy(catalogue[i])for i in [pos-1,pos+1]
            if 0<=i<len(catalogue) and catalogue[i]['source_type']==block['source_type']]
        result.append({'reference':deepcopy(ref),'location':loc,'source_block':deepcopy(block),
            'adjacent_blocks':neighbors,'location_only_not_semantic_proof':True,
            'adjacent_blocks_are_context_not_additional_support':True})
    return result

def _feedback(unit,check,units,nodes,source,catalogue):
    auxiliary=unit['kind']in AUX_KINDS
    target=unit['id'] if auxiliary else unit['owner_id'] if unit['kind']=='label' else unit['id']
    text=unit['text'] if auxiliary else nodes[target]['text']
    related=[deepcopy(units[i])for i in check['related_unit_ids']]
    return {'unit_id':unit['id'],'target_id':target,'unit_kind':unit['kind'],
        'unit_snapshot':deepcopy(unit),'target_domain':'auxiliary' if auxiliary else 'raw_document',
        'original_target_text':text,'original_target_hash':_text_hash(text),
        'source_judgment':check['source_judgment'],'context_consistency':check['context_consistency'],
        'assertion_type':check['assertion_type'],'reviewer_note':check['note'],
        'evidence':_expand_evidence(check['evidence'],source,catalogue),'related_units':related,
        'related_units_are_edit_targets':False,'preserve_units':[],
        'review_question':'Resolve the reported issue using the original source and current context. '+check['note'],
        'suggested_replacement':None,'semantic_truth_automatically_certified':False}

def build_repair_plan(deliverable,receipt,source,runtime_date_basis):
    """Return a bound routing plan from a valid complete review.

    can_dispatch means a constrained editing callback has grounded review input,
    not that the proposed result is correct, approved, or final. Unknown facts
    require source review/clarification, never automatic wording invention.
    """
    from omission_review import audit_review
    from resume_controls.citations import catalogue
    binding=_binding(deliverable,receipt,source,runtime_date_basis)
    try:
        audit=audit_review(deliverable,receipt,source,runtime_date_basis)
    except (ValueError,KeyError,TypeError) as exc:
        return _finish(binding,{'passed':False,'delivery_ready':False,'receipt_valid':False,
            'error':str(exc)},[],[],[{'unit_id':None,'risk_kind':'invalid_or_stale_review',
            'why':str(exc),'review_question':'Rebuild or complete a review for the exact current source, runtime and deliverable.'}],force_pending=True)
    units={u['id']:u for u in deliverable['units']};nodes={n['id']:n for n in deliverable['raw_document']['nodes']}
    unresolved=[];body=[];aux=[]
    if receipt is None:
        for ident in audit['missing_unit_ids']:
            unresolved.append({'unit_id':ident,'unit_snapshot':deepcopy(units[ident]),
                'risk_kind':'not_reviewed','why':'No matching reviewer judgment; this is not an unsupported-fact verdict.',
                'review_question':'Review this unit against original source before proposing an edit.'})
        return _finish(binding,audit,[],[],unresolved,force_pending=True)
    blocks=catalogue(source['material_text'],source['jd_text'])
    for check in receipt['checks']:
        unit=units[check['id']];judgment=check['source_judgment'];consistency=check['context_consistency']
        if judgment not in ('contradicted','missing_support','ambiguous') and consistency not in ('contradicted','ambiguous'):
            continue
        item=_feedback(unit,check,units,nodes,source,blocks)
        refs=bool(item['evidence']);other_context=any(x['id']!=unit['id']for x in item['related_units'])
        # A workflow note is not a personal fact. Existing contradictory process
        # assertions may be removed/reframed, but cannot be replaced by an invented
        # rendering or acceptance event even when the source judgment is ambiguous.
        process_only=(unit['kind']=='selection_note' and check['assertion_type']in ('process_claim','non_assertive')
            and consistency=='contradicted' and other_context)
        if process_only:
            item['risk_kind']='reviewer_reported_process_note_inconsistency'
            item['resolution_policy']='remove_or_reframe_nonassertively_no_new_workflow_facts'
            item['review_question']='Remove or non-assertively reframe the reported process-note inconsistency. Do not invent a rendering, approval or acceptance event. '+check['note']
            aux.append(item);continue
        if judgment=='ambiguous' or consistency=='ambiguous':
            item['risk_kind']='reviewer_reported_ambiguity'
            item['resolution_policy']='source_review_or_clarification_before_edit'
            unresolved.append(item);continue
        grounded=refs or (unit['kind']in AUX_KINDS and consistency=='contradicted' and other_context)
        if not grounded:
            item['risk_kind']='review_finding_without_locatable_basis'
            item['resolution_policy']='locate_source_or_context_before_edit'
            item['review_question']='The review flags a problem but supplies no usable source/context basis. Locate evidence or clarify; do not invent a correction. '+check['note']
            unresolved.append(item);continue
        item['risk_kind']=('reviewer_reported_context_contradiction' if consistency=='contradicted'
            else 'reviewer_reported_source_contradiction' if judgment=='contradicted'
            else 'reviewer_reported_missing_support')
        item['resolution_policy']='propose_source_grounded_revision_then_full_rereview'
        (aux if unit['kind']in AUX_KINDS else body).append(item)
    for omission in audit.get('important_omissions',[]):
        target=omission['target_id']
        if not omission['scope_resolved']:
            unresolved.append({'unit_id':target,'risk_kind':'important_omission_without_safe_target',
                'why':omission['scope_unresolved_reason'],'omission':deepcopy(omission),
                'review_question':'Resolve same-source existing target context before editing; do not create structure or move a fact to an unrelated entry.'})
            continue
        unit=units[target]
        body.append({'unit_id':target,'target_id':target,'unit_kind':unit['kind'],
            'unit_snapshot':deepcopy(unit),'target_domain':'raw_document',
            'original_target_text':nodes[target]['text'],'original_target_hash':_text_hash(nodes[target]['text']),
            'source_judgment':'reviewer_reported_important_omission','context_consistency':'existing_unit_judgment_unchanged',
            'assertion_type':'reviewer_coverage_diagnosis','reviewer_note':omission['current_coverage_explanation'],
            'evidence':_expand_evidence(omission['source_evidence'],source,blocks),
            'importance_evidence':_expand_evidence(omission['importance_evidence'],source,blocks),
            'importance_reason':omission['importance_reason'],'target_fit_reason':omission['target_fit_reason'],
            'related_units':[deepcopy(units[i]) for i in omission['reviewed_context_unit_ids'] if i!=target],
            'related_units_are_edit_targets':False,'preserve_units':[],
            'risk_kind':'reviewer_reported_important_source_omission','allowed_operations':['replace'],
            'resolution_policy':'source_grounded_existing_target_replace_then_complete_rereview',
            'review_question':'Address only the explicitly reported important omission in this existing target. Preserve all supported facts, date-event roles and qualifiers; do not infer missing facts. '+omission['current_coverage_explanation'],
            'suggested_replacement':None,'semantic_truth_automatically_certified':False})
    # Protect the counterpart when only a raw bullet's label or body was flagged.
    affected={x['unit_id']for x in body}
    for item in body:
        target=item['target_id']
        item['preserve_units']=[deepcopy(u)for u in units.values()
            if (u['id']==target or u['kind']=='label'and u['owner_id']==target)and u['id']not in affected]
    for ident in audit.get('missing_unit_ids',[]):
        unresolved.append({'unit_id':ident,'unit_snapshot':deepcopy(units[ident]),
            'risk_kind':'not_reviewed','why':'A required unit has no judgment.',
            'review_question':'Complete the current review before any editing callback.'})
    if not receipt['complete']or receipt['incomplete_reason']:
        unresolved.append({'unit_id':None,'risk_kind':'incomplete_review',
            'why':receipt['incomplete_reason']or'Reviewer declared incomplete.',
            'review_question':'Finish the review; do not treat the existing subset as complete.'})
    for issue in audit.get('contract_issues',[]):
        unresolved.append({'unit_id':None,'risk_kind':'generation_state_contract',
            'why':issue,'review_question':'Reconcile state with necessary questions without deleting unresolved questions merely to declare readiness.'})
    if not body and not aux and audit.get('passed') and not audit.get('delivery_ready'):
        for u in units.values():
            if u['kind']=='necessary_question':
                unresolved.append({'unit_id':u['id'],'unit_snapshot':deepcopy(u),'risk_kind':'awaiting_user_input',
                    'why':'Source review accepted the safe draft, but required input is still outstanding.',
                    'review_question':u['text']})
    if not body and not aux and audit.get('passed') and not audit.get('delivery_ready') and not unresolved:
        unresolved.append({'unit_id':None,'risk_kind':'awaiting_user_state_without_question',
            'why':'The candidate is awaiting_user; there is no explicit required question to dispatch.',
            'review_question':'Clarify the outstanding input or state before treating the draft as ready.'})
    return _finish(binding,audit,body,aux,unresolved,
        force_pending=not audit.get('coverage_complete',False))
