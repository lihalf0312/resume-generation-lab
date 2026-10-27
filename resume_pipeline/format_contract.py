"""Configurable report consistency checks, never proof of rendered compliance."""
import math
from .core import digest
from .preferences import validate_preferences


def build_contract(preferences, language):
    validate_preferences(preferences)
    if language not in ('zh-CN','en'):raise ValueError('unsupported language')
    selected=preferences['output_languages']
    if selected is not None and language not in selected:raise ValueError('language excluded by resolved preferences')
    layout=preferences['layout']
    template=preferences['template_paths'].get(language)
    return {'version':'configurable-format-v2','language':language,
            'preferences':preferences,'preferences_hash':digest(preferences),
            'layout_mode':'template_requested_unverified' if template else 'generic_single_column_unrendered',
            'template_fidelity_verified':False,
            'scope':'Partial measurement-report checks; source workflow and actual artifact QA still required.',
            'export_engine_policy':'Any compatible DOCX-to-PDF engine with actual recorded checks; no Word-only default',
            'word_specific_properties_verified':False}


def assess_format_report(report, contract):
    if not isinstance(report,dict):raise ValueError('report must be an object')
    p=contract['preferences'];validate_preferences(p);l=p['layout']
    failures,missing,warnings=[],[],[]
    checks={'language':contract['language'],'page_count':l['target_pages'],'paper':l['page_size'],
            'blank_padding_used':False,'unauthorized_font_shrink_used':False,
            'dates_bold':l['dates_bold'],'graduation_label_and_value_bold':l['graduation_label_and_date_bold'],
            'bullet_alignment_verified':True,'same_final_docx_content':True,
            'body_area_checked':True,'clipping_or_hidden_content':False,'all_final_pages_rendered':True}
    rule=l['section_rules'].get(contract['language'],'follow_template')
    if rule=='follow_template':checks['template_heading_rules_preserved']=True
    else:checks['heading_lines']=rule
    spacing=l['numeric_and_latin_auto_spacing']
    if spacing=='follow_template':
        checks['template_spacing_preserved' if contract['layout_mode'].startswith('template_') else 'generic_spacing_parameters_recorded']=True
    else:
        checks.update(autoSpaceDE=spacing=='enabled',autoSpaceDN=spacing=='enabled')
    compression=l['punctuation_compression']
    if compression=='doNotCompress':checks['doNotCompress_punctuation']=True
    elif compression=='when_visual_issue':
        if type(report.get('punctuation_compression_issue_detected')) is not bool:missing.append('punctuation_compression_issue_detected')
        elif report['punctuation_compression_issue_detected']:checks['doNotCompress_punctuation']=True
    else:checks['template_compression_preserved']=True
    if 'pdf' in p['formats']:
        checks.update(pdf_selectable_text=True,docx_to_pdf_compatible=True)
        if not isinstance(report.get('pdf_export_engine'),str) or not report['pdf_export_engine'].strip():missing.append('pdf_export_engine')
    for k,expected in checks.items():
        if k not in report:missing.append(k)
        elif type(report[k]) is not type(expected) or report[k]!=expected:failures.append(k)
    ratios=report.get('paragraph_last_line_ratios')
    if not isinstance(ratios,list) or not ratios:missing.append('paragraph_last_line_ratios')
    else:
        low=l['body_last_line_min_ratio'];exclusive=l['body_last_line_min_exclusive'];a,b=l['body_last_line_preferred_ratio']
        for i,x in enumerate(ratios):
            if type(x) not in (int,float) or not math.isfinite(x) or x>1 or (x<=low if exclusive else x<low):failures.append('paragraph_last_line_ratios[%s]'%i)
            elif not a<=x<=b:warnings.append('paragraph %s outside preferred band'%i)
    evidence=['docx_sha256','render_evidence_sha256','renderer_version']+(['pdf_sha256','extractor_version'] if 'pdf' in p['formats'] else [])
    for k in evidence:
        v=report.get(k)
        if not isinstance(v,str) or not v:missing.append(k)
        elif k.endswith('sha256') and (len(v)!=64 or any(c not in '0123456789abcdef' for c in v)):failures.append(k)
    return {'status':'fail' if failures else 'not_assessed' if missing else 'reported_pass',
            'failures':failures,'missing_evidence':missing,'warnings':warnings,
            'contract_hash':digest(contract),'actual_style_verified':False,
            'word_specific_properties_verified':False,'export_ready':False,
            'notice':'Report consistency only; engine identity and self-reported flags do not prove actual artifact compliance.'}
