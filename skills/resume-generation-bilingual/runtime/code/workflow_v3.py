"""One complete-deliverable workflow; previews continue while exact gates stay open."""
from pathlib import Path
from copy import deepcopy
import argparse,json
import product as p
from runtime_context import attach_clock,assert_clock,validate_clock
from resume_controls import document as d,label_flow
from resume_controls.capacity import feedback
from resume_controls.patches import apply_patch

def clock_transform(basis):
    basis=validate_clock(basis)
    def transform(q):
        from deliverable_review import GENERATION_CONSISTENCY_GUIDANCE
        q=deepcopy(q)
        if GENERATION_CONSISTENCY_GUIDANCE not in q['context']['rules']:
            q['context']['rules']+='\n'+GENERATION_CONSISTENCY_GUIDANCE
        return attach_clock(q,basis)
    return transform

def stage_transform(basis,source,language,language_bindings=None):
    from language_flow import attach_language_context
    def transform(request):
        return clock_transform(basis)(attach_language_context(request,source,language,language_bindings))
    return transform

def receipt_clock(provenance):
    """Preserve an actual frozen generation clock; do not retrofit historical time."""
    received=provenance.get('runtime_date_basis_received')
    return p.clock_reference() if received is None else validate_clock(received)

def review_complete(deliverable,source,basis,*,directory,stage=None,key='complete-review',receipt=None,language_bindings=None):
    from omission_review import build_review_request,audit_review
    root=Path(directory);p.create_evidence_dir(root)
    request=stage_transform(basis,source,deliverable['raw_document']['language'],language_bindings)(build_review_request(deliverable,source,basis));assert_clock(request,basis)
    p.save(root/'REQUEST.json',request)
    error=None
    try:
        if stage is not None and receipt is not None:raise ValueError('one_review_response_origin_required')
        if stage is not None:receipt=stage(key,deepcopy(request))
        if receipt is not None:p.save(root/'RESPONSE.json',receipt)
        audit=audit_review(deliverable,receipt,source,basis,require_v2=True)
    except Exception as exc:
        error=str(exc)
        audit={'passed':False,'status':'needs_complete_review','missing_unit_ids':[u['id'] for u in deliverable['units']],
            'blocking_findings':[{'unit_id':u['id'],'reason':'invalid_review_receipt: '+error,'next_step':'Supply an exact-bound review; the saved PDF remains inspectable. No automatic retry.'} for u in deliverable['units']],
            'automatic_source_truth_certified':False}
    p.save(root/'AUDIT.json',audit)
    return {'request':request,'audit':audit,'error':error,'receipt':receipt}

