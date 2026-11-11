"""Append-only independent source/layout receipt validation. Never creates approval."""
from copy import deepcopy
from pathlib import Path
import tempfile
import argparse,json
import product as p
from resume_controls.reviews import audit_review
from resume_controls.bullet_labels import label_gate
from resume_controls.generic_presentation import presentation_source_gate
from resume_controls.layout_review import evaluate

def verify_visual(proof,pdf_hash,proof_path=None):
    if proof.get('pdf_sha256')!=pdf_hash:raise ValueError('visual_review_wrong_pdf')
    if proof_path:
        proof['evidence_sha256']=p.file_hash(proof_path)
    elif proof.get('artifact_verified'):
        evidence=proof.get('evidence_path')
        if not evidence or p.file_hash(evidence)!=proof.get('evidence_sha256'):
            raise ValueError('saved_visual_receipt_changed')
        if p.read(evidence).get('pdf_sha256')!=pdf_hash:raise ValueError('saved_visual_receipt_wrong_pdf')
    entries=[proof]+proof.get('labels',[])+proof.get('headings',[])
    for entry in entries:
        if proof.get('evidence_kind')=='embedded_bold_with_visual_inspection' and entry.get('visual_artifact_verified'):
            visual=entry.get('visual_evidence_path') or proof.get('visual_evidence_path')
            expected=entry.get('visual_evidence_sha256') or proof.get('visual_evidence_sha256')
            if not visual or not expected or p.file_hash(visual)!=expected:
                raise ValueError('native_visual_image_missing_or_changed')
        for path_key,sha_key in [('visual_evidence_path','visual_evidence_sha256'),('regular_visual_path','regular_visual_sha256')]:
            if entry.get(path_key) and p.file_hash(entry[path_key])!=entry.get(sha_key):raise ValueError('visual_image_changed')
        for key in ('regular_image_path','bold_image_path'):
            if entry.get(key) and entry.get('pixel_artifact_verified'):
                if p.file_hash(entry[key])!=entry.get('pixel_images_sha256',{}).get(key):
                    raise ValueError('pixel_image_changed')
        if entry.get('pixel_artifact_verified'):
            import pymupdf as fitz
            pairs=[('regular_image_path','regular_ink'),('bold_image_path','bold_ink')] if entry.get('regular_image_path') else [('regular_visual_path','regular_ink'),('visual_evidence_path','bold_ink')]
            for path_key,ink_key in pairs:
                if not entry.get(path_key):raise ValueError('pixel_image_missing')
                px=fitz.Pixmap(entry[path_key])
                if px.n!=1 or px.alpha or sum(255-x for x in px.samples)!=entry.get(ink_key):
                    raise ValueError('pixel_ink_evidence_changed')
    return proof

