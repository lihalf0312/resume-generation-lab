"""Explicit education-date display plans. Source evidence is never deleted.

This is a deterministic projection of editor-annotated fields, NOT an NLP
status/date extractor. Use the changed candidate for fresh source review and
rendering; do not apply this after a candidate has been frozen or accepted.
"""
from copy import deepcopy
from . import document as d
from .common import text_hash
from .citations import resolve_all

EDUCATION_DATE_GUIDANCE = """
Education date display (current user preference):
For graduates, do not separately display a degree-conferral or graduation date by default, including a separate 'degree awarded ...' bullet or suffix. A normal source-supported study-period range may remain. Preserve degree/qualification status and all original dates in source/evidence records; omission from display is not factual withdrawal. Do not merge different study-end and award dates into one falsely asserted event.
Only when current enrollment is explicitly confirmed should a supplied expected graduation date normally be displayed, labeled 'Expected graduation: ...' in English or '预计毕业：...' in Chinese. Do not infer enrollment from a date range, an incomplete degree, course completion or the current calendar date. Missing expected dates remain missing; never invent one. Unknown, withdrawn or coursework-only status is not 'graduated' or 'currently enrolled'.
An explicit user request or a job/application requirement for a specific education date overrides the display default, but can only use source-supported dates. Preserve that requirement and date meaning. A request to show graduation date does not authorize substituting degree-conferral date. Do not treat the safe default omission of an award date as a factual defect or important omission. Retain a material qualification/status limitation if removing it would imply a completed degree. Section order follows the separately confirmed career-stage/education-advantage display policy; do not change fonts or page geometry.
"""

FIELDS = ('study_period', 'expected_graduation', 'graduation', 'degree_conferral')
STATUSES = {'enrolled', 'graduated', 'unknown', 'coursework_completed', 'withdrawn'}


def date_plan(*, language, status, study_period='', expected_graduation='', graduation='', degree_conferral='', required_fields=(), requirement_reason=''):
    if language not in {'en','zh'} or status not in STATUSES:
        raise ValueError('explicit_supported_language_and_education_status_required')
    values={'study_period':study_period,'expected_graduation':expected_graduation,'graduation':graduation,'degree_conferral':degree_conferral}
    if any(not isinstance(v,str)for v in values.values()):raise ValueError('education_dates_must_be_text')
    if not isinstance(required_fields,(list,tuple)) or any(v not in FIELDS for v in required_fields) or len(set(required_fields))!=len(required_fields):
        raise ValueError('required_education_fields_must_be_unique_known_names')
    if required_fields and (not isinstance(requirement_reason,str) or not requirement_reason.strip()):
        raise ValueError('specific_user_or_application_requirement_reason_required')
    if 'expected_graduation' in required_fields and status!='enrolled':raise ValueError('expected_graduation_requires_confirmed_enrollment')
    visible=['study_period']
    if status=='enrolled':visible.append('expected_graduation')
    visible.extend(f for f in required_fields if f not in visible)
    missing=[f for f in visible if not values[f].strip() and (f in required_fields or f=='expected_graduation')]
    # Source text is preserved byte-for-byte in retained_source_dates; only the
    # derived display trims outer whitespace and adds an explicit event label.
    labels={'en':{'expected_graduation':'Expected graduation: ','graduation':'Graduated: ','degree_conferral':'Degree conferred: '},'zh':{'expected_graduation':'预计毕业：','graduation':'毕业：','degree_conferral':'学位授予：'}}
    parts=[labels[language].get(f,'')+values[f].strip()for f in visible if values[f].strip()]
    return {'language':language,'status':status,'display_text':('; 'if language=='en'else'；').join(parts),'retained_source_dates':deepcopy(values),'shown_fields':[f for f in visible if values[f].strip()],'omitted_fields':[f for f in FIELDS if f not in visible and values[f].strip()],'missing_requested_fields':missing,'required_fields':list(required_fields),'requirement_reason':requirement_reason,'source_status_verified':None,'source_date_meaning_verified':None}


def apply_date_plan(doc, date_id, plan, *, base_version, original_hash, source_text, source_refs):
    """Create a versioned display candidate, never mutate sources or frozen docs.

    Caller must supply the current node/version and original-material citations.
    Only an education date field can change. Standalone/combined prose needs an
    ordinary source-linked semantic edit; this helper never regex-deletes it.
    """
    d.validate(doc)
    if base_version!=d.version(doc):raise ValueError('stale_education_display_candidate')
    node=d.units(doc).get(date_id)
    if node is None or node['kind']!='date' or node['purpose']!='education':raise ValueError('education_date_node_required')
    if original_hash!=text_hash(node['text']):raise ValueError('stale_education_date_text')
    if not isinstance(plan,dict):raise ValueError('education_date_plan_required')
    expected=date_plan(language=doc['language'],status=plan.get('status'),**plan.get('retained_source_dates',{}),required_fields=plan.get('required_fields',()),requirement_reason=plan.get('requirement_reason',''))
    # Store exception selections explicitly so reconstruction cannot silently
    # mistake a one-off requirement for the default policy.
    canonical=plan
    if canonical!=expected:raise ValueError('education_date_plan_changed_or_wrong_language')
    if not isinstance(source_refs,list)or not source_refs:raise ValueError('education_date_display_requires_original_material_evidence')
    locations=resolve_all(source_text,source_refs,personal=True)
    if any(l['status']!='unique'for l in locations):raise ValueError('education_date_evidence_not_unique')
    result=deepcopy(doc);changed=node['text']!=plan['display_text']
    if changed:
        next(n for n in result['nodes']if n['id']==date_id)['text']=plan['display_text'];result['revision']+=1
    d.validate(result)
    return result,{'base_version':d.version(doc),'result_version':d.version(result),'date_id':date_id,'before':node['text'],'after':plan['display_text'],'changed':changed,'source_dates_retained':deepcopy(plan['retained_source_dates']),'source_evidence':locations,'source_text_sha256':text_hash(source_text),'source_text_unchanged':True,'section_order_unchanged':True,'source_review_required':changed,'render_required':changed,'semantic_truth_automatically_certified':False}
