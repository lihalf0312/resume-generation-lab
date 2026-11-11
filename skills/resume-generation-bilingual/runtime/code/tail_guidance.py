"""Read-only, PDF-bound revision guidance. No network, rewrites or layout shortcuts.

The diagnosis is reusable and deliberately does not certify source semantics.
Budgets use measured glyph advances; every changed text must be rendered again.
"""
from pathlib import Path
from collections import Counter
from statistics import median
import copy, hashlib, json, math, re

PROTOCOL = 'measured-tail-guidance-v1'
def _hash(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def _digest(v): return _hash(json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False))
def _file(p):
    p = Path(p)
    if p.is_symlink() or not p.is_file(): raise ValueError('tail_evidence_file_missing_or_symlink')
    return hashlib.sha256(p.read_bytes()).hexdigest()
def _read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def _compact(s): return ''.join(c for c in s if not c.isspace())
def _finite(v): return type(v) in (float, int) and math.isfinite(v)
def _validate_bundle(bundle):
    from resume_controls import document as d
    for key in ('raw', 'render'):
        if d.version(bundle[key+'_document']) != bundle[key+'_version']: raise ValueError('tail_stale_'+key+'_version')
    nodes = {n['id']: n for n in bundle['render_document']['nodes'] if n['kind']=='sentence'}
    if set(nodes) != set(bundle['records']): raise ValueError('tail_record_ids_mismatch')
    for ident, n in nodes.items():
        if bundle['records'][ident]['body'] != n['text']: raise ValueError('tail_record_body_mismatch')
    return nodes

def _fresh_measurement(bundle, rendered):
    """Re-run the existing strict ordered DOCX/PDF mapper; never trust a ratio alone."""
    from resume_controls.physical_tail_review import measure_tail_lines
    nodes = _validate_bundle(bundle)
    pdf = Path(rendered.get('pdf') or rendered.get('pdf_path') or '')
    docx = Path(rendered.get('docx') or '')
    actual_hash = _file(pdf)
    if actual_hash != rendered.get('pdf_sha256'): raise ValueError('tail_stale_pdf')
    if rendered.get('candidate_version') != bundle['render_version']: raise ValueError('tail_wrong_candidate_version')
    old = rendered.get('measurement', {}).get('tail_line_review', {})
    if not old.get('mapping_complete') or old.get('pdf_sha256') != actual_hash: raise ValueError('tail_mapping_unverified')
    content = Path(rendered.get('content_path') or docx.parent/'content.json')
    _file(content); _file(docx)
    rows = _read(content)['paragraphs']; physical = {r['id']: r for r in rows if r['kind']=='bullet'}
    cached = old.get('bullets', [])
    if len(cached)!=len(nodes) or len({x['id'] for x in cached})!=len(cached) or {x['id'] for x in cached}!=set(nodes): raise ValueError('tail_incomplete_stable_ids')
    by_physical = {x.get('physical_row_id', x['id']):x for x in cached}
    if len(by_physical)!=len(cached) or set(by_physical)!=set(physical): raise ValueError('tail_physical_id_mismatch')
    fresh = measure_tail_lines(pdf, docx, rows)
    if not fresh['mapping_complete']: raise ValueError('tail_fresh_mapping_failed')
    result = []
    for m in fresh['bullets']:
        prior = by_physical[m['id']]; ident = prior['id']; row = physical[m['id']]
        body = row.get('break_source_text', row['text'])
        if body != nodes[ident]['text'] or m['source_text_sha256'] != _hash(body): raise ValueError('tail_text_binding_mismatch')
        record = bundle['records'][ident]
        if row.get('label','') != record['label']+record['colon']: raise ValueError('tail_label_binding_mismatch')
        if row.get('label_source',{}).get('stable_id') not in (None,ident): raise ValueError('tail_label_wrong_stable_id')
        for key in ('source_text_sha256','physical_lines','available_width_pt','width_pt','line_details'):
            if prior.get(key) != m[key]: raise ValueError('tail_cached_measurement_changed:'+key)
        if not _finite(prior.get('ratio')) or abs(prior['ratio']-m['width_pt']/m['available_width_pt'])>1e-5: raise ValueError('tail_ratio_not_measured')
        result.append({**m, 'physical_row_id':m['id'], 'id':ident})
    return pdf, fresh, result