def audit(source,root,*,body=None,labels=None,presentation=None,visual_proof=None):
    p.validate_source(source);root=Path(root)
    bundle=p.read(root/'round-00/visible-label-bundle.json')
    rendered=p.read(root/'round-00/render-result.json')
    policy=p.read(root/'policy.json')
    if (bundle['source_sha256']!=p.text_hash(source['material_text'])
        or policy['source_sha256']!=p.text_hash(source['material_text'])
        or policy['jd_sha256']!=p.text_hash(source['jd_text'])
        or policy['case_id']!=source['case_id']):raise ValueError('audit_source_or_jd_changed')
    if (bundle['jd_sha256']!=p.text_hash(source['jd_text'])
        or p.d.version(bundle['render_document'])!=bundle['render_version']
        or bundle['render_version']!=rendered['candidate_version']
        or p.d.version(bundle['raw_document'])!=bundle['raw_version']):
        raise ValueError('audit_bundle_or_render_version_changed')
    from resume_controls.bullet_labels import adapt_document
    rebuilt=adapt_document(bundle['raw_document'],material_text=source['material_text'],jd_text=source['jd_text'],
        source_links={i:r['source_refs'] for i,r in bundle['records'].items()})
    def content_records(records):return {i:{k:v for k,v in r.items() if k!='origin'} for i,r in records.items()}
    if rebuilt['render_document']!=bundle['render_document'] or content_records(rebuilt['records'])!=content_records(bundle['records']):
        raise ValueError('audit_render_projection_not_derived_from_reviewed_raw')
    if p.file_hash(rendered['pdf'])!=rendered['pdf_sha256']:raise ValueError('audit_pdf_changed')
    checked=deepcopy(rendered)
    expected_labels={i:r['label']+r['colon'] for i,r in bundle['records'].items() if r['parse_status']=='parsed'}
    if (set(rendered.get('label_expected_ids',[]))!=set(expected_labels)
        or rendered.get('label_expected_text')!=expected_labels):raise ValueError('audit_expected_labels_changed')
    checked['presentation_requirements']={'tail_lines':True,'visible_bold':bool(expected_labels)}
    # Freshly check full-width tails against the PDF/DOCX, then independently
    # measure mechanical facts. Cached ratios/page counts/fonts cannot approve.
    from tail_guidance import build_tail_guidance
    guidance=build_tail_guidance(bundle,rendered,source)
    from resume_controls.generic_presentation import load_style
    style=load_style(rendered['target_binding'],document_kind=policy['document_kind'])
    engine=style.engine
    rows=p.read(Path(rendered['docx']).parent/'content.json')['paragraphs']
    with tempfile.TemporaryDirectory(prefix='v2-audit-measure-') as temp:
        fresh=engine.measure(Path(rendered['docx']),Path(rendered['pdf']),rows,bundle['raw_document']['language'],Path(temp))
    if bundle['raw_document']['language']=='zh':
        fresh['chinese_label_alignment']=style.measure_chinese_label_alignment(
            Path(rendered['pdf']),Path(rendered['docx']),rows)
    if p.file_hash(rendered['pdf'])!=rendered['pdf_sha256']:raise ValueError('audit_pdf_changed_during_measurement')
    checked['measurement'].update(fresh)
    if visual_proof:
        checked['measurement']['visual_bold']=verify_visual(p.read(visual_proof),rendered['pdf_sha256'],visual_proof)
    elif checked['measurement'].get('visual_bold'):
        checked['measurement']['visual_bold']=verify_visual(checked['measurement']['visual_bold'],rendered['pdf_sha256'])
    from resume_controls.convergence import mechanical
    layout=evaluate(bundle['render_document'],checked)
    blockers=layout['blocking_findings']
    if fresh['pages']!=1:blockers.append({'code':'one_page_required','observed_pages':fresh['pages'],'blocks_current_draft':True})
    if len(expected_labels)!=len(bundle['records']):blockers.append({'code':'unparsed_lead_ins_require_review','blocks_current_draft':True})
    blockers.extend(rendered['measurement'].get('generic_render_findings',[]))
    for finding in fresh.get('chinese_label_alignment',{}).get('blocking_findings',[]):
        if finding not in blockers:
            blockers.append(finding)
    header=rendered['measurement'].get('header_asset_review')
    if header and header.get('status')!='passed':
        blockers.extend(header.get('blocking_findings') or [{'code':'header_assets_require_visual_review','blocks_current_draft':True}])
    if blockers:layout['status']='needs_layout_review'
    return {'schema':'product-independent-audit-1','pdf_sha256':rendered['pdf_sha256'],
        'mechanical_integrity_passed':mechanical(fresh),'fresh_page_count':fresh['pages'],
        'fresh_tail_guidance_sha256':guidance['guidance_sha256'],
        'fresh_chinese_label_alignment':fresh.get('chinese_label_alignment'),
        'body':audit_review(bundle['render_document'],body,source['material_text'],jd_text=source['jd_text']) if body else None,
        'labels':label_gate(bundle,labels,material_text=source['material_text'],jd_text=source['jd_text']) if labels else None,
        'presentation':presentation_source_gate(rendered,source['material_text'],source['jd_text'],presentation),
        'layout':layout,'automatic_source_truth_certified':False,
        'status':'inspect_independent_gates_no_automatic_release','new_model_calls':0}

