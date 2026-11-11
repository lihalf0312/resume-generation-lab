"""Actual request-builder overlay. No provider, credential or accounting code."""
import importlib.util
from . import BASELINE
from .common import digest
from .bullet_labels import LABEL_GUIDANCE, LABEL_PROTOCOL

_spec = importlib.util.spec_from_file_location(__package__ + '._label_baseline_requests',
                                             BASELINE / 'code/resume_controls/requests.py')
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
RULES, GUIDANCE = _base.RULES, _base.GUIDANCE + LABEL_GUIDANCE
load_skill = _base.load_skill
PRESENTATION_GUIDANCE = '''
Unified approved heading contract, new generations and explicit heading replacements:
Use Project Experience for English sections whose purpose is projects. Put each
project's own name first, then its organization affiliation, as Project name | Organization.
For experience and education, put the organization or school name first, then
the role or degree, separated by |. The FIRST complete component declares the
primary proper name to emphasize; do not put a role, date or invented entity
there. Preserve affiliation and all project/employment status distinctions.
The renderer bolds only that name, not the following role, affiliation or date.
Retain source names or a clearly descriptive translation when an official
English name is unknown. Do not invent projects, independent work or titles.
This is a display contract, not source approval. Every actual visible heading
and every bullet lead-in remains subject to source review. Other language,
education-date, section-order and source-fidelity guidance still applies.
'''


def preflight(request):
    _base.preflight(request)
    if request['context'].get('bullet_label_protocol') != LABEL_PROTOCOL:
        raise ValueError('bullet_label_protocol_missing_or_changed')
    if LABEL_GUIDANCE not in request['context']['rules']:
        raise ValueError('bullet_label_guidance_missing')
    if PRESENTATION_GUIDANCE not in request['context']['rules']:
        raise ValueError('unified_heading_guidance_missing')
    return True


def build(stage, **kwargs):
    request = _base.build(stage, **kwargs)
    request.pop('input_sha256')
    request['context']['rules'] += LABEL_GUIDANCE + PRESENTATION_GUIDANCE
    request['context']['entry_heading_contract'] = 'primary-name-first-pipe-v1'
    request['context']['bullet_label_protocol'] = LABEL_PROTOCOL
    preflight(request)
    return {**request, 'input_sha256': digest(request)}
