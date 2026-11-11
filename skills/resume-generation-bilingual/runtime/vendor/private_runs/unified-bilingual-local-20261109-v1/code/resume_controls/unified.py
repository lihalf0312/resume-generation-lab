"""One executable bilingual pipeline, using existing caller-owned stage callbacks.

No provider transport, billing, credentials or automatic retry. Every run is new
and write-once. Preview provenance is explicitly NOT per-claim source evidence.
"""
from copy import deepcopy
from pathlib import Path
import importlib.util, os, sys
from . import document as d, label_flow
from .common import create_evidence_dir, save, read, digest, text_hash, file_hash
from .requests import build
from .bullet_labels import adapt_document, build_label_review, label_gate
from .citations import catalogue, locate
from .capacity import feedback
from .layout_review import evaluate
from .presentation_port import bind_render_evidence
from .reviews import audit_review, acceptance
from .convergence import mechanical, geometry, boundary_findings
from .generation_plan import generation_request
from .generic_presentation import normalize_sidecar, validate_target, validate_identity, load_style, presentation_source_gate

HERE = Path(__file__).resolve().parents[2]
STYLE = HERE.parent / 'bilingual-style-20261109-v4/style_renderer.py'


def paths(doc):
    out = {}
    for si, section in enumerate(n for n in doc['nodes'] if n['kind'] == 'section'):
        out[f's{si}'] = section['id']
        for ei, entry in enumerate(n for n in doc['nodes'] if n['parent'] == section['id']):
            out[f's{si}.e{ei}'] = entry['id']
            for bi, bullet in enumerate(n for n in doc['nodes'] if n['parent'] == entry['id'] and n['kind'] == 'sentence'):
                out[f's{si}.e{ei}.b{bi}'] = bullet['id']
    return out


def source_links_from_sidecar(doc, sidecar, material, jd):
    sidecar = normalize_sidecar(doc, sidecar)
    mapping = paths(doc); blocks = catalogue(material)
    links = {}
    for rid, label in sidecar.get('bullet_labels', {}).items():
        if rid not in mapping: raise ValueError('unknown_sidecar_bullet')
        refs = []
        for fact in label.get('source_facts', []):
            if 'source_id' in fact:
                refs.append({k: fact[k] for k in ('source_id', 'quote') if k in fact}); continue
            quote = fact['source_quote']; hits = [x for x in blocks if quote in x['text']]
            if len(hits) != 1: raise ValueError('sidecar_source_quote_not_unique')
            refs.append({'source_id': hits[0]['id'], 'quote': quote})
        links[mapping[rid]] = refs
    return links


