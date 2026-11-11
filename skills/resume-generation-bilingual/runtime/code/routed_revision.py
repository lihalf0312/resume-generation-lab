"""Execute only the repair route justified by a complete current review.

No transport, automatic retries, heuristic source certification or implicit review.
"""
from copy import deepcopy
from pathlib import Path
import product as p
from resume_controls import document as d
from resume_controls.patches import apply_patch
from resume_controls.bullet_labels import adapt_document,parse_bullet
from runtime_context import assert_clock

def _scope(patch,feedback,*,replace_only=False):
    allowed={item['target_id'] for item in feedback}
    seen={op.get('target_id') for op in patch.get('operations',[])}
    if not seen or not seen<=allowed:raise ValueError('patch_exceeds_reviewed_repair_scope')
    restricted={f['target_id'] for f in feedback if f.get('allowed_operations')==['replace']}
    if any(op.get('target_id') in restricted and op.get('op')!='replace' for op in patch.get('operations',[])):
        raise ValueError('important_omission_requires_existing_target_replace')
    if replace_only and any(op.get('op')!='replace' for op in patch.get('operations',[])):
        raise ValueError('layout_only_allows_replace_not_delete_merge_or_split')

def _preserve_body_label_parts(before,after,feedback):
    old={n['id']:n for n in before['nodes']};new={n['id']:n for n in after['nodes']}
    for ident in {f['target_id'] for f in feedback}:
        kinds={f['unit_snapshot']['kind'] for f in feedback if f['target_id']==ident}
        if old[ident]['kind']!='sentence':continue
        if ident not in new:
            if kinds=={'label'}:raise ValueError('label_only_repair_must_preserve_body')
            continue
        left=parse_bullet(old[ident]['text'],before['language']);right=parse_bullet(new[ident]['text'],before['language'])
        if kinds=={'label'} and left['body']!=right['body']:raise ValueError('label_only_repair_changed_body')
        if 'label' not in kinds and (left['label'],left['colon'])!=(right['label'],right['colon']):
            raise ValueError('body_only_repair_changed_unflagged_label')

