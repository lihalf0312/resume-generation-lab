"""Measured pagination feedback. Flow spans are not exact required semantic cuts."""
from . import document as d
from .common import finite_number

def feedback(doc,measurement,heading_locations=None,tail_unit_ids=None):
 d.validate(doc);g=measurement.get('geometry_pt',{});required=['page_height','top_margin','bottom_margin'];known=all(finite_number(g.get(k)) for k in required)
 available=g['page_height']-g['top_margin']-g['bottom_margin'] if known else None
 if available is not None and available<=0:available=None
 pages=measurement.get('pages_detail',[]);heights=[]
 for page in pages:
  boxes=[line.get('bbox') for line in page.get('text_lines',[]) if isinstance(line.get('bbox'),list) and len(line['bbox'])==4 and all(finite_number(x) for x in line['bbox'])]
  heights.append(max(0,max(b[3] for b in boxes)-g['top_margin']) if boxes and available is not None else None)
 page_count=measurement.get('pages');flow=(page_count-1)*available+heights[-1] if type(page_count)is int and page_count==len(heights) and heights and heights[-1]is not None and available is not None else None
 locations=heading_locations or {};sections=[];sectionnodes=[n for n in doc['nodes'] if n['kind']=='section'];ordered=[]
 for s in sectionnodes:
  hits=locations.get(s['id'],[])
  point=(hits[0]['page']-1)*available+hits[0]['y0']-g['top_margin'] if len(hits)==1 and available is not None else None;ordered.append(point)
 for i,s in enumerate(sectionnodes):
  end=ordered[i+1] if i+1<len(ordered) else flow;start=ordered[i]
  height=end-start if start is not None and end is not None and end>=start else None
  sections.append({'section_id':s['id'],'heading':s['text'],'purpose':s['purpose'],'observed_flow_span_pt':round(height,3) if height is not None else None,'includes_pagination_gaps':True,'protected_evidence_present':bool(d.descendants(doc,s['id'])&set(doc['protected_ids'])),'unknown_reason':None if height is not None else 'heading/location/order not uniquely measurable'})
 tail=pages[-1].get('text_lines',[]) if pages and page_count and page_count>1 else []
 return {'candidate_version':d.version(doc),'language':doc['language'],'available_body_height_pt':available,'includes_fixed_name_target_and_synthetic_header':True,'occupied_height_by_page_pt':heights,'observed_flow_span_pt':flow,'observed_overflow_flow_span_pt':max(0,flow-available) if flow is not None else None,'exact_height_to_remove_to_fit_one_page_pt':None,'exact_cut_unknown_reason':'Keep-with-next, line wrapping and page breaks are nonlinear; observed overflow span is not guaranteed required cut. Re-render after a bounded patch.','actual_pages':page_count,'tail_page_content':tail,'tail_page_candidate_unit_ids':tail_unit_ids,'tail_unit_mapping_unknown':tail_unit_ids is None,'section_consumption':sections,'template_geometry_pt':g,'font_sizes_pt':measurement.get('explicit_run_font_sizes_pt'),'word_count_limit':None,'word_count_limit_reason':'No cross-language/font word-count guarantee; actual fixed-template rendering controls.','sparse_selection_attention':any(p.get('body_utilization_pct',100)<65 for p in pages),'sparse_does_not_mean_pad_or_fail':True}

def allocate_space(capacity,priorities):
 """Selection weights are reviewer judgments; output is a proposal, not measurement."""
 sections={s['section_id']:s for s in capacity['section_consumption']}
 if not priorities:return {'section_budgets':None,'basis':'No source/JD selection priorities supplied; do not fabricate a relevance ranking.'}
 if set(priorities)!=set(sections) or any(type(x)is not int or not 1<=x<=5 for x in priorities.values()):raise ValueError('selection_priority_contract')
 available=capacity['available_body_height_pt']
 if available is None:return {'section_budgets':None,'basis':'Available height unknown.'}
 total=sum(priorities.values())
 return {'section_budgets':[{'section_id':k,'relevance_weight':v,'proposed_share_of_body_pt':round(available*v/total,3),'protected_evidence_present':sections[k]['protected_evidence_present']} for k,v in priorities.items()],'measurement':False,'basis':'Relative JD selection priorities, not permission to delete required education/qualifiers or a fit guarantee; includes fixed header overhead, so further capacity is needed.'}
