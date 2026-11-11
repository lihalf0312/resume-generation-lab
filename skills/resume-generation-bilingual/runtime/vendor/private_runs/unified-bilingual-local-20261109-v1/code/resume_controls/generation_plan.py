"""Single shared builder for the frozen two bodies and the executable pipeline."""
from .requests import build, preflight
from .common import digest


def generation_request(source, language, skill, guidance=''):
    if language not in ('en', 'zh'): raise ValueError('requested_language_required')
    request = build('generate', skill=skill, material_text=source['material_text'], jd_text=source['jd_text'])
    request.pop('input_sha256')
    request['context'].update(requested_language='English' if language == 'en' else 'Chinese',
                              adapter_task='generate_' + language)
    if guidance: request['context']['rules'] += '\nExplicit source-only editorial guidance:\n' + guidance
    preflight(request)
    return {**request, 'input_sha256': digest(request)}
