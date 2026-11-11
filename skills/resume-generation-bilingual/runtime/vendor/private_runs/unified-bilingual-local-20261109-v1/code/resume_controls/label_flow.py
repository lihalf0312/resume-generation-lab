"""Reusable generation/patch entry points using the caller's existing callback.

No transport, retry, budget, journal or credentials. The owning runner persists
returned requests/results with its existing confirmed/unknown outcome rules.
"""
from . import document as d
from .requests import build
from .schemas import SCHEMAS, validate
from .patches import apply_patch
from .bullet_labels import adapt_document, build_label_review, label_gate


def generate(*, stage, key, skill, material_text, jd_text, document_id, language, prepared_request=None):
    from .common import digest
    if language not in ('en', 'zh'): raise ValueError('unsupported_language')
    request = build('generate', skill=skill, material_text=material_text, jd_text=jd_text)
    request.pop('input_sha256')
    request['context']['requested_language'] = 'English' if language == 'en' else 'Chinese'
    request['input_sha256'] = digest(request)
    if prepared_request is not None:
        from copy import deepcopy
        from .requests import preflight
        supplied = deepcopy(prepared_request)
        clean = {k: v for k, v in supplied.items() if k != 'input_sha256'}
        preflight(clean)
        if (clean['stage'] != 'generate' or digest(clean) != supplied['input_sha256']
                or supplied['context']['source_blocks'] != request['context']['source_blocks']
                or supplied['context'].get('requested_language') != request['context']['requested_language']):
            raise ValueError('prepared_generation_binding_mismatch')
        request = supplied
    response = stage(key, request)
    validate(SCHEMAS['generate'], response)
    raw, paths = d.ingest(response['resume'], document_id, language,
                          intent_context=d.goal_context(jd_text))
    bundle = adapt_document(raw, material_text=material_text, jd_text=jd_text,
                            origin={'stage_key': key, 'request_sha256': request['input_sha256'],
                                    'response_sha256': digest(response)})
    return {'request': request, 'response': response, 'bundle': bundle, 'paths': paths,
            'generation_state': response['state'], 'source_review_pending': True}


def revise(raw_document, *, stage, key, skill, material_text, jd_text, capacity, issues=()):
    from .common import digest
    from .requests import preflight
    before = adapt_document(raw_document, material_text=material_text, jd_text=jd_text)
    if capacity.get('candidate_version') not in (None, before['raw_version'], before['render_version']):
        raise ValueError('capacity_not_bound_to_raw_or_render_projection')
    request = build('patch', skill=skill, material_text=material_text, jd_text=jd_text,
                    candidate=raw_document, capacity=capacity, issues=issues)
    request.pop('input_sha256')
    request['context']['label_projection_binding'] = {
        'raw_candidate_version': before['raw_version'], 'render_candidate_version': before['render_version'],
        'capacity_candidate_version': capacity.get('candidate_version'),
        'physical_measurements_unchanged': True,
        'instruction': 'Patch the original stable-ID strings including one explicit label prefix. '
                       'Physical body measurements refer to the separately bound body projection; '
                       'do not overwrite measured hashes or reuse label reviews after a change.'}
    preflight(request)
    request['input_sha256'] = digest(request)
    response = stage(key, request)
    validate(SCHEMAS['patch'], response)
    revised, audit = apply_patch(raw_document, response, material_text, jd_text)
    return {'request': request, 'response': response, 'patch_audit': audit,
            'bundle': adapt_document(revised, material_text=material_text, jd_text=jd_text,
                                     origin={'stage_key': key, 'request_sha256': request['input_sha256']}),
            'source_review_pending': True}


def review_labels(bundle, *, stage, key, skill, material_text, jd_text):
    request = build_label_review(bundle, skill=skill, material_text=material_text, jd_text=jd_text)
    response = stage(key, request)
    return {'request': request, 'response': response,
            'gate': label_gate(bundle, response, material_text=material_text, jd_text=jd_text)}
