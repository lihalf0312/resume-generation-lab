"""Read-only PDF glyph-to-row mapping for measured bullet tail widths.

Every visible non-marker character is consumed in document order. Normalization
preserves Latin word boundaries and authored Han/Han spaces, using the existing
controlled renderer's CJK-line-break and DE/DN-spacing rules. No content editing.
"""
from pathlib import Path
import re
from statistics import median
from .common import file_hash, text_hash

CJK = r'[\u3400-\u9fff\u3000-\u303f\uff01-\uff65]'
MARKERS = {'•', '?', '\uf09f'}


def canonical_indexed(chars):
    """Return canonical characters plus their original PDF character indices."""
    units = list(chars)
    def substitute(pattern, replace):
        nonlocal units
        text = ''.join(c for c, _ in units)
        result, cursor = [], 0
        for match in re.finditer(pattern, text):
            result += units[cursor:match.start()]
            result += replace(match, units)
            cursor = match.end()
        result += units[cursor:]
        units = result
    substitute('(' + CJK + ')\n(?=' + CJK + ')', lambda m, u: [u[m.start()]])
    substitute(r'[ \t\r\n]+', lambda m, u: [(' ', u[m.start()][1])])
    while units and units[0][0] == ' ': units.pop(0)
    while units and units[-1][0] == ' ': units.pop()
    substitute('(' + CJK + ') *(?=[A-Za-z0-9])', lambda m, u: [u[m.start()], (' ', None)])
    substitute('([A-Za-z0-9]) *(?=' + CJK + ')', lambda m, u: [u[m.start()], (' ', None)])
    return ''.join(c for c, _ in units), [i for _, i in units]


def _canonical(text):
    return canonical_indexed([(c, None) for c in text])[0]


def _find(needle, hay, start):
    at = hay.find(needle, start)
    if at >= 0:
        return at, at + len(needle), []
    # Same explicit quote/currency edges as the existing Chinese mapper. Add only
    # literal hyphen line-wrap joins, retaining the actual hyphen and all letters.
    parts, adaptations = [], []
    for i, c in enumerate(needle):
        parts.append(re.escape(c))
        if i + 1 < len(needle) and (
            c in '-–—' or (c in '“”' and re.fullmatch(CJK, needle[i+1]))
            or (re.fullmatch(CJK, c) and needle[i+1] in '￥$')):
            parts.append(' ?')
            adaptations.append({'source_index': i, 'edge': needle[i:i+2]})
    match = re.compile(''.join(parts)).search(hay, start)
    return (match.start(), match.end(), adaptations) if match else (-1, -1, [])


def _only_markers_or_space(gap):
    return all(token in MARKERS for token in gap.split())


def _indent(paragraph, name):
    value = getattr(paragraph.paragraph_format, name)
    style = paragraph.style
    seen = set()
    while value is None and style is not None and style.style_id not in seen:
        seen.add(style.style_id)
        value = getattr(style.paragraph_format, name)
        style = style.base_style
    return value.pt if value is not None else 0.0