def audit_workflow(root,*,complete_receipt=None,body=None,labels=None,presentation=None,visual_proof=None,response_disposition=None):
    """Current complete payload and actual PDF are independently rebound, not trusted by filename."""
    from deliverable_review import build_deliverable
    from omission_review import audit_review,VERSION as REVIEW_PROTOCOL
    from runtime_context import validate_clock
    root=Path(root);source=p.read(root/'SOURCE.json');flow=p.read(root/'FLOW-CONTEXT.json')
    generation=p.read(root/'VISIBLE_GENERATION.json');raw=p.read(root/'VISIBLE-STABLE-DOCUMENT.json')
    original=p.read(root/'ORIGINAL_GENERATION.json');projection=p.read(root/'PROJECTION-BINDING.json')
    saved=p.read(root/'DELIVERABLE.json');basis=validate_clock(flow['runtime_date_basis'])
    if (p.digest(original)!=flow['original_generation_sha256']
        or p.digest(original)!=projection['original_generation_sha256']
        or p.digest(generation)!=projection['visible_generation_sha256']
        or p.d.version(raw)!=projection['raw_document_version']
        or p.digest(basis)!=flow['runtime_date_basis_sha256']):raise ValueError('workflow_projection_or_clock_changed')
    rebuilt=build_deliverable(generation,raw,source,basis,previous=saved)
    if rebuilt!=saved:raise ValueError('complete_deliverable_payload_changed')
    protocol=flow.get('complete_review_protocol')
    if protocol not in (None,REVIEW_PROTOCOL):raise ValueError('unknown_complete_review_protocol')
    saved_request=root/'complete-review/REQUEST.json'
    saved_protocol=p.read(saved_request).get('context',{}).get('complete_review_protocol') if saved_request.exists() else None
    if saved_protocol not in (None,REVIEW_PROTOCOL):raise ValueError('unknown_saved_review_protocol')
    complete=audit_review(saved,complete_receipt,source,basis,require_v2=protocol==REVIEW_PROTOCOL or saved_protocol==REVIEW_PROTOCOL)
    result=audit(source,root/'preview',body=body,labels=labels,presentation=presentation,visual_proof=visual_proof)
    bundle=p.read(root/'preview/round-00/visible-label-bundle.json')
    if bundle['raw_version']!=p.d.version(raw):raise ValueError('complete_review_not_bound_to_visible_PDF_projection')
    result['complete_deliverable']=complete
    from language_flow import language_audit
    language=language_audit(saved,source,raw['language'],flow.get('language_bindings'))
    if raw['language']=='en':
        import re,pymupdf as fitz
        han=r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+'
        known=[span for n in raw['nodes'] for span in re.findall(han,n['text'])]
        with fitz.open(p.read(root/'preview/round-00/render-result.json')['pdf']) as pdf:
            spans=[s for page in pdf for s in re.findall(han,page.get_text())]
        unexpected=[s for s in spans if not any(s in original for original in known)]
        language['actual_pdf_unexpected_han_spans']=unexpected
        if unexpected:
            language['language_pending']=True;language['precheck_passed']=False
            language.setdefault('findings',[]).append({'reason':'Non-English rendered text outside the reviewed resume projection.',
                'spans':unexpected,'next_step':'Review the renderer/presentation language; do not certify a full-English result.'})
    result['language_completeness']=language
    from response_disposition import audit as audit_response_disposition
    disposition=audit_response_disposition(root,response_disposition)
    result['response_disposition']=disposition
    result['response_contract_pending']=disposition['response_contract_pending']
    result['historical_response_issues']=disposition.get('historical_response_issues',False)
    source_ready=complete.get('passed') is True and complete.get('delivery_ready') is True
    # Complete review explicitly includes each body, label and heading. Legacy
    # receipts, when provided, must also be valid; they cannot override it.
    body_ok=body is None or (result['body'].get('coverage_complete') and result['body'].get('source_judgment')=='reviewer_reports_supported' and not result['body'].get('unresolved_claim_ids'))
    label_ok=labels is None or result['labels'].get('passed') is True
    ready=(disposition['passed'] and source_ready and language.get('precheck_passed') is True and not language.get('language_pending')
        and body_ok and label_ok and result['mechanical_integrity_passed'] and result['fresh_page_count']==1
        and result['presentation']['passed'] and not result['layout']['blocking_findings'])
    result.update(final_acceptance=bool(ready),status='reviewed_ready' if ready else 'needs_review',
        body_and_labels_covered_by_complete_deliverable_review=source_ready,
        preview_may_be_inspected=True,other_cases_may_continue=True)
    return result

def cli(args=None):
    if args is None:
        from workflow_cli_args import audit_parser
        args=audit_parser().parse_args()
    kw={k:p.read(getattr(args,k)) for k in ('body','labels','presentation') if getattr(args,k)}
    try:
        if args.prepare_response_disposition:
            if args.response_disposition:raise ValueError('prepare_does_not_accept_a_disposition')
            from response_disposition import prepare
            if p.read(args.source)!=p.read(args.run/'SOURCE.json'):raise ValueError('CLI_source_differs_from_saved_workflow')
            result=prepare(args.run)
        elif (args.run/'DELIVERABLE.json').exists():
            if p.read(args.source)!=p.read(args.run/'SOURCE.json'):raise ValueError('CLI_source_differs_from_saved_workflow')
            result=audit_workflow(args.run,complete_receipt=p.read(args.complete_review) if args.complete_review else None,visual_proof=args.visual_proof,response_disposition=p.strict_json(p.read_evidence_bytes(args.response_disposition).decode('utf-8')) if args.response_disposition else None,**kw)
        else:result=audit(p.read(args.source),args.run,visual_proof=args.visual_proof,**kw)
    except (ValueError,KeyError,OSError,TypeError) as exc:
        result={'status':'needs_review','final_acceptance':False,'blocking_findings':[{'reason':str(exc),
            'next_step':'Check the exact source, complete payload and receipt/PDF hashes; supply a fresh matching review.'}],
            'existing_preview_not_deleted':True,'preview_reference_not_verified_by_this_attempt':True,
            'other_cases_may_continue':True,'automatic_source_truth_certified':False}
    p.save(args.output,result);print(json.dumps({'status':result.get('status'),'final_acceptance':result.get('final_acceptance',False),
        'layout':result.get('layout',{}).get('status'),'blocking_findings':result.get('blocking_findings',[])}))

if __name__=='__main__':
    cli()