def prepare_revision(source,language,generation,bundle,rendered,deliverable,basis,*,issues=(),review_receipt=None,language_bindings=None,layout_only=False):
    """Prepare the actual original PATCH contract using measured full-width tails."""
    from tail_guidance import build_tail_guidance
    from deliverable_review import build_deliverable
    expected=build_deliverable(generation,bundle['raw_document'],source,basis,previous=deliverable)
    if expected!=deliverable or bundle['raw_document']['language']!=language:
        raise ValueError('revision_complete_snapshot_mismatch')
    from review_feedback import build_repair_plan
    guidance=None;guidance_error=None
    if type(layout_only) is not bool:raise ValueError('explicit_boolean_layout_only_choice_required')
    if layout_only:
        from layout_revision import build_layout_plan
        plan,guidance=build_layout_plan(deliverable,review_receipt,source,basis,bundle,rendered)
    else:plan=build_repair_plan(deliverable,review_receipt,source,basis)
    if plan['can_dispatch'] and plan['body_feedback'] and guidance is None:
        try:guidance=build_tail_guidance(bundle,rendered,source)
        except (ValueError,OSError,KeyError,TypeError) as exc:guidance_error=str(exc)
    raw=bundle['raw_document'];capacity=feedback(bundle['render_document'],rendered['measurement'])
    body_request=None;auxiliary_request=None
    if not plan['can_dispatch']:
        return {'request':None,'auxiliary_request':None,'repair_plan':plan,
            'tail_guidance':guidance,'tail_guidance_error':guidance_error,
            'requires_fresh_render_and_complete_review':True,'preview_preserved':True}
    # Label-flow accepts measured render version and explicitly binds it to raw.
    captured={}
    class Captured(Exception):pass
    def capture(key,request):captured['request']=request;raise Captured()
    if plan['body_feedback']:
        try:
            label_flow.revise(raw,stage=capture,key='prepare-only',skill=p.load_skill(p.SKILL),
                material_text=source['material_text'],jd_text=source['jd_text'],capacity=capacity,
                issues=list(issues)+plan['body_feedback'])
        except Captured:pass
        body_request=captured['request'];context=body_request['context']
        context['complete_deliverable_context']=deliverable
        context['review_repair_feedback']=deepcopy(plan['body_feedback'])
        context['repair_scope']={'target_ids':sorted({f['target_id'] for f in plan['body_feedback']}),
            'related_units_are_context_only':True,'auxiliary_fields_are_not_body_targets':True,
            'route':plan['route'],'allowed_operations':plan.get('allowed_operations')}
        context['measured_tail_guidance']=guidance
        context['tail_guidance_status']='ready_for_diagnosis_only' if guidance else 'unavailable_no_layout_claim'
        context['rules']+='\nAct only on the listed repair_scope target_ids using the quoted source evidence. Reviewer diagnoses are not automatic proof. Do not change merely related units, add facts, clear questions, or repair notes via body PATCH. A new complete review is required.'
        if layout_only:
            context['rules']+='\nThe caller explicitly selected layout-only repair after a complete source review. This is not a factual-error diagnosis. Only replace the measured affected bullet bodies; preserve existing labels, all quantities, actors, limitations and auxiliary text. No merge/delete/split, filler, hard line breaks, typography/margin changes or reduced width denominator. Review every physical line after rendering; a short tail is preferable to changing facts.'
        body_request=stage_transform(basis,source,language,language_bindings)(body_request);assert_clock(body_request,basis)
    if plan['auxiliary_feedback']:
        from deliverable_review import build_auxiliary_revision_request
        auxiliary_request=build_auxiliary_revision_request(deliverable,source,basis,issues=plan['auxiliary_feedback'])
        context=auxiliary_request['context']
        context['review_repair_feedback']=deepcopy(plan['auxiliary_feedback'])
        context['repair_scope']={'target_ids':sorted({f['target_id'] for f in plan['auxiliary_feedback']}),
            'related_units_are_context_only':True,'body_changes_not_authorized_by_auxiliary_route':True}
        context['rules']+='\nOnly repair the listed auxiliary target_ids. Related body units are evidence/context, not edit targets. Do not silently remove a necessary question or change ready state to hide unresolved evidence. Re-review the complete updated deliverable.'
        auxiliary_request=stage_transform(basis,source,language,language_bindings)(auxiliary_request);assert_clock(auxiliary_request,basis)
    return {'request':body_request,'auxiliary_request':auxiliary_request,'repair_plan':plan,
        'tail_guidance':guidance,'tail_guidance_error':guidance_error,
        'requires_fresh_render_and_complete_review':True,'body_patch_does_not_update_auxiliary':True}

