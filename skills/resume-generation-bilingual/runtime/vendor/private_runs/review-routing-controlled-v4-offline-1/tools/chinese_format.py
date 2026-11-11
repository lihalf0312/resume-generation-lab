from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zipfile
from docx import Document
from docx.shared import Pt, Twips, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def node(parent, name, **a):
    n = OxmlElement('w:' + name)
    for (k, v) in a.items():
        n.set(qn('w:' + k), str(v))
    parent.append(n)
    return n

def run(p, text, size=None, bold=False, lang='en', color='000000'):
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(size or (12 if lang == 'zh' else 10.5))
    r.font.bold = bold
    r.font.color.rgb = RGBColor.from_string(color)
    rp = r._element.get_or_add_rPr()
    rf = rp.rFonts
    rf.set(qn('w:ascii'), 'Times New Roman')
    rf.set(qn('w:hAnsi'), 'Times New Roman')
    rf.set(qn('w:cs'), 'Times New Roman')
    rf.set(qn('w:eastAsia'), '楷体' if lang == 'zh' else 'Times New Roman')
    return r

def para(doc, text='', kind='body', lang='en', date=None, label=None):
    p = doc.add_paragraph()
    pp = p._p.get_or_add_pPr()
    pf = p.paragraph_format
    node(pp, 'autoSpaceDE', val=1)
    node(pp, 'autoSpaceDN', val=1)
    if kind == 'name':
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf.keep_with_next = True
        run(p, text, 18, lang == 'en', lang)
    elif kind in ['contact', 'marker']:
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf.keep_with_next = True
        run(p, text, 8 if kind == 'marker' else None, False, lang, '555555' if kind == 'marker' else '000000')
    elif kind == 'section':
        pf.keep_with_next = True
        borders = node(pp, 'pBdr')
        if lang == 'zh':
            node(borders, 'top', val='single', sz=4, space=1, color='000000')
        node(borders, 'bottom', val='single', sz=4 if lang == 'zh' else 6, space=1, color='000000')
        run(p, text, 14 if lang == 'zh' else 12, True, lang)
    elif kind == 'entry':
        pf.keep_with_next = True
        pf.tab_stops.add_tab_stop(Twips(10772 if lang == 'zh' else 9638), WD_TAB_ALIGNMENT.RIGHT)
        run(p, text, None, True, lang)
        if date:
            run(p, '\t' + date, None, True, lang)
    elif kind == 'bullet':
        if lang == 'en':
            np = node(pp, 'numPr')
            node(np, 'ilvl', val=0)
            node(np, 'numId', val=1)
            pf.left_indent = Twips(720)
            pf.first_line_indent = Twips(-442)
        else:
            run(p, '• ', None, False, lang)
        if label:
            run(p, label + ' ', None, True, lang)
        run(p, text, None, False, lang)
        pf.keep_together = True
    elif kind == 'gap':
        run(p, '', None, False, lang)
    else:
        run(p, text, None, False, lang)
    return p
