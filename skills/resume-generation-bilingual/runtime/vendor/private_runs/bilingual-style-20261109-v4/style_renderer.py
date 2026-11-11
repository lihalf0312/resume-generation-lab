"""Private fixed-template style candidate. No API calls; no frozen file writes.
String bullets stay valid. Presentation labels carry explicit source evidence.
Rendered typography and new presentation rules have separate fingerprints.
"""
from pathlib import Path
import copy, hashlib, json, re, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'private_runs/review-routing-controlled-v4-offline-1'
sys.path[:0] = [str(BASE / 'tools')]
import render_offline as engine
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
R_LOCAL = Path(__file__).resolve().parent
STYLE_VERSION = 'bilingual-zh-label-alignment-v5'
DEFAULT_STYLE_OPTIONS = {'english_projects_heading': 'Project Experience', 'english_project_title_order': 'name_first', 'chinese_bullet_alignment': 'left'}
def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()
def save(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')
def typography_fingerprint():
    files = [BASE/'english-runtime/scripts/style_core.py', BASE/'tools/chinese_format.py',
             BASE/'templates/resume-template-zh.docx', BASE/'templates/confirmed-chinese-separators.docx',
             BASE/'english-runtime/assets/blank-english-template.docx']
    return digest({str(p.relative_to(BASE)): engine.sha(p) for p in files})
def style_fingerprint():
    return digest({'version': STYLE_VERSION, 'module': engine.sha(__file__), 'pdf_bold_module': engine.sha(R_LOCAL/'pdf_label_bold.py'),
                   'typography': typography_fingerprint()})
def project_heading_defaults(rows, lang, presentation):
    """Reusable presentation-only English project defaults; exact source binding required.
    Override heading with a string (or None to retain source) and order with 'source'.
    No project identity or affiliation is inferred from an ambiguous string.
    """
    if lang != 'en': return rows, []
    options = {**DEFAULT_STYLE_OPTIONS, **presentation.get('style_options', {})}
    title = options['english_projects_heading']; order = options['english_project_title_order']
    if title is not None and (not isinstance(title,str) or not title.strip()):
        raise ValueError('English projects heading must be a nonempty string or None')
    if order not in ('name_first','source'): raise ValueError('Unsupported project title order')
    changes=[]
    for row in rows:
        if row.get('section_purpose') != 'projects': continue
        before=row['text']
        if row['kind']=='section' and title is not None: row['text']=title
        elif row['kind']=='entry' and order=='name_first':
            primary=row.get('entry_emphasis',{}).get('text')
            if not primary: raise ValueError('Name-first project title requires source-bound entry_primary: '+row['id'])
            if not row['text'].startswith(primary):
                parts=re.split(r'\s*[|｜]\s*',row['text'])
                if parts.count(primary)!=1: raise ValueError('Project name must be a complete semantic heading component: '+row['id'])
                row['text']=' | '.join([primary]+[part for part in parts if part!=primary])
        if row['text']!=before:
            row['source_heading']=before
            changes.append({'id':row['id'],'before':before,'after':row['text'],'rule':'English project section name and source-bound primary-name-first defaults; affiliations preserved'})
    return rows, changes

def rows_from_candidate(candidate, lang, presentation=None):
    presentation = presentation or {}
    labels = presentation.get('bullet_labels', {})
    rows = []
    for s, section in enumerate(candidate['resume']['sections']):
        rows.append({'id':f's{s}', 'kind':'section', 'text':section['heading'], 'section_purpose':section.get('purpose')})
        for e, item in enumerate(section['items']):
            eid = f's{s}.e{e}'
            rows.append({'id':eid, 'kind':'entry', 'text':item['heading'], 'date':item.get('date',''), 'section_purpose':section.get('purpose')})
            for b, text in enumerate(item.get('bullets', [])):
                rid = f'{eid}.b{b}'; row = {'id':rid, 'kind':'bullet', 'text':text}
                label = labels.get(rid)
                if label:
                    if not isinstance(label, dict) or label.get('source_text') != text:
                        raise ValueError('Label must be rebound explicitly to exact current bullet: '+rid)
                    if not label.get('source_facts'):
                        raise ValueError('Evidence required for label: '+rid)
                    value = label['text'].strip()
                    if not value or re.search(r'[:：\n*]', value):
                        raise ValueError('Label must be plain short phrase without punctuation markup: '+rid)
                    row['label'] = value + ('：' if lang == 'zh' else ':')
                    row['label_source'] = copy.deepcopy(label)
                breaking = presentation.get('bullet_breaks', {}).get(rid)
                if breaking:
                    if breaking['source_text'] != text:
                        raise ValueError('Stale explicit break source: '+rid)
                    segments = breaking['segments']
                    joined = (' ' if lang=='en' else '').join(segments)
                    if joined != text: raise ValueError('Breaks must preserve exact words and punctuation: '+rid)
                    row['text'] = '\n'.join(segments)
                    row['break_source_text'] = text
                rows.append(row)
    for row in rows:
        if row['kind']!='entry': continue
        rule=presentation.get('entry_primary',{}).get(row['id'])
        if rule is not None:
            if rule.get('source_text')!=row['text'] or row['text'].count(rule.get('text',''))!=1:
                raise ValueError('Entry emphasis must bind one exact source substring: '+row['id'])
            row['entry_emphasis']=rule
    unknown = set(labels) - {x['id'] for x in rows if x['kind']=='bullet'}
    if unknown: raise ValueError('Stale label ids: '+repr(sorted(unknown)))
    rows, normalizations = project_heading_defaults(rows, lang, presentation)
    return {'presentation_normalizations':normalizations, 'name':candidate['resume']['name'], 'target_role': '运营分析专员' if lang=='zh' else 'Operations Analysis Specialist', 'rows':rows}
def semantic_splits(text):
    # Split after complete semantic delimiters, preserving all visible characters.
    positions = [m.end() for m in re.finditer(r'[,，|｜;；]', text)]
    return [(text[:i].rstrip(), text[i:].lstrip()) for i in positions if text[:i].strip() and text[i:].strip()]
def choose_heading_lines(text, lang, explicit=None):
    width = 538.6 if lang=='zh' else engine.onepage.WIDTH
    if explicit is not None:
        if len(explicit)!=2 or re.sub(r'\s+', '', ''.join(explicit)) != re.sub(r'\s+', '', text):
            raise ValueError('Heading break must preserve all non-whitespace characters')
        options = [tuple(explicit)]
    elif engine.text_width(text,lang) <= width:
        return [text]
    else:
        options = semantic_splits(text)
    good = []
    for a,b in options:
        wa,wb = engine.text_width(a,lang), engine.text_width(b,lang)
        if max(wa,wb)<=width and min(wa,wb)>=width*.15:
            good.append((abs(wa-wb),a,b))
    if not good:
        if explicit is not None: raise ValueError('Explicit heading lines exceed fixed width or leave a short tail')
        return [text]  # Need measured/manual review, never arbitrary character slicing.
    _,a,b = min(good)
    return [a,b]
def structure(rows, lang, presentation=None):
    presentation = presentation or {}
    width = 538.6 if lang=='zh' else engine.onepage.WIDTH
    edited = copy.deepcopy(rows); output=[]; logs=[]
    # Keep legacy normalization while preserving separately bound headings and bullet labels.
    for row in edited:
        if row['kind']=='entry': row['_original_date']=row.get('date',''); row['date']=''
    normalized, oldlogs = engine.structure(edited,lang,fold_functional_headings=False)
    logs += oldlogs
    for row in normalized:
        if row['kind']!='entry': output.append(row); continue
        date=row.pop('_original_date','')
        if lang=='en': date=engine.onepage.short_dates(date)
        before=copy.deepcopy(row); before['date']=date
        lines=choose_heading_lines(row['text'],lang,presentation.get('heading_breaks',{}).get(row['id']))
        if len(lines)==2:
            for n,line in enumerate(lines):
                new=copy.deepcopy(row);new.update(id=row['id']+f'#title{n+1}',text=line,date='',source_id=row['id'])
                if n==1 and date and engine.text_width(line,lang)+engine.text_width(date,lang)+(36 if lang=='zh' else 12)<=width:
                    new['date']=date;date=''
                output.append(new)
            logs.append({'id':row['id'],'rule':'semantic balanced heading at fixed font width; final-line date right tab when it fits','before':before,'after':copy.deepcopy(output[-2:]),'measured_font_widths_pt':[engine.text_width(x,lang) for x in lines]})
        elif date and engine.text_width(row['text'],lang)+engine.text_width(date,lang)+(36 if lang=='zh' else 12)<=width:
            row['date']=date;date='';output.append(row)
        else: output.append(row)
        if date:
            d=copy.deepcopy(row);d.update(id=row['id']+'#date',text=date,date='',right_aligned=True,source_id=row['id']);output.append(d)
    return output, logs
def apply_chinese_bullet_alignment(paragraph, row, lang, presentation=None):
    """Keep inline lead-ins at natural glyph spacing instead of stretching them.
    Paragraph indents, width, font, font size and line spacing remain unchanged.
    A four-Han label now has the same colon position on a full or short line.
    Different natural label lengths remain different; no spaces are inserted.
    """
    if lang != 'zh' or row['kind'] != 'bullet': return
    option = (presentation or {}).get('style_options', {}).get('chinese_bullet_alignment',
                DEFAULT_STYLE_OPTIONS['chinese_bullet_alignment'])
    if option not in ('left', 'template'): raise ValueError('Unsupported Chinese bullet alignment')
    if option == 'left': paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT

def measure_chinese_label_alignment(pdf_path, docx_path, rows):
    """Pixel-position diagnostic, separate from strict document text/tail checks.
    Inspects actual glyph origins and inherited paragraph indents. Equal natural
    label advances are compared, never variable-length phrases as a fake column.
    """
    import pymupdf as fitz
    from statistics import median
    def flat(text): return ''.join(c for c in text if not c.isspace())
    def indent(p, name):
        value=getattr(p.paragraph_format,name); style=p.style; seen=set()
        while value is None and style is not None and style.style_id not in seen:
            seen.add(style.style_id); value=getattr(style.paragraph_format,name); style=style.base_style
        return value.pt if value is not None else 0.0
    pdf=fitz.open(pdf_path); word=Document(docx_path); glyphs=[]
    for pi,page in enumerate(pdf):
        for block in page.get_text('rawdict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    for c in span['chars']:
                        if not c['c'].isspace(): glyphs.append({**c,'font':span['font'],'size':span['size'],'page':pi+1})
    hay=''.join(x['c'] for x in glyphs); cursor=0; output=[]; findings=[]
    if len(rows)!=len(word.paragraphs): raise ValueError('Exact row/paragraph correspondence required')
    for row,p in zip(rows,word.paragraphs):
        text=(row.get('label','')+' ' if row.get('label') else '')+row['text']+(row.get('date',''))
        needle=flat(text); at=hay.find(needle,cursor)
        if at<0:
            findings.append({'id':row['id'],'code':'alignment_row_not_located'});break
        cursor=at+len(needle)
        if row['kind']!='bullet' or not row.get('label'): continue
        lead=glyphs[at:at+len(flat(row['label']))];body=glyphs[at+len(lead):cursor]
        if not lead or not body:findings.append({'id':row['id'],'code':'label_or_body_missing'});continue
        if len({(g['page'],round(g['origin'][1],1)) for g in lead})!=1:
            findings.append({'id':row['id'],'code':'label_wrapped'});continue
        x=lead[0]['origin'][0];colon=lead[-1]['origin'][0]
        left=word.sections[0].left_margin.pt+indent(p,'left_indent')
        width=word.sections[0].page_width.pt-word.sections[0].right_margin.pt-indent(p,'right_indent')-left
        output.append({'id':row['id'],'label':row['label'],'page':lead[0]['page'],
            'label_start_x_pt':x,'colon_start_x_pt':colon,'body_start_x_pt':body[0]['origin'][0],
            'natural_label_advance_pt':round(engine.text_width(row['label'][:-1],'zh'),4),
            'label_glyph_origins':[[g['c'],g['origin'][0]] for g in lead],
            'body_available_width_pt':width,'left_indent_pt':indent(p,'left_indent'),
            'first_line_indent_pt':indent(p,'first_line_indent'),'right_indent_pt':indent(p,'right_indent'),
            'explicit_left_aligned':p.alignment==WD_ALIGN_PARAGRAPH.LEFT})
    groups={}
    for row in output: groups.setdefault(row['natural_label_advance_pt'],[]).append(row)
    comparisons=[]
    for advance,group in groups.items():
        start_range=max(x['label_start_x_pt'] for x in group)-min(x['label_start_x_pt'] for x in group)
        colon_range=max(x['colon_start_x_pt'] for x in group)-min(x['colon_start_x_pt'] for x in group)
        comparisons.append({'natural_label_advance_pt':advance,'ids':[x['id'] for x in group],
            'label_start_range_pt':start_range,'colon_start_range_pt':colon_range,
            'within_tolerance':max(start_range,colon_range)<=.1})
        if max(start_range,colon_range)>.1:
            findings.append({'route':'layout_review','code':'equal_advance_label_alignment_drift',
                'ids':[x['id'] for x in group],'closed':False,'blocks_current_draft':True})
    if any(not x['explicit_left_aligned'] for x in output):
        findings.append({'route':'layout_review','code':'bullet_uses_inherited_or_nonleft_alignment',
            'closed':False,'blocks_current_draft':True})
    return {'status':'passed' if not findings else 'needs_layout_review','pdf_sha256':engine.sha(pdf_path),
        'docx_sha256':engine.sha(docx_path),'labels':output,'equal_natural_advance_groups':comparisons,
        'blocking_findings':findings,'comparison_tolerance_pt':.1,'width_denominator_not_changed':True,
        'different_length_labels':'Natural varying positions retained; no padding, compression, fake column or text edits.',
        'method':'Actual ordered PDF glyph origins plus DOCX paragraph indent/alignment; content mapping and tail widths are checked separately.'}

def make_doc(folder, content, lang, presentation=None):
    rows,logs=structure(content['rows'],lang,presentation)
    rows=[{'id':'name','kind':'name','text':content['name']},
          {'id':'target','kind':'contact','text':('求职意向：' if lang=='zh' else 'Target: ')+content['target_role']},
          {'id':'synthetic','kind':'marker','text':'合成开发样本｜非真实候选人' if lang=='zh' else 'SYNTHETIC DEVELOPMENT SAMPLE | NOT A REAL CANDIDATE'}]+rows
    doc=engine.en.base('en') if lang=='en' else Document(BASE/'templates/resume-template-zh.docx')
    if lang=='zh':
        if engine.backend_name() == 'word':
            # Word's legacy mode varies the advance after the inline bullet.
            for mode in doc.settings.element.xpath(
                './w:compat/w:compatSetting[@w:name="compatibilityMode"]'
                '[@w:uri="http://schemas.microsoft.com/office/word"][@w:val="14"]'
            ):
                mode.set(qn('w:val'), '15')
        for child in list(doc._element.body):
            if engine.E.QName(child).localname!='sectPr': doc._element.body.remove(child)
    # Suppress justification expansion on intentionally balanced semantic line breaks.
    # Fonts, font sizes, paragraph spacing, page geometry and numbering stay unchanged.
    if presentation and presentation.get('bullet_breaks'):
        settings=doc.settings.element
        compat=settings.find('w:compat',engine.N)
        if compat is None:compat=engine.E.SubElement(settings,'{'+engine.N['w']+'}compat')
        if compat.find('w:doNotExpandShiftReturn',engine.N) is None:
            engine.E.SubElement(compat,'{'+engine.N['w']+'}doNotExpandShiftReturn')
    for row in rows:
        formatter=engine.en if lang=='en' else engine.zh
        if row['kind']=='entry' and row.get('entry_emphasis') is not None:
            p=formatter.para(doc,'','entry',lang,None,None)
            primary=row['entry_emphasis']['text'];text=row['text']
            if primary in text:
                start=text.index(primary)
                formatter.run(p,text[:start],None,False,lang)
                formatter.run(p,primary,None,True,lang)
                formatter.run(p,text[start+len(primary):],None,False,lang)
            else:formatter.run(p,text,None,False,lang)
            if row.get('date'):formatter.run(p,'\t'+row['date'],None,True,lang)
        else:
            p=formatter.para(doc,row['text'],row['kind'],lang,row.get('date') or None,row.get('label'))
        apply_chinese_bullet_alignment(p,row,lang,presentation)
        if row.get('right_aligned'):
            p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
            for run in p.runs:
                run.bold=True
    for field in ['author','last_modified_by','title','subject','comments','keywords','category','identifier','version']:
        setattr(doc.core_properties,field,'')
    if lang=='en':engine.en.save(doc,folder/'resume.docx')
    else:
        doc.save(folder/'before-line-overlay.docx')
        save(folder/'separator-assignments.json',engine.overlay(folder/'before-line-overlay.docx',folder/'before-punctuation-fix.docx',[r['text'] for r in rows if r['kind']=='section']))
        save(folder/'punctuation-font-changes.json',engine.punctuation_font_fix(folder/'before-punctuation-fix.docx',folder/'resume.docx'))
    save(folder/'content.json',{'paragraphs':rows});save(folder/'STRUCTURE_CHANGES.json',logs)
    word=Document(folder/'resume.docx')
    expected=[('• ' if lang=='zh' and r['kind']=='bullet' else '')+(r.get('label','')+' ' if r.get('label') else '')+r['text']+('\t'+r['date'] if r.get('date') else '') for r in rows]
    assert [p.text for p in word.paragraphs]==expected
    (folder/'docx-body.txt').write_text('\n'.join(expected)+'\n',encoding='utf-8')
    checks=[]
    for row,p in zip(rows,word.paragraphs):
        if row['kind']!='bullet' or not row.get('label'):continue
        start=2 if lang=='zh' else 0; end=start+len(row['label']); cursor=0; label_chars=[]; body_chars=[]
        for run in p.runs:
            for char in run.text:
                if start<=cursor<end:label_chars.append(bool(run.bold))
                elif cursor>end and not char.isspace():body_chars.append(bool(run.bold))
                cursor+=1
        assert len(label_chars)==len(row['label']) and all(label_chars)
        assert body_chars and not any(body_chars)
        checks.append({'id':row['id'],'label':row['label'],'label_and_colon_bold':True,'body_not_bold':True})
    save(folder/'RUN_FORMAT_CHECKS.json',checks)
    return rows
def render_candidate(candidate, lang, output_dir, presentation=None):
    if lang not in ('en','zh'):raise ValueError('Language must be en or zh')
    folder=Path(output_dir);folder.mkdir(parents=True,exist_ok=False)
    content=rows_from_candidate(candidate,lang,presentation)
    save(folder/'candidate.json',candidate);save(folder/'presentation.json',presentation or {})
    save(folder/'environment.json',engine.check_environment())
    save(folder/'PRESENTATION_NORMALIZATIONS.json',content['presentation_normalizations'])
    rows=make_doc(folder,content,lang,presentation)
    attempt=folder/'attempt-01';attempt.mkdir()
    with tempfile.TemporaryDirectory(prefix='bilingual-style-') as profile:
        p=subprocess.run([engine.RENDERER,'--headless','--norestore','--nodefault','--nologo','-env:UserInstallation='+Path(profile).as_uri(),'--convert-to','pdf:writer_pdf_Export','--outdir',str(attempt),str(folder/'resume.docx')],env=engine.environment(),capture_output=True,text=True,timeout=90)
    save(attempt/'process.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    if p.returncode or not(attempt/'resume.pdf').exists():raise ValueError('Fixed renderer failed; no automatic retries')
    bold=None
    if lang=='zh' and any(r.get('label') for r in rows):
        from pdf_label_bold import embolden_targets
        targets=[]
        for r in rows:
            if r.get('label'):targets.append({'id':r['id'],'kind':'label','text':r['label'],'context_text':r['label'],'font_size':12})
            elif r['kind']=='section':targets.append({'id':r['id'],'kind':'section','text':r['text'],'context_text':r['text'],'font_size':14})
            elif r.get('entry_emphasis') and r['entry_emphasis']['text'] in r['text']:
                targets.append({'id':r.get('source_id',r['id']),'kind':'entry_primary','text':r['entry_emphasis']['text'],'context_text':r['text'],'font_size':12})
        (attempt/'resume.pdf').rename(attempt/'resume-regular.pdf')
        bold=embolden_targets(attempt/'resume-regular.pdf',attempt/'resume.pdf',targets)
    m=engine.measure(folder/'resume.docx',attempt/'resume.pdf',rows,lang,attempt)
    if bold:
        bold['evidence_path']=str(attempt/'VISUAL_BOLD_EVIDENCE.json')
        m['visual_bold']=bold
    if lang=='zh':
        m['chinese_label_alignment']=measure_chinese_label_alignment(attempt/'resume.pdf',folder/'resume.docx',rows)
        save(folder/'CHINESE_LABEL_ALIGNMENT.json',m['chinese_label_alignment'])
    m['pdf_path']=str(attempt/'resume.pdf')
    m['presentation_normalizations']=content['presentation_normalizations']
    m['style_version']=STYLE_VERSION;m['style_fingerprint']=style_fingerprint();m['typography_fingerprint']=typography_fingerprint()
    m['new_API_calls']=0;m['visual_review']='pending'
    save(folder/'STYLE_MEASUREMENT.json',m)
    return m