def revise_saved(source,language,generation,bundle,rendered,deliverable,basis,*,
                 key,directory,target_role,origin,review_receipt=None,stage=None,
                 auxiliary_stage=None,review_stage=None,renderer=None,presentation=None,header_assets=None,language_bindings=None,layout_only=False,provenance=None):
    from workflow_v3 import prepare_revision,preview,clock_transform
    from deliverable_review import apply_auxiliary_patch
    root=Path(directory);p.create_evidence_dir(root)
    calls={'body':0,'auxiliary':0}
    def pending(status,reason,**extra):
        out={'schema':'review-directed-revision-v3','status':status,'reason':reason,
            'pdf':rendered.get('pdf'),'preview_preserved':True,'final_acceptance':False,
            'other_cases_may_continue':True,'callback_calls':dict(calls),
            'automatic_source_truth_certified':False,'no_automatic_retry':True,**extra}
        p.save(root/'RESULT.json',out);return out
    try:
        if rendered['measurement'].get('header_asset_set_sha256') and header_assets is None:
            raise ValueError('same_local_header_configuration_required_before_revision')
        prep=prepare_revision(source,language,generation,bundle,rendered,deliverable,basis,review_receipt=review_receipt,language_bindings=language_bindings,layout_only=layout_only)
    except Exception as exc:return pending('needs_review',str(exc))
    plan=prep['repair_plan'];p.save(root/'REPAIR-PREPARATION.json',prep)
    p.save(root/'REVIEW-RECEIPT.json',review_receipt);p.save(root/'REPAIR-PLAN.json',plan)
    if not plan['can_dispatch']:
        return pending('no_source_revision_needed' if plan['route']=='no_revision_needed' else 'no_layout_revision_needed' if plan['route']=='no_layout_revision_needed' else 'needs_review',
            'No repair callback is authorized by the current complete review.',route=plan['route'],repair_plan=plan)
    missing=[]
    if plan['body_feedback'] and stage is None:missing.append('body')
    if plan['auxiliary_feedback'] and auxiliary_stage is None:missing.append('auxiliary')
    if missing:return pending('awaiting_callbacks','Supply callbacks for the planned route; nothing was sent.',route=plan['route'],missing_callbacks=missing)
    revised=deepcopy(bundle['raw_document']);updated=deepcopy(generation)
    if plan['body_feedback']:
        request=prep['request'];assert_clock(request,basis);p.save(root/'PATCH-REQUEST.json',request)
        returned=False
        try:
            calls['body']+=1;response=stage(key,deepcopy(request));returned=True
            p.save(root/'PATCH-RESPONSE.json',response);_scope(response,plan['body_feedback'],replace_only=plan['route']=='layout_only')
            revised,audit=apply_patch(revised,response,source['material_text'],source['jd_text'])
            _preserve_body_label_parts(bundle['raw_document'],revised,plan['body_feedback'])
            if plan['route']=='layout_only':
                from tail_guidance import validate_tail_revision
                protection=validate_tail_revision(prep['tail_guidance'],bundle,
                    adapt_document(revised,material_text=source['material_text'],jd_text=source['jd_text']),source=source)
                p.save(root/'LAYOUT-PROTECTION-CHECK.json',protection)
                if not protection['structural_pass']:
                    raise ValueError('layout_patch_protection_failed:'+','.join(x['code'] for x in protection['blocking_findings']))
            p.save(root/'BODY-PATCH-AUDIT.json',audit);p.save(root/'STAGED-BODY-DOCUMENT.json',revised)
        except Exception as exc:
            return pending('body_revision_failed',str(exc),callback_returned=returned,
                outcome_uncertain=not returned,route=plan['route'])
    if plan['auxiliary_feedback']:
        request=deepcopy(prep['auxiliary_request'])
        request['context']['revised_body_document']=deepcopy(revised)
        request=clock_transform(basis)(request);assert_clock(request,basis)
        p.save(root/'AUXILIARY-PATCH-REQUEST.json',request);returned=False
        try:
            calls['auxiliary']+=1;response=auxiliary_stage(key+'-auxiliary',deepcopy(request));returned=True
            p.save(root/'AUXILIARY-PATCH-RESPONSE.json',response);_scope(response,plan['auxiliary_feedback'])
            aux=apply_auxiliary_patch(deliverable,response,source,basis)
            p.save(root/'AUXILIARY-PATCH-AUDIT.json',aux);updated=aux['generation']
        except Exception as exc:
            return pending('auxiliary_revision_failed',str(exc),callback_returned=returned,
                outcome_uncertain=not returned,body_patch_already_applied=bool(calls['body']),route=plan['route'])
    updated['resume']=d.to_resume(revised);p.validate(p.GENERATION,updated)
    p.save(root/'DERIVED_GENERATION.json',updated)
    before_after={'raw_before':d.version(bundle['raw_document']),'raw_after':d.version(revised),
        'body_unchanged':bundle['raw_document']==revised,
        'auxiliary_unchanged':all(updated[k]==generation[k] for k in ('selection_notes','necessary_questions','optional_questions','state')),
        'route':plan['route'],'callbacks':dict(calls),'origin':origin,'requires_new_complete_review':True}
    p.save(root/'REVISION-CHANGES.json',before_after)
    warning=None
    if plan['body_feedback'] and prep['tail_guidance']:
        from tail_guidance import validate_tail_revision
        try:warning=validate_tail_revision(prep['tail_guidance'],bundle,adapt_document(revised,material_text=source['material_text'],jd_text=source['jd_text']),source=source)
        except Exception as exc:warning={'status':'diagnostics_need_review','reason':str(exc),'preview_may_continue':True}
        p.save(root/'TAIL-REVISION-CHECK.json',warning)
    result=preview(source,language,updated,directory=root/'deliverable',target_role=target_role,basis=basis,
        origin=origin,review_stage=review_stage,renderer=renderer,previous_deliverable=deliverable,
        document_kind=rendered.get('measurement',{}).get('document_kind','synthetic_development'),
        initial_document=revised,presentation=presentation,header_assets=header_assets,language_bindings=language_bindings,
        provenance={'prior_provenance':deepcopy(provenance),'revision_route':plan['route'],'complete_review_sha256':p.digest(review_receipt),
            'reviewer_declared_diagnoses_not_automatic_truth':True,'body_callback_count':calls['body'],
            'auxiliary_callback_count':calls['auxiliary'],'transport_owner_verified_not_inferred':False})
    new_root=root/'deliverable/preview/round-00'
    if plan['body_feedback'] and prep['tail_guidance'] and (new_root/'render-result.json').exists():
        try:warning=validate_tail_revision(prep['tail_guidance'],bundle,p.read(new_root/'visible-label-bundle.json'),
                source=source,rerendered=p.read(new_root/'render-result.json'))
        except Exception as exc:warning={'status':'diagnostics_need_review','reason':str(exc),'preview_may_continue':True}
        p.save(root/'TAIL-REVISION-AFTER-RENDER.json',warning)
    out={**result,'revision_route':plan['route'],'callback_calls':dict(calls),'revision_findings':warning,
        'review_receipt_not_reused_after_changes':True,'final_acceptance':False}
    p.save(root/'RESULT.json',out);return out