def preview(source,language,generation,*,directory,target_role,basis,origin,
            provenance=None,presentation=None,header_assets=None,review_stage=None,review_receipt=None,
            renderer=None,previous_deliverable=None,initial_document=None,language_bindings=None,document_kind='synthetic_development'):
    from deliverable_review import build_deliverable
    p.validate_source(source);basis=validate_clock(basis)
    if document_kind not in ('synthetic_development','user_resume'):raise ValueError('explicit_document_kind_required')
    root=Path(directory);p.create_evidence_dir(root)
    from response_recovery import ingest,history_pending
    generation,intake=ingest(generation,directory=root/'response-intake')
    prior_response_pending=history_pending(provenance)
    p.save(root/'SOURCE.json',source)
    if generation is None:
        result={'status':'needs_response_review','pdf':None,'final_acceptance':False,
            'response_intake':intake,'response_contract_pending':True,
            'prior_response_contract_pending':prior_response_pending,'original_payload_preserved':True,'no_automatic_retry':True,
            'automatic_source_truth_certified':False,'other_cases_may_continue':True}
        p.save(root/'RESULT.json',result);return result
    p.save(root/'ORIGINAL_GENERATION.json',generation)
    p.save(root/'LOCAL-PRESENTATION.json',{'presentation':presentation,'header_assets':header_assets,'never_sent_to_model':True})
    p.save(root/'FLOW-CONTEXT.json',{'runtime_date_basis':basis,'runtime_date_basis_sha256':p.digest(basis),
        'origin':origin,'document_kind':document_kind,'complete_review_protocol':'complete-deliverable-review-v2','original_generation_sha256':p.digest(generation),'provenance':provenance,
        'provenance_sha256':p.digest(provenance),'language_bindings':language_bindings,
        'date_fix_live_model_tested':False,'no_automatic_retry':True})
    if initial_document is None:
        raw,_=d.ingest(generation['resume'],source['case_id']+'-'+language+'-product',language,
            intent_context=d.goal_context(source['jd_text']))
    else:
        d.validate(initial_document)
        if d.to_resume(initial_document)!=generation['resume']:raise ValueError('revision_stable_document_mismatch')
        raw=deepcopy(initial_document)
    render_options={} if renderer is None else {'renderer':renderer}
    render_error=None
    try:
        rendered_result=p.consume(source,language,generation,directory=root/'preview',target_role=target_role,
            presentation=presentation,header_assets=header_assets,origin=origin,document_kind=document_kind,allow_pending_preview=True,
            raw_document=raw,request_transform=stage_transform(basis,source,language,language_bindings),**render_options)
    except Exception as exc:
        render_error=str(exc);rendered_result={'status':'preview_failed_for_this_case','pdf':None}
        p.save(root/'PREVIEW-FAILURE.json',{'reason':render_error,'other_cases_may_continue':True,'no_automatic_retry':True})
    bundle=None;rendered=None
    if (root/'preview/round-00/visible-label-bundle.json').exists():
        bundle=p.read(root/'preview/round-00/visible-label-bundle.json')
        rendered=p.read(root/'preview/round-00/render-result.json');raw=bundle['raw_document']
    visible=deepcopy(generation);visible['resume']=d.to_resume(raw)
    p.save(root/'VISIBLE_GENERATION.json',visible)
    p.save(root/'VISIBLE-STABLE-DOCUMENT.json',raw)
    p.save(root/'PROJECTION-BINDING.json',{'original_generation_sha256':p.digest(generation),
        'provenance_sha256':p.digest(provenance),'visible_generation_sha256':p.digest(visible),'raw_document_version':d.version(raw),
        'differences_are_renderer_recorded_normalizations_only':True,
        'auxiliary_text_unchanged':all(visible[k]==generation[k] for k in ('selection_notes','necessary_questions','optional_questions','state')),
        'heading_transforms':rendered.get('heading_normalizations',[]) if rendered else []})
    deliverable=build_deliverable(visible,raw,source,basis,previous=previous_deliverable,document_kind=document_kind)
    p.save(root/'DELIVERABLE.json',deliverable)
    from label_recovery import prepare as prepare_labels
    label_request=prepare_labels(source,language,visible,raw,basis)
    p.save(root/'LABEL-REPAIR-REQUEST.json',label_request)
    label_pending=bool(label_request['context']['targets'] or label_request['context']['blocked_ambiguous_prefixes'])
    p.save(root/'LABEL-CONTRACT.json',{'missing_label_targets':label_request['context']['targets'],
        'ambiguous_prefixes':label_request['context']['blocked_ambiguous_prefixes'],
        'label_format_pending':label_pending,'no_label_guessed':True,'body_preserved':True,
        'next_step':'Supply source-bound label-only proposals, then review every visible unit again.'})
    from language_flow import language_audit
    try:language_review=language_audit(deliverable,source,language,language_bindings)
    except (ValueError,KeyError,TypeError) as exc:
        language_review={'language_pending':True,'precheck_passed':False,'preview_allowed':True,
            'semantic_language_certified':False,'findings':[{'reason':str(exc),'next_step':'Fix the explicit language-name inputs and repeat the language precheck.'}]}
    p.save(root/'LANGUAGE-REVIEW.json',language_review)
    review=review_complete(deliverable,source,basis,directory=root/'complete-review',stage=review_stage,receipt=review_receipt,language_bindings=language_bindings)
    revision=None
    if bundle and rendered:
        try:revision=prepare_revision(source,language,visible,bundle,rendered,deliverable,basis,review_receipt=review['receipt'],language_bindings=language_bindings)
        except Exception as exc:revision={'request':None,'tail_guidance_error':str(exc),'preview_preserved':True,
            'next_step':'Repair the measured-revision binding before editing; inspect the existing PDF meanwhile.'}
        p.save(root/'REVISION-PREPARATION.json',revision)
    audit=review['audit']
    units={u['id']:u for u in deliverable['units']}
    unresolved=[]
    for finding in audit.get('blocking_findings',[]):
        unit=units.get(finding.get('unit_id'),{})
        unresolved.append({**finding,'unit_kind':unit.get('kind','receipt'),
            'text_excerpt':unit.get('text','')[:160],'field_path':unit.get('path')})
    result={'schema':'complete-bilingual-product-v2','status':'needs_review','language':language,'document_kind':document_kind,
        'response_intake':intake,'response_contract_pending':intake['response_review_pending'] or prior_response_pending,
        'prior_response_contract_pending':prior_response_pending,
        'label_format_pending':label_pending,
        'generation_state':generation['state'],'preview_status':rendered_result.get('status'),
        'pdf':rendered_result.get('pdf'),'page_count':rendered_result.get('page_count'),
        'complete_deliverable_review_passed':audit.get('passed') is True,
        'source_delivery_ready':audit.get('delivery_ready') is True,
        'all_delivery_gates_ready':False,
        'language_pending':language_review['language_pending'],'language_review':language_review,
        'missing_review_unit_ids':audit.get('missing_unit_ids',[]),'review_findings':unresolved,
        'necessary_questions':generation['necessary_questions'],'optional_questions':generation['optional_questions'],
        'preview_error':render_error,'tail_guidance_error':revision.get('tail_guidance_error') if revision else 'no_measured_preview',
        'next_steps':['Review the exact complete-review/REQUEST.json, including each auxiliary unit.',
            'Inspect the actual PDF and measured tails; retain any remaining layout findings.',
            'Any edit requires new complete review and rendering; do not reuse prior approval.'],
        'preview_not_blocked_by_missing_review':True,'other_cases_may_continue':True,
        'automatic_source_truth_certified':False,'final_acceptance':False,'date_fix_live_model_tested':False}
    p.save(root/'RESULT.json',result)
    return result