def presentation_for(bundle, sidecar=None, *, generated_heading_contract=False):
    doc = bundle['render_document']; sidecar = normalize_sidecar(doc, sidecar, allowed_versions=[bundle['raw_version']])
    mapping = paths(doc); nodes = d.units(doc)
    labels, primary, stable_titles, breaks = {}, {}, {}, {}
    for rid, ident in mapping.items():
        node = nodes[ident]
        if node['kind'] == 'sentence':
            record = bundle['records'][ident]
            if record['parse_status'] != 'parsed':
                # Legacy literal strings remain visible. Never invent a topic
                # from body punctuation; the label/source gate stays open.
                continue
            old = sidecar.get('bullet_labels', {}).get(rid)
            if old and (old['source_text'] != node['text'] or old['text'] != record['label']):
                raise ValueError('stale_editor_label_sidecar')
            # Actual origin provenance only. Never label this as a located claim
            # citation or pass a source gate from it. Preview must remain blocked.
            provenance = [{'kind': 'original_generation_source_provenance_only',
                           'source_document_sha256': bundle['source_sha256'],
                           'claim_support': 'unreviewed_no_per_label_evidence'}]
            labels[rid] = {'text': record['label'], 'source_text': node['text'],
                          'source_facts': deepcopy(record['source_refs']) or provenance,
                          'source_review_status': 'pending', 'preview_only': True,
                          'stable_id': ident}
            br = sidecar.get('bullet_breaks', {}).get(rid)
            if br:
                if br['source_text'] != node['text']: raise ValueError('stale_body_break')
                breaks[rid] = br
        elif node['kind'] == 'entry' and node['text'].strip() and (node['purpose'] in ('experience', 'projects', 'education') or rid in sidecar.get('entry_primary',{})):
            rule = sidecar.get('entry_primary', {}).get(rid)
            if rule:
                if rule.get('source_text') != node['text'] or node['text'].count(rule.get('text', '')) != 1:
                    raise ValueError('stale_explicit_primary_name')
                origin = 'existing_explicit_editor_primary_binding'
            elif generated_heading_contract:
                parts = node['text'].split('|')
                if any(not p.strip() for p in parts) or '｜' in node['text']:
                    raise ValueError('ambiguous_declared_heading_components')
                rule = {'source_text': node['text'], 'text': parts[0].strip()}
                origin = 'model_declared_first_component_not_source_certified'
            else: raise ValueError('needs_explicit_primary_name_binding:' + ident)
            primary[rid] = rule
            title_locations=[]
            for ref in rule.get('source_refs',[]):
                if '_material' not in bundle: raise ValueError('source_text_required_to_check_primary_references')
                located=locate(bundle['_material'],ref,bundle['_jd'])
                if located['status']!='unique': raise ValueError('primary_name_reference_not_unique_personal_material')
                selected=ref.get('quote') or located['matches'][0]['text']
                if rule['text'] not in selected and rule.get('translation_basis')!='explicit_descriptive_translation':
                    raise ValueError('primary_name_not_in_selected_source_or_explicit_translation')
                title_locations.append(located)
            stable_titles[ident] = {**deepcopy(rule), 'origin': origin, 'source_review_status': 'pending',
                                   'source_locations':title_locations}
    sentence_paths={rid for rid,ident in mapping.items() if nodes[ident]['kind']=='sentence'}
    if set(sidecar.get('bullet_labels', {})) - sentence_paths: raise ValueError('unknown_sidecar_labels')
    return {'bullet_labels': labels, 'entry_primary': primary, 'bullet_breaks': breaks,
            'heading_breaks': deepcopy(sidecar.get('heading_breaks', {})),
            'style_options': {'english_projects_heading': 'Project Experience',
                              'english_project_title_order': 'name_first'}}, stable_titles


def render_v4(bundle, directory, sidecar=None, *, generated_heading_contract=False, header_assets=None,
              target_role=None, document_kind='synthetic_development', allow_synthetic_test_assets=False):
    presentation, titles = presentation_for(bundle, sidecar, generated_heading_contract=generated_heading_contract)
    target = validate_target(target_role or (sidecar or {}).get('target_role'), bundle['_jd'])
    identity = validate_identity(bundle['render_document'], sidecar, bundle['_material'], generated_contract=generated_heading_contract)
    module = load_style(target, document_kind=document_kind)
    original_doc = bundle['render_document']; mapping = paths(original_doc)
    candidate = {'resume': d.to_resume(original_doc)}
    if header_assets:
        from .header_assets import render_with_header_assets
        measurement = render_with_header_assets(module, candidate, original_doc['language'], directory,
                                                presentation, header_assets=header_assets,
                                                allow_synthetic_test_assets=allow_synthetic_test_assets)
    else:
        measurement = module.render_candidate(candidate, original_doc['language'], directory, presentation)
    visible_raw = deepcopy(bundle['raw_document']); visible_nodes = d.units(visible_raw)
    transforms = []
    for change in measurement.get('presentation_normalizations', []):
        ident = mapping[change['id']]
        if visible_nodes[ident]['text'] != change['before']: raise ValueError('normalization_source_heading_changed')
        visible_nodes[ident]['text'] = change['after']
        transforms.append({**change, 'stable_id': ident, 'not_an_arbitrary_content_rewrite': True})
    visible = adapt_document(visible_raw, material_text=bundle['_material'], jd_text=bundle['_jd'],
        source_links={i: r['source_refs'] for i, r in bundle['records'].items()},
        origin={'kind': 'actual_visible_projection', 'prior_raw_version': bundle['raw_version'], 'heading_transforms': transforms})
    visible['_material'], visible['_jd'] = bundle['_material'], bundle['_jd']
    stable_bullets = {rid: ident for rid, ident in mapping.items() if d.units(original_doc)[ident]['kind']=='sentence'}
    rendered = bind_render_evidence(visible['render_document'], directory, measurement, stable_bullets, presentation['bullet_labels'])
    rendered['heading_normalizations'] = transforms
    rendered['stable_primary_names'] = titles
    rendered['target_binding'] = target
    rendered['identity_binding'] = identity
    rendered['preview_only'] = True
    rendered['pending_items'] = [{'route': 'source_review', 'code': 'current_labels_and_primary_names_unreviewed',
        'closed': False, 'blocks_current_draft': True,
        'reason': 'Actual source provenance is not per-claim support. Review complete visible headings, bodies and labels.'}]
    return visible, rendered


