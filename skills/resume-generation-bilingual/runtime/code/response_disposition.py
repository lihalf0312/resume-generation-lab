"""Explicit review of one known isolation operation, not candidate approval.

Scope is source + exact original/derived payload and isolation delta. It does
not re-sign every PDF. Current facts, labels and layout keep their own existing
complete-review/audit bindings. Original intake records stay immutable.
"""
from copy import deepcopy
from pathlib import Path
import os
import tempfile
from resume_controls.common import digest,read,read_evidence_bytes,text_hash
from resume_controls.schemas import obj,string,validate,HASH
from response_recovery import ingest,history_pending,strict_json

VERSION='known-isolation-disposition-v1'
CONFIRMATIONS=('available_original_payload_reviewed','only_known_nonpersonal_self_assessment_isolated',
    'no_personal_fact_removed_by_isolation','self_assessment_not_used_as_acceptance_evidence')
SCHEMA=obj({'schema_version':{'const':VERSION},'scope_sha256':HASH,
    'decision':{'enum':['accept_known_isolation','keep_pending']},
    'reviewer':string(200),'rationale':string(1200),
    'confirmations':obj({key:{'type':'boolean'} for key in CONFIRMATIONS})})


def _collect(root,source):
    issues={};seen={}
    def visit_run(directory):
        directory=Path(directory)
        # Preserve the lexical components for the Windows no-reparse reader.
        directory=directory.absolute() if os.name=='nt' else directory.resolve()
        if directory in seen:
            if seen[directory] is None:raise ValueError('response_lineage_cycle')
            return set(seen[directory])
        if len(seen)>=32:raise ValueError('response_lineage_too_deep')
        seen[directory]=None;bound=set()
        if read(directory/'SOURCE.json')!=source:raise ValueError('disposition_lineage_source_changed')
        flow=read(directory/'FLOW-CONTEXT.json')
        if 'provenance_sha256' in flow and digest(flow.get('provenance'))!=flow['provenance_sha256']:
            raise ValueError('response_provenance_binding_changed')
        projection=read(directory/'PROJECTION-BINDING.json')
        if 'provenance_sha256' in projection and projection['provenance_sha256']!=flow.get('provenance_sha256'):
            raise ValueError('response_provenance_binding_missing_or_changed')
        path=directory/'response-intake/REPORT.json'
        if path.exists():
            saved=read(path)
            if saved.get('input_kind')=='raw_json_text':
                payload=read_evidence_bytes(path.parent/'ORIGINAL-RESPONSE.txt').decode('utf-8')
            elif saved.get('input_kind')=='caller_parsed_object':payload=read(path.parent/'ORIGINAL-PAYLOAD.json')
            else:raise ValueError('disposition_original_payload_unavailable')
            with tempfile.TemporaryDirectory(prefix='verify-isolation-') as tmp:
                candidate,rebuilt=ingest(payload,directory=Path(tmp)/'intake')
            if rebuilt!=saved:raise ValueError('disposition_intake_changed_or_not_reconstructable')
            if candidate is None:raise ValueError('blocked_or_unknown_response_cannot_be_disposed')
            if candidate!=read(directory/'ORIGINAL_GENERATION.json'):
                raise ValueError('disposition_original_candidate_changed')
            if digest(candidate)!=flow['original_generation_sha256']:
                raise ValueError('disposition_original_flow_binding_changed')
            if rebuilt['response_review_pending']:
                # ingest has already proved the exact allowlist delta and strict
                # candidate schema. Include both values/hashes for human review.
                item={'original_payload_sha256':rebuilt['original_payload_sha256'],
                    'candidate_sha256':rebuilt['candidate_sha256'],
                    'raw_utf8_sha256':rebuilt.get('raw_utf8_sha256'),
                    'input_kind':rebuilt['input_kind'],'extensions':rebuilt['extensions'],
                    'transformations':rebuilt['transformations'],'original_schema_pass':False,
                    'original_payload':strict_json(payload) if isinstance(payload,str) else deepcopy(payload),
                    'normalized_candidate':deepcopy(candidate)}
                issues[digest(item)]={'issue_id':digest(item),**item};bound.add(digest(item))
        else:
            raise ValueError('response_intake_evidence_required_for_final_audit')
        bound.update(visit_provenance(flow.get('provenance')))
        if history_pending(read(directory/'RESULT.json')) and not bound:
            raise ValueError('historical_pending_without_bound_isolation_evidence')
        seen[directory]=set(bound)
        return bound
    def visit_provenance(value):
        if not isinstance(value,dict):
            if history_pending(value):raise ValueError('unbound_response_history')
            return set()
        remaining=deepcopy(value);bound=set()
        if 'prior_run' in value:
            directory=Path(value['prior_run']);records=value.get('prior_records')
            allowed={'response-intake/REPORT.json','FLOW-CONTEXT.json','RESULT.json'}
            if not isinstance(records,dict) or not records or set(records)-allowed:
                raise ValueError('unbound_response_lineage_records')
            for name,record in records.items():
                if record!=read(directory/name):raise ValueError('response_lineage_snapshot_changed')
            bound.update(visit_run(directory))
            remaining.pop('prior_run',None);remaining.pop('prior_records',None)
        if 'prior_provenance' in value:
            bound.update(visit_provenance(value['prior_provenance']));remaining.pop('prior_provenance')
        if history_pending(remaining):raise ValueError('unbound_response_pending_history')
        return bound
    visit_run(root)
    return [issues[key] for key in sorted(issues)]