def generate(source,language,*,stage,key,directory,target_role,mode='full',observed_at=None,timezone=None,
             review_stage=None,origin='new_model_response',renderer=None,presentation=None,header_assets=None,language_bindings=None):
    """One generation callback; each later review is separately supplied/owned."""
    p.validate_target(target_role,source['jd_text'])
    if header_assets:
        from resume_controls.header_assets import preflight_header_assets
        preflight_header_assets(header_assets,language)
    request,manifest=p.prepare(source,language,mode=mode,observed_at=observed_at,timezone=timezone,language_bindings=language_bindings)
    root=Path(directory);p.create_evidence_dir(root)
    p.save(root/'GENERATION-REQUEST.json',request);p.save(root/'GENERATION-MANIFEST.json',manifest)
    returned=False
    try:
        result=stage(key,deepcopy(request));returned=True;p.save(root/'GENERATION-RESPONSE.json',result)
    except Exception as exc:
        p.save(root/'GENERATION-FAILURE.json',{'reason':str(exc),'callback_returned':returned,'callback_count':1,
            'status':'returned_payload_invalid_or_not_saved' if returned else 'callback_outcome_requires_owner_inspection',
            'uncertain_outcome_requires_owner_inspection':not returned,'no_retry':True});raise
    return preview(source,language,result,directory=root/'deliverable',target_role=target_role,
        basis=request['context']['runtime_date_basis'],origin=origin,review_stage=review_stage,renderer=renderer,
        presentation=presentation,header_assets=header_assets,language_bindings=language_bindings,
        provenance={'generation_request_sha256':request['input_sha256'],'callback_owner_verified_transport':False})