_NUM = re.compile(r'\d+(?:[.,]\d+)*(?:\s*%|％)?|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)\b|[一二三四五六七八九十百千万两]+(?=[个名条篇张类份次周月年项步页])',re.I)
_NEG = re.compile(r'\b(?:not|no|without|only|separately|independent|unrecorded|unmeasured|unverified|different|non[- ]comparable|cannot)\b|未|不|仅|只|分别|独立|非同批|不同|不推断|无记录',re.I)
_ACTOR = re.compile(r'\b(?:supervisor|manager|lead|staff|colleague|support|responsible|confirmed|approved|decid\w*|maintain\w*)\b|主管|经理|负责人|同事|工程支持|负责|确认|决定|维护|审核|审批',re.I)
_CARRIER = re.compile(r'\b(?:was|were) responsible for\b|\b(?:in order to|for the purpose of|with respect to)\b|根据|进行|负责|其中|分别为',re.I)

def _spans(text):
    """Keep complete clauses, including their punctuation and source offsets."""
    spans=[];start=0
    for edge in re.finditer(r'[。；;!?！？]|(?<!\d)\.(?=\s|$)',text):
        end=edge.end()
        if text[start:end].strip():spans.append({'start':start,'end':end,'text':text[start:end]})
        start=end
    if text[start:].strip():spans.append({'start':start,'end':len(text),'text':text[start:]})
    return spans

def _protections(text, node, record):
    clauses = _spans(text)
    return {'quantities':[{'text':m.group(),'start':m.start(),'end':m.end()} for m in _NUM.finditer(text)],
            'negative_scope_and_comparison_clauses':[x for x in clauses if _NEG.search(x['text'])],
            'actor_responsibility_clauses':[x for x in clauses if _ACTOR.search(x['text'])],
            'all_claim_clauses':clauses,'parent_entry_id':node['parent'],'purpose':node['purpose'],
            'label':record['label']+record['colon'],'source_refs':copy.deepcopy(record.get('source_refs',[])),'source_scope_review_required':True,
            'rule':'Preserve each claim and its attached number, timeframe, population, comparison limit, negation and actor. Lexical checks are incomplete; semantic source review remains mandatory.'}

def _glyph_profile(pdf, lines):
    """Widths of real embedded PDF glyph boxes, excluding justified inter-glyph gaps.

    This is a measured natural-advance proxy, not a promise of wrapping. Spaces
    use the smallest same-font observed space width to avoid counting stretched
    justification as content. Real re-rendering is the only acceptance test.
    """
    import pymupdf as fitz
    with fitz.open(pdf) as d:
        space = {}; selected = []; allchars = {}
        for pi in sorted({x['page'] for x in lines}):
            cs = [dict(c,font=sp['font'],size=sp['size']) for b in d[pi-1].get_text('rawdict')['blocks'] for l in b.get('lines',[]) for sp in l['spans'] for c in sp['chars']]
            allchars[pi] = cs
            for c in cs:
                if c['c']==' ': space.setdefault((c['font'],c['size']),[]).append(c['bbox'][2]-c['bbox'][0])
        for line in lines:
            x0,_,x1,_ = line['bbox']; y = line['baseline_pt']
            cs = [c for c in allchars[line['page']] if abs(c['origin'][1]-y)<.8 and c['bbox'][0]>=x0-.02 and c['bbox'][2]<=x1+.02]
            if _compact(''.join(c['c'] for c in cs)) != _compact(line['text']): raise ValueError('tail_glyph_line_mismatch')
            selected.extend(cs)
    total = 0.; widths = {}; fonts = set(); nonspace = 0
    for c in selected:
        w = c['bbox'][2]-c['bbox'][0]
        if c['c'].isspace(): w=min(space.get((c['font'],c['size']),[w]))
        else: widths.setdefault(c['c'],[]).append(w);nonspace+=1
        total+=w;fonts.add((c['font'],round(c['size'],5)))
    values=[median(ws) for ws in widths.values()];mean=sum(values)/len(values) if values else 0
    return {'natural_advance_proxy_pt':round(total,4),'nonspace_glyph_count':nonspace,
            'median_nonspace_glyph_width_pt':round(median(values),4) if values else 0,
            'observed_glyph_widths_pt':{c:round(median(ws),5) for c,ws in sorted(widths.items())},
            'fonts_and_sizes':[{'font':f,'size_pt':s} for f,s in sorted(fonts)],
            'method':'Sum actual PDF glyph bbox widths; same-font minimum observed space width, no justified gaps. Proxy only; contextual shaping and word boundaries require re-render.'}

