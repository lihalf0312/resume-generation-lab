"""Explicit lead-in syntax, lossless body projection, separate source-review gate.

Parsing is typography only, never a factual or semantic classifier. Raw model
strings and stable IDs remain available. Legacy strings are not guessed at.
"""
from copy import deepcopy
import re
from . import document as d
from .common import digest, text_hash
from .citations import catalogue, locate

LABEL_PROTOCOL = 'explicit-bold-lead-in-v1'
LABEL_GUIDANCE = '''
Bullet lead-in presentation contract (explicit-bold-lead-in-v1):
For generation and replacement of a bullet string, use exactly **Topic:** body
in English, or **概括短语：**正文 in Chinese. Keep the existing string-bullet
schema; do not return objects or new response fields. The prefix and colon are
rendered bold, the body normal. English labels: normally 2-4 words, at most 6
words / 48 characters. Chinese labels: normally 2-8 characters, at most 12.
Use a brief objective topic naming the actual activity, object or artifact,
supported by original personal material and consistent with this exact body.
Do not introduce a benefit, performance level, seniority, title, qualification,
ownership, completion or causal result. Do not use a topic label to upgrade
assistance to leadership or record handling to authorship. Do not mechanically
rewrite facts into 优化/确保/负责 or optimization/guarantee/ownership claims.
Preserve explicitly supported positive work, its actor and all material limits.
If an existing bullet already has this prefix, retain or replace that ONE prefix,
never prepend a second one. Preserve body times, ratios, URLs and other colons.
Legacy unprefixed bullets remain readable; do not infer labels from their colons.
If no short supported label is clear, leave the body unchanged for label review
rather than inventing one. Every new or changed label needs its own source
review. A body-only review cannot certify a label, and correct syntax is not
evidence of truth. Full-candidate review must include all visible label words.
'''

_PREFIX = re.compile(r'^\*\*([^*\r\n]*?)([:：])\*\*([ \t]*)(.*)$', re.S)


def parse_bullet(raw, language):
    if language not in ('en', 'zh') or not isinstance(raw, str):
        raise ValueError('string_bullet_and_language_required')
    result = {'original_text': raw, 'original_sha256': text_hash(raw), 'body': raw,
              'label': None, 'colon': None, 'separator': '', 'parse_status': 'needs_label_review',
              'source_review_status': 'pending', 'reason': 'missing_explicit_prefix'}
    match = _PREFIX.fullmatch(raw)
    if not match:
        if raw.startswith('**'): result['reason'] = 'malformed_explicit_prefix'
        return result
    label, colon, space, body = match.groups()
    reason = None
    if not label.strip() or label != label.strip(): reason = 'empty_or_padded_label'
    elif not body.strip(): reason = 'empty_body'
    elif re.search(r'[:：\r\n*\[\]<>/\\]', label): reason = 'ambiguous_label_punctuation'
    elif not any(c.isalpha() for c in label): reason = 'non_topic_prefix'
    elif language == 'en' and (len(label) > 48 or len(label.split()) > 6): reason = 'label_too_long'
    elif language == 'zh' and len(label) > 12: reason = 'label_too_long'
    elif body.startswith('**'): reason = 'repeated_or_ambiguous_prefix'
    if reason:
        result['reason'] = reason
        return result
    result.update(body=body, label=label, colon=colon, separator=space,
                  parse_status='parsed', reason=None)
    return result


def compose_bullet(label, body, language):
    """Explicit caller label, not a label generator. Repeated calls are idempotent."""
    old = parse_bullet(body, language)
    if old['parse_status'] == 'parsed':
        if old['label'] != label: raise ValueError('existing_label_differs_use_explicit_patch')
        return body
    if body.startswith('**'): raise ValueError('ambiguous_prefix_not_repaired_automatically')
    if any(body.startswith(label + colon) for colon in (':', '：')):
        raise ValueError('matching_plain_prefix_requires_explicit_review')
    value = '**' + label + ('：**' if language == 'zh' else ':** ') + body
    if parse_bullet(value, language)['parse_status'] != 'parsed':
        raise ValueError('invalid_explicit_label')
    return value


