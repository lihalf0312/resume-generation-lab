"""Stable section selection order from explicit facts/preferences, not school ranking."""
from copy import deepcopy
from . import document as d

SECTION_ORDER_GUIDANCE = """
Section order (confirmed default): an explicit user-specified order takes priority. Otherwise, students and recent graduates usually put Education first; candidates with substantial relevant experience can put Experience first. Source-supported educational strengths or the user's judgment that their education is a particular advantage can justify Education first even for an experienced candidate. Do not invent school prestige/rankings or infer recent-graduate status from a guessed date threshold. Preserve the relative order of the other sections and all within-section content, unless separately justified. Keep the approved template typography, geometry and current sample layout. Richer content must come from richer authorized sources and relevant evidence, never padding to fill a page.
"""


def apply_section_order(doc, *, base_version, user_order=None, career_stage='unknown', stage_basis='', substantial_relevant_experience=False, experience_basis='', education_advantage=False, education_basis=''):
    d.validate(doc)
    if base_version!=d.version(doc):raise ValueError('stale_section_order_candidate')
    if career_stage not in {'enrolled','recent_graduate','experienced','unknown'}:raise ValueError('explicit_career_stage_required')
    if type(substantial_relevant_experience)is not bool or type(education_advantage)is not bool:raise ValueError('explicit_boolean_selection_flags_required')
    sections=[n for n in doc['nodes']if n['kind']=='section'];ids=[n['id']for n in sections]
    reason='preserve_existing_order';priority=None
    if user_order is not None:
        if not isinstance(user_order,list)or len(user_order)!=len(ids)or set(user_order)!=set(ids):raise ValueError('user_order_must_list_each_current_section_once')
        ordered=list(user_order);reason='explicit_user_order'
    else:
        if career_stage!='unknown' and (not isinstance(stage_basis,str)or not stage_basis.strip()):raise ValueError('career_stage_requires_source_or_user_basis')
        if education_advantage and (not isinstance(education_basis,str)or not education_basis.strip()):raise ValueError('education_advantage_requires_source_or_user_basis')
        if substantial_relevant_experience and (not isinstance(experience_basis,str)or not experience_basis.strip()):raise ValueError('relevant_experience_requires_source_or_user_basis')
        if education_advantage:priority='education';reason='confirmed_education_advantage'
        elif career_stage in {'enrolled','recent_graduate'}:priority='education';reason='confirmed_student_or_recent_graduate'
        elif substantial_relevant_experience:priority='experience';reason='confirmed_relevant_experience'
        ordered=[n['id']for n in sections if n['purpose']==priority]+[n['id']for n in sections if n['purpose']!=priority]if priority else ids[:]
    result=deepcopy(doc);changed=ordered!=ids
    if changed:
        names=[n for n in result['nodes']if n['kind']=='name']
        groups={i:[n for n in result['nodes']if n['id']in d.descendants(result,i)]for i in ids}
        result['nodes']=names+[n for i in ordered for n in groups[i]];result['revision']+=1
    d.validate(result)
    return result,{'base_version':d.version(doc),'result_version':d.version(result),'before':ids,'after':ordered,'changed':changed,'reason':reason,'source_or_user_basis':{'career_stage':stage_basis,'experience':experience_basis,'education':education_basis},'school_ranking_inferred':False,'text_and_dates_unchanged':True,'within_section_order_unchanged':True,'font_or_geometry_changed':False,'render_required':changed,'semantic_truth_automatically_certified':False}