def _budgets(m, profile):
    w=m['available_width_pt'];n=m['physical_lines'];advance=profile['natural_advance_proxy_pt'];g=profile['median_nonspace_glyph_width_pt']
    if n==1:return {'single_line_exempt':True,'do_not_pad':True,'recommended_operations':[]}
    # Removing a line is a compression budget, never a demand to drop a fact.
    first_offset=max(0,m['line_details'][0]['bbox'][0]-m['body_left_pt']);target=(n-1)*w-first_offset;reduction=max(0,advance-target)
    return {'basis':'approximate_natural_glyph_advance_not_character_count','requires_real_remeasurement':True,
            'same_line_count':{'lines':n,'tail_hard_min_pt_exclusive':w*.5,'tail_preferred_pt':[w*2/3,w*.8],
                'current_tail_deficit_pt_exclusive':max(0,w*.5-m['width_pt']),
                'instruction':'Reorder/compress complete clauses only if all lines remain natural. A deficit is NOT permission to add words; no hard line breaks or reduced line width.'},
            'one_fewer_line':{'target_lines':n-1,'total_natural_advance_ceiling_pt':round(target,4),'observed_first_line_start_offset_pt':round(first_offset,4),
                'approx_reduction_to_capacity_pt':round(reduction,4),'conservative_reduction_target_pt':round(reduction+w*.025,4),
                'approx_typical_glyph_equivalents':round(reduction/g,1) if g else None,
                'wrap_pressure':'word_or_run_boundary_fragmentation' if reduction==0 else 'substantial_compression' if reduction/max(advance,1)>.2 else 'modest_compression',
                'zero_deficit_note':'Zero aggregate deficit does not mean it fits: greedy word wrapping, labels and run boundaries can still require another line.',
                'instruction':'First test shorter carrier grammar and repeated framing. Keep every fact/limit. This budget is not an exact word quota or a guarantee of fitting.'},
            'add_content_to_fill_tail':False,'font_or_margin_change_allowed':False,'hard_line_breaks_allowed':False}

def _opportunities(body, protections, node, nodes, records):
    carriers=[{'quote':m.group(),'start':m.start(),'end':m.end(),'action':'Compress carrier grammar while keeping the complete payload and the same responsible actor.'} for m in _CARRIER.finditer(body)]
    clauses=protections['all_claim_clauses'];sibling=[]
    for ident,n in nodes.items():
        if ident!=node['id'] and n['parent']==node['parent']:
            same={x['text'].strip() for x in _spans(records[ident]['body'])}&{x['text'].strip() for x in clauses}
            if same:sibling.append({'id':ident,'exact_repeated_claims':sorted(same),'action':'Consider deduplication only after source-bound whole-claim review; never move across employer/project.'})
    return {'carrier_phrases':carriers,'clause_order_candidates':clauses if len(clauses)>1 else [],
        'clause_reorder_rule':'A local rewrite may reorder whole claims within the same bullet only if chronology, actor and limitation scope remain unchanged; use prose, not forced breaks.',
        'parallel_list_present':bool(re.search(r'[,，、]|\band\b',body)),
        'list_rule':'Share repeated verbs or framing across parallel items; retain every listed object and its count.',
        'same_entry_exact_duplicates':sibling,
        'merge_or_delete':{'automatic':False,'requires':'Explicit action-specific source review, same-entry scope for merging, retention of all claim limits and protected IDs. No operation is authorized by shortness alone.'}}