def adapt_document(doc, *, material_text, jd_text, source_links=None, origin=None):
    """Split only explicit prefixes; linked evidence is not assumed to support them.

    source_links is an optional stable-ID map of existing M: references. Without
    links the adapter still returns a body projection, but cannot render labels.
    """
    d.validate(doc)
    links = deepcopy(source_links or {})
    ids = {n['id'] for n in doc['nodes'] if n['kind'] == 'sentence'}
    if set(links) - ids: raise ValueError('source_link_for_unknown_bullet')
    projected = deepcopy(doc)
    records, labels, pending = {}, {}, []
    for node in projected['nodes']:
        if node['kind'] != 'sentence': continue
        ident = node['id']; record = parse_bullet(node['text'], doc['language'])
        refs = links.get(ident, [])
        located = [locate(material_text, ref, jd_text) for ref in refs]
        if any(x['status'] != 'unique' for x in located):
            raise ValueError('source_link_not_unique_personal_material:' + ident)
        record.update(id=ident, source_refs=refs, source_locations=located,
                      origin=deepcopy(origin), source_map_sha256=digest(catalogue(material_text, jd_text)))
        if record['parse_status'] == 'parsed':
            node['text'] = record['body']
            labels[ident] = {'text': record['label'], 'source_text': record['body'],
                             'source_facts': deepcopy(refs), 'source_review_status': 'pending',
                             'original_text': record['original_text'], 'original_sha256': record['original_sha256']}
        else:
            pending.append({'id': ident, 'route': 'source_review', 'code': 'needs_label_review',
                            'reason': record['reason'], 'closed': False, 'blocks_current_draft': True})
        records[ident] = record
    d.validate(projected)
    return {'protocol': LABEL_PROTOCOL, 'raw_document': deepcopy(doc),
            'raw_version': d.version(doc), 'render_document': projected,
            'render_version': d.version(projected), 'records': records, 'stable_labels': labels,
            'source_sha256': text_hash(material_text), 'jd_sha256': text_hash(jd_text),
            'pending_items': pending, 'automatic_label_factual_certification': False}


def validate_bundle(bundle):
    raw, projected = bundle['raw_document'], bundle['render_document']
    if d.version(raw) != bundle['raw_version'] or d.version(projected) != bundle['render_version']:
        raise ValueError('label_bundle_version_changed')
    expected = deepcopy(raw)
    ids, parsed_ids = set(), set()
    for node in expected['nodes']:
        if node['kind'] != 'sentence': continue
        ident = node['id']; ids.add(ident)
        parsed = parse_bullet(node['text'], raw['language'])
        record = bundle['records'].get(ident, {})
        if any(record.get(k) != v for k, v in parsed.items()):
            raise ValueError('label_record_not_bound_to_original')
        if parsed['parse_status'] == 'parsed':
            parsed_ids.add(ident); node['text'] = parsed['body']
            label = bundle['stable_labels'].get(ident, {})
            if (label.get('text') != parsed['label'] or label.get('source_text') != parsed['body']
                    or label.get('source_facts') != record.get('source_refs')):
                raise ValueError('label_sidecar_not_bound_to_original')
    if expected != projected or set(bundle['records']) != ids or set(bundle['stable_labels']) != parsed_ids:
        raise ValueError('label_projection_or_coverage_changed')
    return True


def label_document(bundle):
    """Different candidate version prevents body-only verdict reuse.

    Stable IDs remain unchanged. Full original bullet bodies accompany the review
    request as context so a generic topic cannot hide mismatched attribution.
    """
    validate_bundle(bundle)
    if bundle['pending_items']: raise ValueError('unparsed_labels_need_review_before_label_audit')
    doc = deepcopy(bundle['raw_document'])
    doc['document_id'] += '-labels-' + digest({'raw_version': bundle['raw_version'],
        'source_sha256': bundle['source_sha256'], 'jd_sha256': bundle['jd_sha256']})[:16]
    for node in doc['nodes']:
        if node['kind'] == 'sentence': node['text'] = bundle['records'][node['id']]['label']
    d.validate(doc)
    return doc