def measure_tail_lines(pdf_path, docx_path, rows):
    import pymupdf as fitz
    from docx import Document
    pdf_path, docx_path = Path(pdf_path), Path(docx_path)
    word = Document(docx_path)
    if len(word.sections) != 1 or len(word.paragraphs) != len(rows):
        raise ValueError('one_section_and_exact_physical_row_paragraph_alignment_required')
    section = word.sections[0]
    raw, glyphs = [], []
    with fitz.open(pdf_path) as pdf:
        for pi, page in enumerate(pdf):
            for block in page.get_text('rawdict', sort=False)['blocks']:
                if block.get('type') != 0: continue
                for li, line in enumerate(block['lines']):
                    for span in line['spans']:
                        for char in span['chars']:
                            glyph = {'text': char['c'], 'bbox': list(char['bbox']), 'origin': list(char['origin']),
                                     'page': pi+1, 'font': span['font'], 'size': span['size'],
                                     'block': block['number'], 'line': li}
                            raw.append((char['c'], len(glyphs)))
                            glyphs.append(glyph)
                    raw.append(('\n', None))
    hay, indices = canonical_indexed(raw)
    cursor, bullets, errors, adaptations = 0, [], [], []
    for row, paragraph in zip(rows, word.paragraphs):
        # Confirm the renderer did not attach a positional row to another paragraph.
        expected = (row.get('label', '') + ' ' if row.get('label') else '') + row['text']
        if row.get('date'): expected += '\t' + row['date']
        actual_para = paragraph.text
        if row['kind'] == 'bullet' and actual_para[:1] in MARKERS:
            actual_para = actual_para[1:].lstrip()
        if _canonical(actual_para) != _canonical(expected):
            errors.append({'id': row['id'], 'code': 'docx_row_binding_mismatch'}); break
        needle = _canonical(expected)
        if not needle: continue
        at, end, changes = _find(needle, hay, cursor)
        if at < 0 or not _only_markers_or_space(hay[cursor:at]):
            errors.append({'id': row['id'], 'code': 'ordered_pdf_row_mapping_failed',
                           'expected': needle, 'next_pdf_text': hay[cursor:cursor+len(needle)+50]}); break
        consumed = [glyphs[i] for i in indices[at:end] if i is not None and not glyphs[i]['text'].isspace()]
        if changes: adaptations.append({'id': row['id'], 'source_verified_spacing_edges': changes})
        cursor = end
        if row['kind'] != 'bullet': continue
        # Baseline grouping, not PDF block grouping: labels may be separate runs.
        lines = []
        for glyph in consumed:
            if not lines or glyph['page'] != lines[-1][0]['page'] or abs(glyph['origin'][1] - median(g['origin'][1] for g in lines[-1])) > .8:
                lines.append([])
            lines[-1].append(glyph)
        left = section.left_margin.pt + _indent(paragraph, 'left_indent')
        right = section.page_width.pt - section.right_margin.pt - _indent(paragraph, 'right_indent')
        available = right - left
        if not lines or available <= 0:
            errors.append({'id': row['id'], 'code': 'physical_lines_or_body_width_unknown'}); break
        last = lines[-1]
        x0, x1 = min(g['bbox'][0] for g in last), max(g['bbox'][2] for g in last)
        width, count = x1-x0, len(lines)
        ratio = width/available
        status = 'single_line_exempt' if count == 1 else 'passed' if ratio > .5 else 'needs_rewrite'
        # Rebuild visible line text including authored/extracted spaces from raw glyph order.
        def line_text(line):
            positions = [i for i,g in enumerate(glyphs) if g is line[0] or g is line[-1]]
            return ''.join(g['text'] for g in glyphs[min(positions):max(positions)+1]).strip()
        source_text = row.get('break_source_text', row['text'])
        if 'break_source_text' in row and source_text not in {''.join(row['text'].split('\n')), ' '.join(row['text'].split('\n'))}:
            errors.append({'id': row['id'], 'code': 'manual_break_changes_source_text'}); break
        bullets.append({'id': row['id'], 'source_text_sha256': text_hash(source_text),
            'rendered_text_sha256': text_hash(row['text']), 'layout_only_manual_linebreaks': 'break_source_text' in row,
            'physical_lines': count, 'last_line': line_text(last), 'width_pt': round(width, 6),
            'available_width_pt': round(available, 6), 'body_left_pt': left, 'body_right_pt': right,
            'ratio': ratio, 'status': status, 'preferred_range_met': count > 1 and 2/3 <= ratio <= .8,
            'line_details': [{'page': line[0]['page'], 'baseline_pt': median(g['origin'][1] for g in line),
                              'text': line_text(line), 'bbox': [min(g['bbox'][0] for g in line), min(g['bbox'][1] for g in line),
                                      max(g['bbox'][2] for g in line), max(g['bbox'][3] for g in line)]} for line in lines]})
    if not errors and not _only_markers_or_space(hay[cursor:]):
        errors.append({'code': 'unconsumed_pdf_text', 'text': hay[cursor:]})
    expected_ids = [r['id'] for r in rows if r['kind'] == 'bullet']
    complete = not errors and [b['id'] for b in bullets] == expected_ids
    return {'status': 'unverified' if not complete else 'failed' if any(b['status'] == 'needs_rewrite' for b in bullets) else 'passed',
        'threshold': .5, 'comparison': 'strictly_greater', 'preferred_range': [2/3, .8],
        'short_single_line_bullets': 'exempt_do_not_pad', 'bullets': bullets, 'errors': errors,
        'mapping_complete': complete, 'pdf_sha256': file_hash(pdf_path), 'docx_sha256': file_hash(docx_path),
        'spacing_adaptations': adaptations,
        'method': 'Ordered rawdict glyph coverage; baseline-grouped physical lines; last non-whitespace glyph bbox union width / actual DOCX continuation-line body width. No estimated string widths or content resync.',
        'not_a_source_factual_pass': True}
