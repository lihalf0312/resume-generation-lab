"""Language identity and editorial aids; never semantic or rendering certification."""
import unicodedata

POLICY_VERSION = 'bilingual-semantics-local-1'
GUIDANCE = """
Bilingual source fidelity and writing:
- Independently select and write Chinese and English from original M: material. Review each language against original evidence before comparing them. Agreement between versions is not evidence. Keep dates, quantity units, actor/team attribution, role status, qualification and completion status faithful. The JD only guides selection.
- A subjectless resume bullet attributes its action to the applicant. An existing record, note, budget or project constraint does not establish that the applicant recorded, authored or managed it. Preserve passive and third-party attribution. Retain explicitly evidenced leadership and assistance at their actual scope.
- Organizing existing records does not necessarily mean authoring them. An activity not performed does not establish exclusion from assigned duties. Identifier logging alone does not establish scheduling purpose or improved efficiency. Preserve separately evidenced purposes and results without banning useful verbs.
- Keep proposed, projected, estimated, piloted, tested, completed and deployed states distinct. A purpose is not an achieved outcome. Keep measurements, recalled ranges, upper/lower bounds, percentage points versus relative percentages, population, time basis and numeric units. Seven entrances are not seven buildings; two JD passages are not two whole JDs. Convert ten-thousand notation only with exact quantity/unit preservation.
- Preserve employee, internship, volunteer, course/simulation and unknown status; never infer volunteering from unpaid-looking work. Course completion is not a degree award. Keep study dates separate from award dates and dataset coverage separate from work dates. JD requirements never establish proficiency, certification or eligibility.
- Natural Chinese and English need not have identical sentence counts, order or peripheral detail. Explain meaningful selection differences using existing review categories; do not invent a missing counterpart ID or force both versions to include every fact. A reasonable omission must not erase a material limitation and turn a retained conclusion into a stronger claim.
- Write concise Chinese with concrete actions and objects; avoid inflated slogans and translated English syntax. Write idiomatic English with precise verbs and normal spaces; avoid repetitive candidate narration and literal Chinese clause chains. Keep proper names, acronyms, tools, URLs and supplied degree/certificate names intact where appropriate. Chinese text may contain English terms; English text may retain original names. Do not impose Latin-only output or silently invent official translations.
- Do not infer photos, political information, contact details or language proficiency from output language. Language detection and script counts are advisory, not proof of truth, fluency, fonts or successful rendering. Keep necessary unresolved questions awaiting_user and produce only a supported safe draft.
"""


def validate_language_bindings(docs, *, bilingual=False):
    if not isinstance(docs, dict) or not docs:
        raise ValueError('language_candidate_mapping_required')
    if set(docs) - {'en', 'zh'} or bilingual and set(docs) != {'en', 'zh'}:
        raise ValueError('exact_bilingual_language_set_required' if bilingual else 'unsupported_candidate_language')
    for language, doc in docs.items():
        if not isinstance(doc, dict) or doc.get('language') != language:
            raise ValueError('candidate_language_binding_mismatch:' + language)
    return True


def validate_request_language(context, stage):
    if stage == 'bilingual_review':
        validate_language_bindings(context.get('candidates'), bilingual=True)
    elif stage != 'generate':
        doc = context.get('candidate')
        if not isinstance(doc, dict) or doc.get('language') not in {'en', 'zh'}:
            raise ValueError('candidate_language_required')
        task = context.get('adapter_task', '')
        expected = ('en' if task.endswith('_en') else 'zh' if task.endswith('_zh') else None)
        declared = {'English': 'en', 'Chinese': 'zh'}.get(context.get('requested_language'))
        if expected and doc['language'] != expected or declared and doc['language'] != declared:
            raise ValueError('requested_candidate_language_mismatch')
    return True


def language_advisories(doc):
    """Prioritize prose review only. Preserve all text, punctuation and Unicode."""
    language = doc['language']
    findings = []
    for node in doc['nodes']:
        if node['kind'] != 'sentence':
            continue
        text = node['text']
        letters = [c for c in text if unicodedata.category(c).startswith('L')]
        han = sum('CJK UNIFIED IDEOGRAPH' in unicodedata.name(c, '') or
                  'CJK COMPATIBILITY IDEOGRAPH' in unicodedata.name(c, '') for c in letters)
        code = None
        if language == 'en' and len(letters) >= 6 and han / len(letters) > .35:
            code = 'english_prose_has_substantial_han_review_language'
        elif language == 'zh' and han == 0 and len(text.split()) >= 4:
            code = 'chinese_prose_has_no_han_review_language'
        if code:
            findings.append({'id': node['id'], 'language': language, 'code': code,
                             'automatic_block': False, 'language_verified': None,
                             'reason': 'Review intended prose language; proper names and technical terms may legitimately be mixed.'})
    return findings


# Successor-only display preference; the previous frozen study is unchanged.
from .education_display import EDUCATION_DATE_GUIDANCE
GUIDANCE += EDUCATION_DATE_GUIDANCE

from .section_order import SECTION_ORDER_GUIDANCE
GUIDANCE += SECTION_ORDER_GUIDANCE

# Future requests only: source-fidelity delta, not deterministic prose rewriting.
from .semantic_precision import SEMANTIC_PRECISION_GUIDANCE
GUIDANCE += SEMANTIC_PRECISION_GUIDANCE