def prepare(root):
    root=Path(root);source=read(root/'SOURCE.json')
    from product import validate_source
    validate_source(source)
    issues=_collect(root,source)
    scope={'schema_version':VERSION,'source_case_sha256':digest(source),
        'source_sha256':text_hash(source['material_text']),'jd_sha256':text_hash(source['jd_text']),
        'source_for_review':deepcopy(source),
        'isolations':issues}
    return {'schema_version':VERSION,'status':'review_required' if issues else 'not_required',
        'scope':scope,'scope_sha256':digest(scope),'output_schema':deepcopy(SCHEMA),
        'review_instructions':'Review the retained original payload, exact isolated extension and unchanged normalized candidate. Only accept isolation of the known nonpersonal boolean self-assessment; it never proves order, facts or quality. Unknown fields cannot be approved through this route. This decision closes only the isolation gate. Current complete source, label, language, presentation and actual-layout reviews remain required.',
        'receipt_reusable_for_same_source_and_isolation_scope':True,
        'candidate_or_pdf_approval_granted_by_this_request':False}


def audit(root,receipt=None):
    out={'schema_version':VERSION,'passed':False,'response_contract_pending':True,
        'status':'needs_response_disposition','original_error_history_retained':True,
        'candidate_acceptance_granted':False,'automatic_semantic_truth_certified':False}
    try:
        request=prepare(root);issues=request['scope']['isolations']
        out.update(scope_sha256=request['scope_sha256'],isolations=issues,
            historical_response_issues=bool(issues))
        if not issues:
            if receipt is not None:raise ValueError('disposition_receipt_for_different_or_empty_scope')
            out.update(passed=True,response_contract_pending=False,status='not_required');return out
        if receipt is None:return out
        validate(SCHEMA,receipt)
        if receipt['scope_sha256']!=request['scope_sha256']:raise ValueError('stale_or_different_isolation_scope')
        if not receipt['reviewer'].strip() or not receipt['rationale'].strip():raise ValueError('explicit_reviewer_and_rationale_required')
        out['receipt']=deepcopy(receipt);out['receipt_sha256']=digest(receipt)
        if receipt['decision']!='accept_known_isolation':return out
        if not all(receipt['confirmations'][key] is True for key in CONFIRMATIONS):
            raise ValueError('all_isolation_review_confirmations_required')
        out.update(passed=True,response_contract_pending=False,status='reviewer_accepted_known_isolation')
    except (ValueError,KeyError,TypeError,OSError,UnicodeError) as exc:
        out['reason']=str(exc)
    return out