def build_tail_guidance(bundle, rendered, source):
    """Return JSON suitable for request.context.measured_tail_guidance.

    Raises ValueError on stale/incomplete evidence. Does not edit or call a model.
    """
    nodes=_validate_bundle(bundle)
    if bundle.get('source_sha256')!=_hash(source['material_text']) or bundle.get('jd_sha256')!=_hash(source['jd_text']):raise ValueError('tail_source_or_jd_mismatch')
    pdf,fresh,measured=_fresh_measurement(bundle,rendered);m0=rendered['measurement']
    style=rendered.get('style_fingerprint') or m0.get('style_fingerprint');typo=rendered.get('typography_fingerprint') or m0.get('typography_fingerprint')
    if not style or not typo:raise ValueError('tail_style_locks_missing')
    binding={'raw_version':bundle['raw_version'],'render_version':bundle['render_version'],'source_sha256':bundle['source_sha256'],'jd_sha256':bundle['jd_sha256'],'pdf_sha256':fresh['pdf_sha256'],'docx_sha256':fresh['docx_sha256'],'style_fingerprint':style,'typography_fingerprint':typo}
    bullets=[];feedback=[]
    for m in measured:
        ident=m['id'];node=nodes[ident];record=bundle['records'][ident];body=record['body'];profile=_glyph_profile(pdf,m['line_details']);protect=_protections(body,node,record)
        pages=sorted({x['page'] for x in m['line_details']});ratios=[(x['bbox'][2]-x['bbox'][0])/m['available_width_pt'] for x in m['line_details']]
        status='single_line_exempt' if m['physical_lines']==1 else 'cross_page_review' if len(pages)>1 else 'needs_rewrite' if m['ratio']<=.5 else 'passed'
        item={'id':ident,'label':record['label']+record['colon'],'source_refs':copy.deepcopy(record.get('source_refs',[])),'source_scope_review_required':True,'body':body,'body_sha256':_hash(body),'parent_entry_id':node['parent'],'status':status,
            'measurement':{k:copy.deepcopy(m[k]) for k in ('physical_lines','available_width_pt','width_pt','ratio','last_line','line_details')},
            'all_line_width_ratios':ratios,'pages':pages,'crosses_page_boundary':len(pages)>1,'glyph_profile':profile,
            'budget':_budgets(m,profile),'protections':protect,'opportunities':_opportunities(body,protect,node,nodes,bundle['records']),
            'semantic_support_certified':False,'changed_text_requires_new_pdf':True}
        bullets.append(item)
        if status in ('needs_rewrite','cross_page_review'):
            feedback.append({k:copy.deepcopy(item[k]) for k in ('id','label','body','body_sha256','parent_entry_id','status','measurement','all_line_width_ratios','pages','budget','protections','opportunities')})
    result={'protocol':PROTOCOL,'status':'ready','binding':binding,'bullets':bullets,'revision_feedback':feedback,
            'page_count':m0.get('pages'),'pagination_rule':'A cross-page bullet remains one bullet, never separate single-line exemptions. Use the full page-capacity review before a tail-only rewrite.',
            'summary':{'total_bullets':len(bullets),'short_tail_ids':[b['id'] for b in bullets if b['status']=='needs_rewrite'],'cross_page_ids':[b['id'] for b in bullets if b['crosses_page_boundary']],'single_line_exempt_ids':[b['id'] for b in bullets if b['status']=='single_line_exempt']},
            'rules':['Never add filler, invent facts, remove qualifiers, shrink typography/margins or the width denominator.','Do not force early line breaks or split a bullet into single-line exemptions.','Prefer natural, source-supported concise prose. Safe whole-unit merge/delete requires explicit evidence, not layout pressure.','Re-render every changed candidate and reassess every physical line, page count, factual scope and visible bold.'],
            'limitations':{'model_improvement_verified':False,'automatic_semantic_certification':False,'budgets_are_approximate':True,'source_review_required_for_any_rewrite':True,'not_layout_acceptance':True,'case_gold_used':False,'new_API_calls':0}}
    result['guidance_sha256']=_digest(result)
    return result

