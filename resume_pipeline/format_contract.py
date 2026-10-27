"""Original-skill requirements and report checks, not a Word/PDF renderer.

A measurement report is untrusted input. Passing these checks proves only that
its fields satisfy the contract, never that a real artifact was visually checked.
"""
import math
from .core import digest

CONTRACT = {
    'version': 'original-skill-format-v1',
    'scope': 'Partial machine-check report contract, not complete source requirements',
    'word_export_gate_origin': 'Additional current-task constraint; sanitized source permits equivalent verified DOCX export tools',
    'languages': ['zh', 'en'],
    'separate_language_documents': True,
    'pages_per_language': 1,
    'paper': 'A4',
    'orientation': 'portrait',
    'blank_padding_allowed': False,
    'font_shrink_allowed': False,
    'paragraph_last_line_ratio_exclusive_minimum': 0.50,
    'paragraph_last_line_preferred_range': [0.67, 0.80],
    'zh_heading_lines': 'double',
    'en_heading_lines': 'lower_only',
    'dates_bold': True,
    'zh_graduation_label_and_value_bold': True,
    'autoSpaceDE': True,
    'autoSpaceDN': True,
    'doNotCompress_punctuation': True,
    'bullet_alignment_verified': True,
    'final_pdf_export_engine': 'Microsoft Word',
    'pdf_selectable_text': True,
}


def assess_format_report(report):
    """Validate completeness/consistency of supplied measurements; fail closed.

    Required measurements are artifact-specific, not inferred from Markdown.
    A trusted Word/PDF inspector must independently produce and verify evidence.
    """
    failures, missing, warnings = [], [], []
    if not isinstance(report, dict):
        raise ValueError('report must be an object')
    checks = {
        'separate_language_documents': True, 'page_count': 1,
        'paper': 'A4', 'orientation': 'portrait', 'blank_padding_used': False,
        'font_shrink_used': False, 'dates_bold': True,
        'autoSpaceDE': True, 'autoSpaceDN': True,
        'doNotCompress_punctuation': True, 'bullet_alignment_verified': True,
        'pdf_export_engine': 'Microsoft Word', 'pdf_selectable_text': True,
    }
    language = report.get('language')
    if language not in CONTRACT['languages']:
        failures.append('language must be zh or en')
    checks['heading_lines'] = 'double' if language == 'zh' else 'lower_only'
    if language == 'zh':
        checks['graduation_label_and_value_bold'] = True
    for key, expected in checks.items():
        if key not in report:
            missing.append(key)
        elif type(report[key]) is not type(expected) or report[key] != expected:
            failures.append(key)
    ratios = report.get('paragraph_last_line_ratios')
    if not isinstance(ratios, list) or not ratios:
        missing.append('paragraph_last_line_ratios')
    else:
        for i, ratio in enumerate(ratios):
            if type(ratio) not in (int, float) or not math.isfinite(ratio) or not 0.5 < ratio <= 1:
                failures.append('paragraph_last_line_ratios[%s]' % i)
            elif not .67 <= ratio <= .80:
                warnings.append('paragraph %s outside preferred 67–80%% last-line width' % i)
    # Evidence identity is necessary but cannot prove a report is truthful.
    for key in ('docx_sha256', 'pdf_sha256', 'render_evidence_sha256', 'extractor_version', 'word_version'):
        value = report.get(key)
        if not isinstance(value, str) or not value:
            missing.append(key)
        elif key.endswith('sha256') and (len(value) != 64 or any(c not in '0123456789abcdef' for c in value)):
            failures.append(key)
    status = 'fail' if failures else 'not_assessed' if missing else 'reported_pass'
    return {'status': status, 'failures': failures, 'missing_evidence': missing,
            'warnings': warnings, 'contract_hash': digest(CONTRACT),
            'actual_style_verified': False, 'export_ready': False,
            'notice': 'Self-reported evidence checked for consistency only; independent artifact inspection still required.'}