def build_label_review(bundle, *, skill, material_text, jd_text):
    from .requests import build, preflight
    if (text_hash(material_text) != bundle['source_sha256'] or
            text_hash(jd_text) != bundle['jd_sha256']): raise ValueError('label_review_source_changed')
    request = build('final_review', skill=skill, material_text=material_text, jd_text=jd_text,
                    candidate=label_document(bundle))
    request.pop('input_sha256')
    request['context']['label_review_context'] = {
        'raw_candidate_version': bundle['raw_version'],
        'labels_and_original_bodies': {i: {'label': r['label'], 'body': r['body']}
                                      for i, r in bundle['records'].items()},
        'instructions': 'Independently assess every listed lead-in against personal source material AND its exact body. '
                        'Return a check for every label ID, including generic-sounding topics. '
                        'Do not treat body-only reviews or source-link existence as label support. '
                        'Supported label checks require personal M: evidence. No prior verdicts are supplied.'}
    preflight(request)
    return {**request, 'input_sha256': digest(request)}


def label_gate(bundle, review, *, material_text, jd_text):
    from .reviews import audit_review
    if review is None or bundle['pending_items']:
        return {'status': 'needs_label_review', 'passed': False,
                'reason': 'missing_independent_label_review_or_unparsed_labels'}
    try:
        if text_hash(material_text) != bundle['source_sha256'] or text_hash(jd_text) != bundle['jd_sha256']:
            raise ValueError('label_review_source_changed')
        audited = audit_review(label_document(bundle), review, material_text, jd_text=jd_text)
        by = {x['id']: x for x in review['checks']}
        supported = all(i in by and by[i]['judgment'] == 'supported' and by[i]['evidence']
                        and all(locate(material_text, ref, jd_text)['status'] == 'unique' for ref in by[i]['evidence'])
                        for i in bundle['records'])
        passed = bool(supported and audited['coverage_complete'] and
                      audited['source_judgment'] == 'reviewer_reports_supported' and
                      not audited['unresolved_claim_ids'] and not audited['awaiting_user'] and
                      not audited['material_omissions'])
        return {'status': 'reviewer_reports_supported' if passed else 'needs_label_review',
                'passed': passed, 'audit': audited, 'review_sha256': digest(review),
                'raw_version': bundle['raw_version'], 'render_version': bundle['render_version'],
                'automatic_label_factual_certification': False}
    except ValueError as exc:
        return {'status': 'needs_label_review', 'passed': False, 'reason': str(exc)}


def renderer_for_bundle(bundle, module_path, *, material_text, jd_text, target_role, label_review=None,
                        body_presentation=None):
    """Use existing v2 renderer and measured tail/bold interface, never fake proofs.

    Render the body projection, not raw Markdown. Physical body hashes are never
    rewritten to raw hashes. Changed body/label requires fresh bindings/review.
    """
    from .presentation_port import make_renderer, bind_labels
    validate_bundle(bundle)
    if target_role != ('运营分析专员' if bundle['raw_document']['language'] == 'zh' else 'Operations Analysis Specialist'):
        raise ValueError('current_style_requires_explicit_operations_analysis_target')
    labels = deepcopy(bundle['stable_labels'])
    gate = label_gate(bundle, label_review, material_text=material_text, jd_text=jd_text)
    if gate['passed']:
        by = {x['id']: x for x in label_review['checks']}
        for ident, label in labels.items():
            label['source_facts'] = deepcopy(by[ident]['evidence'])
            label['source_review_status'] = 'reviewer_reports_supported'
    if bundle['pending_items'] or any(not x['source_facts'] for x in labels.values()):
        raise ValueError('needs_label_review_or_source_links_before_labeled_render')
    if body_presentation:
        old = bind_labels(bundle['render_document'], body_presentation)
        for ident, value in old.items():
            if ident not in labels or value['text'] != labels[ident]['text']:
                raise ValueError('presentation_label_disagrees_with_explicit_prefix')
            if '_bullet_break' in value: labels[ident]['_bullet_break'] = value['_bullet_break']
    renderer = make_renderer(module_path, labels)
    def render(doc, directory):
        if d.version(doc) != bundle['render_version']:
            raise ValueError('changed_body_requires_new_label_bundle_and_review')
        result = renderer(doc, directory)
        result['label_generation_binding'] = {'raw_version': bundle['raw_version'],
                                              'render_version': bundle['render_version'],
                                              'protocol': LABEL_PROTOCOL}
        result['label_source_review'] = gate
        result['pending_items'] = [{'route': 'source_review', 'code': 'independent_label_source_review',
                                    'closed': gate['passed'], 'blocks_current_draft': not gate['passed'],
                                    'reason': 'Separate current label review; body-only review cannot close this gate.'}]
        return result
    return render