def run(*, source, language, skill, directory, stage, key_prefix,
        generation_origin, presentation=None, patch_stage=None, review_stage=None,
        label_review_stage=None, max_rounds=0, renderer=render_v4, guidance='', atomic_groups=(), header_assets=None,
        target_role=None, document_kind='synthetic_development', initial_document=None, allow_synthetic_test_assets=False,
        presentation_review=None, request_transform=None, initial_generation_state='ready'):
    """Generate -> stable parse -> lead-ins/primary names -> real render -> measure -> source review.
    At most two optional content patches. No retry after an uncertain callback.
    Passing source or layout gates never certifies model quality or source truth.
    """
    if language not in ('en', 'zh') or type(max_rounds) is not int or not 0 <= max_rounds <= 2:
        raise ValueError('language_or_revision_limit')
    if set(source) != {'case_id', 'source_language', 'material_text', 'jd_text'}:
        raise ValueError('source_only_four_key_case_required')
    target_role = deepcopy(target_role or (presentation or {}).get('target_role'))
    if renderer is render_v4: validate_target(target_role, source['jd_text'])
    header_preflight = None
    if allow_synthetic_test_assets and (document_kind!='synthetic_development' or generation_origin not in ('synthetic_fake_new_contract','manual_development_fixture')):
        raise ValueError('synthetic_assets_only_in_explicit_synthetic_test')
    if header_assets:
        from .header_assets import preflight_header_assets
        header_preflight = preflight_header_assets(header_assets, language,
                                                   allow_synthetic_test_assets=allow_synthetic_test_assets)
    active_header_assets = header_assets if header_preflight and header_preflight['status'] == 'ready' else None
    root = Path(directory)
    root = root.absolute() if os.name == 'nt' else root.resolve()
    create_evidence_dir(root)
    save(root / 'policy.json', {'origin': generation_origin, 'source_sha256': text_hash(source['material_text']),
        'jd_sha256': text_hash(source['jd_text']), 'case_id': source['case_id'], 'language': language,
        'max_rounds': max_rounds, 'style_module_sha256': file_hash(STYLE),
        'local_header_preflight': header_preflight,
        'target_role': target_role, 'document_kind': document_kind,
        'no_transport_or_authorization_created': True})
    calls = {'generate': 0, 'patch': 0, 'body_review': 0, 'label_review': 0}
    def recorded_generation(key, request):
        if request_transform:request=request_transform(request)
        save(root / 'generation-request.json', request); calls['generate'] += 1
        response = stage(key, deepcopy(request))
        save(root / 'generation-response.json', response); return response
    try:
        if initial_document is None:
            generated = label_flow.generate(stage=recorded_generation, key=key_prefix + '-generate-' + language,
                skill=skill, material_text=source['material_text'], jd_text=source['jd_text'],
                document_id=source['case_id'] + '-' + language + '-unified', language=language,
                prepared_request=generation_request(source, language, skill, guidance))
            raw = generated['bundle']['raw_document']
        else:
            d.validate(initial_document); d.validate_intent_context(initial_document, source['jd_text'])
            if initial_document['language'] != language: raise ValueError('initial_document_language_mismatch')
            if initial_generation_state not in ('ready','awaiting_user'):raise ValueError('initial_generation_state_invalid')
            raw = deepcopy(initial_document); generated = {'generation_state':initial_generation_state}
            save(root/'input-stable-document.json', raw)
        history = []; first_lock = None
        before_protection=d.version(raw)
        if presentation and presentation.get('candidate_version'):
            normalize_sidecar(raw,presentation)
            presentation=deepcopy(presentation)
        raw['protected_ids'] = sorted(set(raw['protected_ids']) | {n['id'] for n in raw['nodes']
            if n['kind'] == 'entry' and n['purpose'] == 'education'})
        if presentation and presentation.get('candidate_version'):
            presentation['candidate_version']=d.version(raw)
            save(root/'presentation-protection-rebind.json',{'input_version':before_protection,
                'protected_version':d.version(raw),'reason':'education_protected_ids_metadata_only',
                'text_and_stable_ids_unchanged':True})
        declared = generation_origin in ('new_model_response', 'host_assisted', 'synthetic_fake_new_contract')
        for round_no in range(max_rounds + 1):
            dest = root / f'round-{round_no:02d}'
            links = source_links_from_sidecar(raw, presentation or {}, source['material_text'], source['jd_text'])
            bundle = adapt_document(raw, material_text=source['material_text'], jd_text=source['jd_text'],
                source_links=links, origin={'kind': generation_origin, 'round': round_no})
            save(dest / 'raw-label-bundle.json', bundle)
            bundle['_material'], bundle['_jd'] = source['material_text'], source['jd_text']
            visible, rendered = renderer(bundle, dest / 'render', presentation,
                                         generated_heading_contract=declared, header_assets=active_header_assets,
                                         target_role=target_role, document_kind=document_kind,
                                         allow_synthetic_test_assets=allow_synthetic_test_assets)
            raw = visible['raw_document']; projection = visible['render_document']
            save(dest / 'visible-label-bundle.json', {k: v for k, v in visible.items() if not k.startswith('_')})
            save(dest / 'render-result.json', rendered)
            measurement = rendered['measurement']
            if not mechanical(measurement): raise ValueError('render_mechanical_integrity_blocked')
            if active_header_assets and measurement.get('header_asset_set_sha256') != header_preflight['asset_set_sha256']:
                raise ValueError('header_assets_changed_after_preflight')
            lock = (geometry(measurement), rendered['typography_fingerprint'], rendered['style_fingerprint'],
                    measurement.get('header_asset_set_sha256'))
            if first_lock is None: first_lock = lock
            elif first_lock != lock: raise ValueError('typography_or_style_changed_during_revision')
            layout = evaluate(projection, rendered)
            layout['blocking_findings'] += measurement.get('generic_render_findings', [])
            if measurement.get('generic_render_findings'):
                layout['status']='needs_layout_review'; layout['content_rewrite_possible']=False
            header_review = measurement.get('header_asset_review', {})
            if active_header_assets and header_review.get('status') != 'passed':
                layout['blocking_findings'] += header_review.get('blocking_findings') or [
                    {'route': 'layout_review', 'code': 'header_assets_require_review', 'closed': False, 'blocks_current_draft': True}]
                layout['status'] = 'needs_layout_review'; layout['content_rewrite_possible'] = False
            cap = feedback(projection, measurement)
            cap['presentation_review'] = layout
            cap['physical_lines_by_page'] = [{'page': p['page'], 'text_lines': p.get('text_lines', [])}
                                            for p in measurement['pages_detail']]
            save(dest / 'layout-review.json', layout); save(dest / 'capacity.json', cap)
            history.append({'round': round_no, 'raw_version': visible['raw_version'],
                'render_version': visible['render_version'], 'pages': measurement['pages'],
                'layout_status': layout['status']})
            if measurement['pages'] == 1 and not layout['blocking_findings']: break
            if round_no == max_rounds or patch_stage is None or (layout['blocking_findings'] and not layout['content_rewrite_possible']): break
            def patch(key, request):
                if request_transform:request=request_transform(request)
                save(dest / 'patch-request.json', request); calls['patch'] += 1
                response = patch_stage(key, deepcopy(request)); save(dest / 'patch-response.json', response); return response
            revised = label_flow.revise(raw, stage=patch, key=key_prefix + f'-patch-{language}-{round_no+1}',
                skill=skill, material_text=source['material_text'], jd_text=source['jd_text'], capacity=cap,
                issues=['Preserve labels and source boundaries; do not shrink typography or pad tails.'])
            proposed = revised['bundle']['raw_document']
            boundaries = boundary_findings(raw, proposed, atomic_groups)
            save(dest / 'boundary-audit.json', {'findings': boundaries, 'coverage': 'explicit_groups_only',
                'no_automatic_semantic_truth_claim': True})
            if boundaries: raise ValueError('source_atomic_boundary_change_rejected')
            raw = proposed; presentation = None; declared = True
        # Body review sees the actual visible heading normalization, not stale input headings.
        body_request = build('final_review', skill=skill, material_text=source['material_text'],
                             jd_text=source['jd_text'], candidate=projection)
        label_request = None if visible['pending_items'] else build_label_review(visible, skill=skill, material_text=source['material_text'], jd_text=source['jd_text'])
        if request_transform:
            body_request=request_transform(body_request)
            if label_request:label_request=request_transform(label_request)
        save(root / 'body-review-request.json', body_request)
        if label_request: save(root / 'label-review-request.json', label_request)
        else: save(root/'label-review-unavailable.json',{'status':'needs_label_review','pending_items':visible['pending_items'],
            'reason':'Literal legacy or ambiguous bullets preserved without inferred labels; label audit not dispatched.'})
        body_audit = None; label_audit = label_gate(visible, None, material_text=source['material_text'], jd_text=source['jd_text'])
        if review_stage:
            calls['body_review'] += 1
            response = review_stage(key_prefix + '-body-review-' + language, deepcopy(body_request))
            save(root / 'body-review-response.json', response)
            body_audit = audit_review(projection, response, source['material_text'], jd_text=source['jd_text'])
            save(root / 'body-review-audit.json', body_audit)
        if label_review_stage and label_request:
            calls['label_review'] += 1
            response = label_review_stage(key_prefix + '-label-review-' + language, deepcopy(label_request))
            save(root / 'label-review-response.json', response)
            label_audit = label_gate(visible, response, material_text=source['material_text'], jd_text=source['jd_text'])
        save(root / 'label-review-audit.json', label_audit)
        pending = list(layout['blocking_findings']) + [{'route': 'source_review', 'code': 'independent_label_review',
            'closed': label_audit['passed'], 'blocks_current_draft': not label_audit['passed']}]
        presentation_audit=None
        if rendered.get('target_binding'):
            presentation_audit=presentation_source_gate(rendered,source['material_text'],source['jd_text'],presentation_review)
            save(root/'presentation-source-review.json',presentation_audit)
            pending.append({'route':'source_review','code':'explicit_target_and_identity_presentation_review',
                'closed':presentation_audit['passed'],'blocks_current_draft':not presentation_audit['passed'],
                'reason':'Located target/name evidence is not semantic source approval. No automatic release.'})
        if not body_audit: pending.append({'route': 'source_review', 'code': 'full_visible_body_and_heading_review', 'closed': False, 'blocks_current_draft': True})
        gate = acceptance(protocol_usable=True, citations_locatable=bool(body_audit), review_audit=body_audit,
            known_issues=[], measurement=measurement, clarification={'awaiting_user': generated['generation_state']=='awaiting_user'},
            visual_preferences={'editorial_review': 'pending'}, pending_items=pending)
        result = {'status': 'eligible_for_editorial_review' if gate['complete_flow_pass'] else
                  'needs_layout_review' if measurement['pages'] != 1 or layout['blocking_findings'] else 'review_required',
            'language': language, 'history': history, 'callback_calls': calls, 'generation_origin': generation_origin,
            'page_count': measurement['pages'], 'acceptance': gate, 'layout_review': layout,
            'label_source_review': label_audit, 'body_source_review': body_audit,
            'pdf': rendered['pdf'], 'pdf_sha256': rendered['pdf_sha256'],
            'actual_visible_heading_transforms': rendered.get('heading_normalizations', []),
            'target_binding': rendered.get('target_binding'),
            'identity_binding': rendered.get('identity_binding'),
            'presentation_source_review':presentation_audit,
            'model_quality_improvement_established': False, 'automatic_source_truth_certified': False}
        save(root / 'RESULT.json', result); return result
    except Exception as exc:
        save(root / 'FAILURE.json', {'type': type(exc).__name__, 'reason': str(exc), 'callback_calls': calls,
             'no_automatic_retry': True, 'outcome': 'inspect_saved_callback_evidence_before_any_retry'})
        raise
