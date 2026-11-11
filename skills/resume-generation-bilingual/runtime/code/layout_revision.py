"""Explicit caller-selected, source-reviewed, measured tail-only editing route.

This is a proposal scope, not factual or layout approval. It never calls a model.
"""
from copy import deepcopy
from resume_controls.common import digest
from resume_controls.citations import catalogue
from review_feedback import build_repair_plan,_feedback
from tail_guidance import build_tail_guidance

def build_layout_plan(deliverable,receipt,source,basis,bundle,rendered):
    source_plan=build_repair_plan(deliverable,receipt,source,basis)
    plan=deepcopy(source_plan);plan.pop('plan_version',None)
    plan.update(requested_mode='explicit_layout_only',body_feedback=[],auxiliary_feedback=[],can_dispatch=False,
                route='needs_review',allowed_operations=['replace'],auxiliary_changes_allowed=False,
                automatic_source_truth_certified=False,layout_acceptance=False)
    guidance=None
    def finish():return {**plan,'plan_version':digest(plan)},guidance
    if (source_plan['route']!='no_revision_needed' or source_plan['audit'].get('passed') is not True
            or source_plan['audit'].get('delivery_ready') is not True):
        plan['unresolved']=source_plan['unresolved']+[{
            'unit_id':None,'risk_kind':'source_review_required_before_layout_only',
            'why':'Resolve current full-deliverable source review before requesting layout-only edits.',
            'review_question':'Complete current source review; do not hide source defects as layout changes.'}]
        return finish()
    try:guidance=build_tail_guidance(bundle,rendered,source)
    except (ValueError,OSError,TypeError,KeyError) as exc:
        plan['unresolved']=[{'unit_id':None,'risk_kind':'stale_or_missing_measured_layout','why':str(exc),
            'review_question':'Render and measure the exact current candidate; cached ratios cannot authorize edits.'}]
        return finish()
    plan['binding']['measured_tail_guidance_sha256']=guidance['guidance_sha256']
    plan['binding']['measured_pdf_sha256']=guidance['binding']['pdf_sha256']
    units={u['id']:u for u in deliverable['units']};nodes={n['id']:n for n in bundle['raw_document']['nodes']}
    checks={c['id']:c for c in receipt['checks']};blocks=catalogue(source['material_text'],source['jd_text'])
    affected=guidance['summary']['short_tail_ids']+guidance['summary']['cross_page_ids']
    for ident in sorted(set(affected)):
        unit=units.get(ident);check=checks.get(ident)
        if not unit or unit['kind']!='body' or not check or not check['evidence']:
            plan['unresolved'].append({'unit_id':ident,'risk_kind':'affected_body_has_no_located_source_evidence',
                'review_question':'Supply source-bound support before rewriting this affected bullet.'})
            continue
        item=_feedback(unit,check,units,nodes,source,blocks)
        item.update(risk_kind='measured_layout_issue_not_a_factual_error',
            resolution_policy='natural_prose_only_preserve_all_facts_actors_limits_and_existing_label',
            review_question='Propose concise natural prose for this measured bullet only. Preserve every supported claim, quantity, actor, qualifier and label. No padding, forced line breaks, deletion, split/merge or smaller typography. Re-render and independently review the entire result.',
            preserve_units=[deepcopy(u) for u in units.values() if u['kind']=='label' and u['owner_id']==ident],
            measured_layout=deepcopy(next(b for b in guidance['bullets'] if b['id']==ident)))
        plan['body_feedback'].append(item)
    if plan['unresolved']:
        plan['body_feedback']=[]
    elif plan['body_feedback']:
        plan.update(route='layout_only',can_dispatch=True)
    else:plan['route']='no_layout_revision_needed'
    return finish()
