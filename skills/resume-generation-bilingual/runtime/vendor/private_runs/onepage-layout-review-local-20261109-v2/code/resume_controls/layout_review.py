"""Independent physical presentation gates; a single page is not completion."""
from math import isfinite
from . import document as d
from .common import text_hash


def number(value):
    return type(value) in (int, float) and isfinite(value)


def evaluate(doc, rendered):
    m = rendered['measurement']
    expected = {n['id']: n for n in doc['nodes'] if n['kind'] == 'sentence'}
    pdf_hash = rendered.get('pdf_sha256')
    requirements = rendered.get('presentation_requirements', {'tail_lines': True, 'visible_bold': False})
    failures, preferences, assessed = [], [], []
    def fail(code, ident=None, action='Inspect the measured layout before revising; never add facts or remove claim limits to fill a line.'):
        failures.append({'route': 'layout_review', 'code': code, 'id': ident, 'closed': False,
                         'blocks_current_draft': True, 'action': action})
    tail = m.get('tail_line_review', {})
    if requirements.get('tail_lines', True):
        entries = tail.get('bullets', [])
        ids = [b.get('id') for b in entries if isinstance(b, dict)]
        if (not tail.get('mapping_complete') or tail.get('pdf_sha256') != pdf_hash or not pdf_hash
                or len(ids) != len(entries) or len(set(ids)) != len(ids) or set(ids) != set(expected)):
            fail('tail_line_measurement_missing_stale_or_incomplete')
        else:
            for b in entries:
                ident, node = b['id'], expected[b['id']]
                width, available, count = b.get('width_pt'), b.get('available_width_pt'), b.get('physical_lines')
                if (b.get('source_text_sha256') != text_hash(node['text']) or type(count) is not int or count < 1
                        or not number(width) or width < 0 or not number(available) or available <= 0
                        or not b.get('last_line')):
                    fail('tail_line_measurement_invalid_or_wrong_text', ident); continue
                ratio = width/available
                if not number(b.get('ratio')) or abs(b['ratio']-ratio) > .00001:
                    fail('tail_line_ratio_not_bound_to_measured_width', ident); continue
                status = 'single_line_exempt' if count == 1 else 'passed' if ratio > .5 else 'needs_rewrite'
                assessed.append({'id': ident, 'physical_lines': count, 'last_line': b['last_line'],
                                 'width_pt': width, 'available_width_pt': available, 'ratio': ratio, 'status': status})
                if status == 'needs_rewrite':
                    fail('multi_line_tail_not_over_half', ident,
                         'Rewrite this complete bullet using only source-supported wording, preserving all claim boundaries; re-render. Do not pad short single-line bullets or alter typography.')
                elif count > 1 and not 2/3 <= ratio <= .8:
                    preferences.append({'id': ident, 'code': 'tail_outside_preferred_two_thirds_to_four_fifths',
                                        'ratio': ratio, 'blocking': False, 'do_not_pad_or_remove_limits': True})
    bold = m.get('visual_bold', {})
    if requirements.get('visible_bold'):
        expected_labels = set(rendered.get('label_expected_ids', expected))
        expected_text = rendered.get('label_expected_text', {})
        entries = bold.get('labels', [])
        ids = [b.get('id') for b in entries if isinstance(b, dict)]
        mode = bold.get('evidence_kind', 'pixel_ab' if 'pixel' in str(bold.get('method', '')).lower() else None)
        if (bold.get('status') != 'passed' or bold.get('pdf_sha256') != pdf_hash or not pdf_hash
                or not bold.get('evidence_path') or mode not in {'pixel_ab', 'embedded_bold_with_visual_inspection'}
                or bold.get('artifact_verified') is not True or not bold.get('evidence_sha256')
                or len(ids) != len(entries) or len(set(ids)) != len(ids) or set(ids) != expected_labels
                or set(expected_text) != expected_labels
                or bold.get('checked_labels') != len(expected_labels)):
            fail('visible_bold_missing_failed_or_unverified', action='Verify each label and colon on the actual PDF with same-text pixel evidence; Word w:b or font flags alone are insufficient.')
        else:
            for b in entries:
                regular, actual = b.get('regular_ink'), b.get('bold_ink')
                pixel_ok = (mode == 'pixel_ab' and b.get('unchanged_glyph_positions') is True
                            and b.get('pixel_artifact_verified') is True
                            and number(regular) and regular > 0 and number(actual) and actual > regular)
                native_ok = (mode == 'embedded_bold_with_visual_inspection' and b.get('embedded_bold_face') is True
                             and len(str(b.get('embedded_font_sha256', ''))) == 64
                             and b.get('visual_artifact_verified') is True)
                if b.get('visibly_bold') is not True or b.get('text') != expected_text.get(b['id']) or not (pixel_ok or native_ok):
                    fail('label_visible_bold_not_demonstrated', b['id'],
                         'Inspect same-text pixel comparison for label and colon, keeping the approved font, glyph positions and dimensions unchanged.')
    codes = {f['code'] for f in failures}
    return {'status': 'needs_layout_review' if failures else 'passed', 'blocking_findings': failures,
            'preferences': preferences, 'bullet_tails': assessed, 'threshold': .5,
            'comparison': 'strictly_greater', 'preferred_range': [2/3, .8],
            'content_rewrite_possible': bool(codes) and codes == {'multi_line_tail_not_over_half'},
            'bold_visibility_status': bold.get('status', 'not_required' if not requirements.get('visible_bold') else 'unverified'),
            'not_a_source_factual_pass': True}