def revise_saved(*args,**kwargs):
    from routed_revision import revise_saved as routed
    return routed(*args,**kwargs)


def cli(argv=None, *, args=None):
    if args is None:
        from workflow_cli_args import product_parser
        args=product_parser().parse_args(argv)
    from response_recovery import saved_lineage
    if args.origin=='host_assisted' and args.command not in ('revise-reviewed','revise-labels'):
        raise ValueError('host_assisted_generation_requires_render_host_response_entry')
    if args.layout_only and args.command!='revise-reviewed':raise ValueError('layout_only_requires_revise_reviewed_command')
    if args.command=='batch-replay':
        if not args.batch:raise ValueError('batch_manifest_required')
        p.create_evidence_dir(args.output);results=[]
        for i,item in enumerate(p.read(args.batch)['cases']):
            try:
                def local(key):
                    value=Path(item[key]);return value if value.is_absolute() else args.batch.parent/value
                source=p.read(local('source'));response,provenance=p.verify_receipt(local('receipt'),source,item['language'],p.read(local('context')),preserve_invalid_for_preview=True)
                result=preview(source,item['language'],response,directory=args.output/f'case-{i:03d}',
                    target_role=p.read(local('target_role')),basis=receipt_clock(provenance),origin='new_model_response',provenance=provenance)
                results.append({'index':i,'status':result['status'],'pdf':result['pdf']})
            except Exception as exc:results.append({'index':i,'status':'case_failed_others_continue','reason':str(exc)})
        p.save(args.output/'BATCH-RESULT.json',results);print(json.dumps(results,ensure_ascii=False));return
    if not args.source or not args.language:raise ValueError('source_and_language_required')
    source=p.read(args.source)
    if args.command=='prepare':
        q,m=p.prepare(source,args.language,mode=args.mode,observed_at=args.observed_at,timezone=args.timezone,
            language_bindings=p.read(args.language_bindings) if args.language_bindings else None)
        p.create_evidence_dir(args.output);p.save(args.output/'REQUEST.json',q);p.save(args.output/'MANIFEST.json',m)
        print(json.dumps(m,ensure_ascii=False));return
    if args.command in ('bind-host-response','render-host-response'):
        if not args.request or not args.response:raise ValueError('prepared_request_and_raw_response_required')
        if args.origin or args.receipt or args.context or args.observed_at or args.timezone or args.language_bindings:
            raise ValueError('host_entry_uses_bound_request_origin_clock_and_language_context')
        options={'request_text':p.read_evidence_bytes(args.request).decode('utf-8'),
            'response_text':p.read_evidence_bytes(args.response).decode('utf-8'),'directory':args.output,'mode':args.mode}
        if args.command=='bind-host-response':
            if args.host_declaration:raise ValueError('bind_creates_a_declaration_does_not_accept_one')
            result=p.bind_host_response(source,args.language,**options)
        else:
            if not args.host_declaration or not args.target_role:raise ValueError('host_declaration_and_JD_bound_target_required')
            result=p.consume_host_response(source,args.language,**options,
                declaration_text=p.read_evidence_bytes(args.host_declaration).decode('utf-8'),target_role=p.read(args.target_role),
                presentation=p.read(args.presentation) if args.presentation else None,
                header_assets=p.read(args.header_assets) if args.header_assets else None,
                review_receipt=p.read(args.complete_review) if args.complete_review else None)
        print(json.dumps(result,ensure_ascii=False));return
    if not args.target_role:raise ValueError('explicit_JD_bound_target_required')
    if args.observed_at or args.timezone:raise ValueError('historical_response_clock_is_not_retroactively_changed')
    if args.command=='revise-labels':
        if not args.run or not args.origin:raise ValueError('saved_run_and_explicit_origin_required')
        if source!=p.read(args.run/'SOURCE.json'):raise ValueError('label_revision_source_changed')
        result=p.revise_labels(source,args.language,p.read(args.run/'VISIBLE_GENERATION.json'),
            p.read(args.run/'VISIBLE-STABLE-DOCUMENT.json'),p.read(args.run/'FLOW-CONTEXT.json')['runtime_date_basis'],
            directory=args.output,target_role=p.read(args.target_role),origin=args.origin,
            response=p.strict_json(p.read_evidence_bytes(args.label_proposals).decode('utf-8')) if args.label_proposals else None,
            presentation=p.read(args.presentation) if args.presentation else p.read(args.run/'LOCAL-PRESENTATION.json')['presentation'],
            header_assets=p.read(args.header_assets) if args.header_assets else p.read(args.run/'LOCAL-PRESENTATION.json')['header_assets'],
            provenance=saved_lineage(args.run),
            document_kind=p.read(args.run/'FLOW-CONTEXT.json').get('document_kind','synthetic_development'),
            language_bindings=p.read(args.language_bindings) if args.language_bindings else None)
        print(json.dumps(result,ensure_ascii=False));return
    if args.command=='apply-name-bindings':
        if not args.run or not args.language_bindings or not args.presentation:
            raise ValueError('saved_run_explicit_name_bindings_and_source_bound_presentation_required')
        result=p.apply_name_bindings(source,args.language,p.read(args.run/'VISIBLE_GENERATION.json'),
            p.read(args.run/'VISIBLE-STABLE-DOCUMENT.json'),p.read(args.run/'FLOW-CONTEXT.json')['runtime_date_basis'],
            bindings=p.read(args.language_bindings),directory=args.output,target_role=p.read(args.target_role),provenance=saved_lineage(args.run),
            document_kind=p.read(args.run/'FLOW-CONTEXT.json').get('document_kind','synthetic_development'),
            presentation=p.read(args.presentation),origin='offline_editor_revision')
        print(json.dumps(result,ensure_ascii=False));return
    if args.command=='revise-reviewed':
        if not args.run or not args.origin:raise ValueError('saved_run_and_explicit_local_origin_required')
        if source!=p.read(args.run/'SOURCE.json'):raise ValueError('revision_source_differs_from_saved_workflow')
        result=revise_saved(source,args.language,p.read(args.run/'VISIBLE_GENERATION.json'),
            p.read(args.run/'preview/round-00/visible-label-bundle.json'),
            p.read(args.run/'preview/round-00/render-result.json'),p.read(args.run/'DELIVERABLE.json'),
            p.read(args.run/'FLOW-CONTEXT.json')['runtime_date_basis'],
            review_receipt=p.read(args.complete_review) if args.complete_review else None,
            stage=(lambda key,q:p.read(args.body_patch)) if args.body_patch else None,
            auxiliary_stage=(lambda key,q:p.read(args.auxiliary_patch)) if args.auxiliary_patch else None,
            key='local-reviewed-replay',directory=args.output,target_role=p.read(args.target_role),origin=args.origin,
            presentation=p.read(args.presentation) if args.presentation else None,
            header_assets=p.read(args.header_assets) if args.header_assets else None,
            language_bindings=p.read(args.language_bindings) if args.language_bindings else p.read(args.run/'FLOW-CONTEXT.json').get('language_bindings'),
            layout_only=args.layout_only,provenance=saved_lineage(args.run))
        print(json.dumps(result,ensure_ascii=False));return
    if args.command=='render-receipt':
        if not args.receipt or not args.context:raise ValueError('receipt_and_frozen_context_required')
        response,prov=p.verify_receipt(args.receipt,source,args.language,p.read(args.context),preserve_invalid_for_preview=True);origin='new_model_response'
    else:
        if not args.response or not args.origin:raise ValueError('response_and_explicit_origin_required')
        response=p.read_evidence_bytes(args.response).decode('utf-8');prov={'origin':args.origin};origin=args.origin
    result=preview(source,args.language,response,directory=args.output,target_role=p.read(args.target_role),
        basis=receipt_clock(prov),origin=origin,provenance=prov,
        presentation=p.read(args.presentation) if args.presentation else None,
        header_assets=p.read(args.header_assets) if args.header_assets else None,
        review_receipt=p.read(args.complete_review) if args.complete_review else None,
        language_bindings=p.read(args.language_bindings) if args.language_bindings else None)
    print(json.dumps(result,ensure_ascii=False))