def validate_tail_revision(guidance,before_bundle,after_bundle,*,source,source_review=None,rerendered=None):
    """Conservative candidate preflight, not a substitute for source or PDF review.

    Source-review receipts are recorded, not trusted as semantic certification by
    this module. Removed or merged nodes always remain blocked for explicit review.
    """
    before=_validate_bundle(before_bundle);after=_validate_bundle(after_bundle)
    if guidance.get('guidance_sha256')!=_digest({k:v for k,v in guidance.items() if k!='guidance_sha256'}):raise ValueError('tail_guidance_evidence_changed')
    if after_bundle.get('source_sha256')!=_hash(source['material_text']) or after_bundle.get('jd_sha256')!=_hash(source['jd_text']):raise ValueError('tail_candidate_source_changed')
    if guidance.get('protocol')!=PROTOCOL or guidance['binding']['raw_version']!=before_bundle['raw_version'] or guidance['binding']['render_version']!=before_bundle['render_version']:raise ValueError('tail_guidance_wrong_base')
    if guidance['binding']['source_sha256']!=_hash(source['material_text']) or guidance['binding']['jd_sha256']!=_hash(source['jd_text']):raise ValueError('tail_revision_source_changed')
    failures=[];review=[];changed=[]
    for field in ('document_id','language','protected_ids'):
        if before_bundle['render_document'][field]!=after_bundle['render_document'][field]:failures.append({'code':'document_identity_or_protection_changed','field':field})
    oldnodes={n['id']:n for n in before_bundle['render_document']['nodes']};newnodes={n['id']:n for n in after_bundle['render_document']['nodes']}
    removed=set(oldnodes)-set(newnodes);added=set(newnodes)-set(oldnodes)
    if added:failures.append({'code':'new_stable_ids_or_split_requires_explicit_review','ids':sorted(added)})
    if removed:failures.append({'code':'whole_unit_delete_or_merge_requires_explicit_source_review','ids':sorted(removed)})
    protected=set(before_bundle['render_document'].get('protected_ids',[]))
    if removed&protected:failures.append({'code':'protected_unit_removed','ids':sorted(removed&protected)})
    diagnostics={b['id']:b for b in guidance['bullets']}
    for ident in oldnodes.keys()&newnodes.keys():
        a,b=oldnodes[ident],newnodes[ident]
        if any(a[k]!=b[k] for k in ('parent','purpose','kind')):failures.append({'code':'stable_unit_scope_changed','id':ident})
        if a['kind']!='sentence':
            if a['text']!=b['text']:failures.append({'code':'non_bullet_change_outside_tail_scope','id':ident})
            continue
        old,new=a['text'],b['text'];record_before=before_bundle['records'][ident];record_after=after_bundle['records'][ident]
        label_changed=(record_before['label'],record_before['colon'])!=(record_after['label'],record_after['colon'])
        if label_changed:review.append({'code':'changed_label_needs_source_review','id':ident})
        if old!=new or label_changed:changed.append(ident)
        if old==new:continue
        if '\n' in new or '\r' in new:failures.append({'code':'manual_break_not_semantic_rewrite','id':ident})
        qold=Counter(x.group().lower() for x in _NUM.finditer(old));qnew=Counter(x.group().lower() for x in _NUM.finditer(new))
        if qold!=qnew:failures.append({'code':'quantity_token_change_needs_explicit_source_review','id':ident,'removed':list((qold-qnew).elements()),'added':list((qnew-qold).elements())})
        lost_scope=Counter(x.group().lower() for x in _NEG.finditer(old))-Counter(x.group().lower() for x in _NEG.finditer(new))
        if lost_scope:failures.append({'code':'negation_or_scope_marker_removed_requires_source_review','id':ident,'removed':list(lost_scope.elements())})
        p=diagnostics[ident]['protections']
        for key in ('negative_scope_and_comparison_clauses','actor_responsibility_clauses'):
            missing=[x['text'] for x in p[key] if x['text'] not in new]
            if missing:review.append({'code':key+'_rewritten_verify_scope_and_actor','id':ident,'original_clauses':missing})
        review.append({'code':'complete_claim_semantics_require_source_review','id':ident})
    measured=None
    if rerendered is not None:
        measured=build_tail_guidance(after_bundle,rerendered,source)
        if measured['binding']['style_fingerprint']!=guidance['binding']['style_fingerprint'] or measured['binding']['typography_fingerprint']!=guidance['binding']['typography_fingerprint']:failures.append({'code':'style_or_typography_changed'})
        if changed and measured['binding']['pdf_sha256']==guidance['binding']['pdf_sha256']:failures.append({'code':'changed_text_reused_old_pdf'})
        oldb={x['id']:x for x in guidance['bullets']}
        for item in measured['bullets']:
            prev=oldb.get(item['id'])
            if prev and abs(prev['measurement']['available_width_pt']-item['measurement']['available_width_pt'])>1e-6:failures.append({'code':'body_width_denominator_changed','id':item['id']})
    return {'status':'blocked' if failures else 'needs_source_and_render_review' if changed or review else 'unchanged',
        'structural_pass':not failures,'changed_ids':sorted(changed),'blocking_findings':failures,'review_findings':review,
        'must_rerender':bool(changed) and measured is None,'fresh_render_bound':measured is not None,
        'remaining_short_tail_ids':measured['summary']['short_tail_ids'] if measured else None,
        'source_review_receipt_present':source_review is not None,'source_review_receipt_certified_by_this_module':False,
        'semantic_pass':False,'overall_acceptance':False,'no_automatic_edit':True}




