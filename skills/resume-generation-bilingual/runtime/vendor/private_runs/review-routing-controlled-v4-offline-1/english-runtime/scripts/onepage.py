"""Reusable offline one-page workflow; no case-based deletion and no model client.

Automatic structure never selects weak evidence. Semantic edits are explicit,
source-linked Codex/human decisions applied by a generic patch interpreter.
"""
from pathlib import Path
from collections import Counter,defaultdict
from statistics import median
from datetime import datetime,timezone
import argparse,copy,hashlib,json,math,re,subprocess,sys,zipfile
from lxml import etree as E
from docx import Document
import pymupdf as fitz
from PIL import Image,ImageDraw
import style_core as style


BASE=Path(__file__).resolve().parent
MAXBODY={'page_width_pt':11906/20,'page_height_pt':16838/20,'margin_top_pt':964/20,'margin_bottom_pt':964/20,'margin_left_pt':1134/20,'margin_right_pt':1134/20,'body_font_pt':10.5,'grid_pitch_pt':312/20,'bullet_indent_pt':36}
WIDTH=MAXBODY['page_width_pt']-MAXBODY['margin_left_pt']-MAXBODY['margin_right_pt']
HEIGHT=MAXBODY['page_height_pt']-MAXBODY['margin_top_pt']-MAXBODY['margin_bottom_pt']
MONTHS={x[:3]:x for x in ['January','February','March','April','May','June','July','August','September','October','November','December']}
FUNCTIONAL={'education':'education','tools':'tools','skills':'skills','technical tools':'tools','technical skills':'skills','professional development':'development','development':'development','training':'training','certification':'certification','certifications':'certification'}

def read(path):return json.loads(Path(path).read_text())
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def norm(x):return re.sub(r'[ \t\r\n]+',' ',x).strip()
def ptext(p):return (p.get('label','')+' ' if p.get('label') else '')+p['text']+(' | '+p['date'] if p.get('date') else '')
def plain(rows):return '\n'.join(ptext(p) for p in rows)+'\n'
def flatten(resume):
    rows=[{'id':'name','kind':'name','text':resume['name']}]
    if resume.get('target_role'):rows.append({'id':'target','kind':'contact','text':'Target: '+resume['target_role']})
    if resume.get('synthetic',False): rows.append({'id':'synthetic-marker','kind':'marker','text':'SYNTHETIC SAMPLE | NOT A REAL CANDIDATE'})
    for si,s in enumerate(resume['sections']):
        rows.append({'id':f's{si}','kind':'section','text':s['heading'],'section':si})
        for ii,item in enumerate(s['items']):
            rows.append({'id':f's{si}.i{ii}','kind':'entry','text':item['heading'],'date':item.get('date',''),'section':si,'item':ii})
            for bi,b in enumerate(item.get('bullets',[])):
                rows.append({'id':f's{si}.i{ii}.b{bi}','kind':'bullet','text':b,'section':si,'item':ii})
    return rows

def short_dates(text):
    for short,full in MONTHS.items():text=re.sub(r'\b'+full+r'\b',short,text)
    return text
def date_atom(text):
    m=re.fullmatch(r'([A-Za-z]+)\s+(\d{4})',text.strip())
    return (m[1][:3].lower(),m[2]) if m else None

def automatic_structure(rows):
    out=copy.deepcopy(rows);changes=[]
    def log(rule,before,after):changes.append({'class':'automatic_structure','rule':rule,'before':before,'after':after,'semantic_quality_pass':None})
    for p in out:
        if p.get('date'):
            old=copy.deepcopy(p);p['date']=short_dates(p['date'])
            if p!=old:log('month_abbreviation_preserves_precision',old,copy.deepcopy(p))
    # Explicit awarded date may be folded only when it equals the supplied
    # study end month. Preserve both range endpoints and awarded status.
    for entry in [p for p in out if p['kind']=='entry' and re.search(r'\b(BEng|MEng|BSc|MSc|BA|MA|PhD|Bachelor|Master|Doctorate)\b',p['text'])]:
        body=[p for p in out if p['kind']=='bullet' and (p.get('section'),p.get('item'))==(entry.get('section'),entry.get('item'))]
        date=entry.get('date','');parts=date.split(';',1);range_=parts[0].strip();end=re.split(r'\s*[–—]\s*',range_)[-1]
        award=None;award_body=None;rest=None
        if len(parts)>1:
            m=re.fullmatch(r'\s*(?:degree\s+)?awarded\s+(.+)\s*',parts[1],re.I)
            if m:award=m[1].strip()
        for b in body:
            m=re.match(r'^Degree awarded ([A-Za-z]+ \d{4})(?:;\s*(.*))?$',b['text'])
            if m and (not award or date_atom(short_dates(award))==date_atom(short_dates(m[1]))):
                award=short_dates(m[1]);award_body=b;rest=m[2]
        if award and date_atom(end) and date_atom(end)==date_atom(short_dates(award)):
            old=copy.deepcopy(entry);entry['date']=range_+' (awarded)';log('same_month_award_dedup_keep_study_range',old,copy.deepcopy(entry))
            if award_body:
                old=copy.deepcopy(award_body)
                if rest:award_body['text']=rest
                else:out.remove(award_body)
                log('move_explicit_award_status_not_delete_qualification',old,copy.deepcopy(award_body) if rest else None)
    # Mixed functional sections can be split without moving experience ownership.
    for section in [p for p in out if p['kind']=='section']:
        parts=re.split(r'\s+(?:and)\s+|\s*&\s*',section['text'],flags=re.I)
        cats=[FUNCTIONAL.get(p.lower().strip()) for p in parts]
        if len(parts)==2 and all(cats):
            entries=[p for p in out if p['kind']=='entry' and p.get('section')==section.get('section')]
            if entries:
                e=entries[-1];cat=FUNCTIONAL.get(e['text'].lower().strip())
                if not e.get('date') and cat==cats[-1]:
                    old=copy.deepcopy(section);section['text']=parts[0];log('separate_mixed_functional_categories',old,copy.deepcopy(section))
                    old=copy.deepcopy(e);e['kind']='section';log('retain_child_category_as_section',old,copy.deepcopy(e))
    # Fold an undated functional subheading into a label, retaining its words.
    for section in [p for p in out if p['kind']=='section' and FUNCTIONAL.get(p['text'].lower().strip()) in ('skills','tools')]:
        idx=out.index(section);end=next((i for i in range(idx+1,len(out)) if out[i]['kind']=='section'),len(out));group=out[idx+1:end]
        entries=[p for p in group if p['kind']=='entry'];bullets=[p for p in group if p['kind']=='bullet']
        if len(entries)==1 and not entries[0].get('date') and bullets:
            entry=entries[0];old=copy.deepcopy(entry)
            if entry['text'].strip().lower()!=section['text'].strip().lower():
                first=bullets[0];old_b=copy.deepcopy(first);first['label']=entry['text'].rstrip(':')+':'
                log('fold_label_preserve_unique_heading_information',old_b,copy.deepcopy(first))
            out.remove(entry);log('remove_standalone_functional_subheading_row',old,None)
    # Only exact empty separators, never empty early employment headings.
    for p in list(out):
        if p['kind']=='gap' or p['kind']=='body' and not p['text'].strip():out.remove(p);log('remove_empty_separator',p,None)
    return out,changes

def apply_semantic(rows,decision,source):
    out=copy.deepcopy(rows);changes=[]
    if decision.get('editor')!='Codex-assisted semantic editing':raise ValueError('semantic decisions must identify editor class')
    for op in decision.get('operations',[]):
        p=next((p for p in out if p['id']==op['paragraph_id']),None)
        if p is None or ptext(p)!=op['before']:raise ValueError('patch does not match current paragraph')
        if not op.get('reason') or not op.get('source_fragments'):raise ValueError('source and reason required')
        for f in op['source_fragments']:
            if f['field'] not in ('material_text','jd_text'):raise ValueError('unsupported source field')
            text=source[f['field']]
            if type(f.get('start')) is not int or type(f.get('end')) is not int or f['start']<0 or f['end']<=f['start'] or f['end']>len(text):raise ValueError('invalid source fragment offsets')
            if text[f['start']:f['end']]!=f['quote']:raise ValueError('source fragment not literal; never strip spaces')
        if 'after_date' in op:
            if op.get('action')!='replace' or p['kind']!='entry':raise ValueError('after_date is allowed only for replace on an entry row')
            if not isinstance(op['after_date'],str):raise ValueError('after_date must be a string')
            if not any(f['field']=='material_text' for f in op['source_fragments']):raise ValueError('date edits require literal material_text evidence; JD is selection data only')
        old=copy.deepcopy(p)
        if op['action']=='replace':
            if 'after' not in op and 'after_date' not in op:raise ValueError('replace requires after text and/or after_date')
            if 'after' in op:
                if not isinstance(op['after'],str):raise ValueError('after text must be a string')
                p['text']=op['after']
            if 'after_date' in op:p['date']=op['after_date']
        elif op['action']=='remove':out.remove(p)
        else:raise ValueError('unapproved semantic operation')
        changes.append({**op,'class':'Codex-assisted semantic editing','before_row':old,'after_row':copy.deepcopy(p) if p in out else None,'semantic_quality_pass':None})
    return out,changes

def core(path):
    with zipfile.ZipFile(path) as z:
        d=E.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        return ({n:sha(E.tostring(E.fromstring(z.read(n)),method='c14n')) for n in ('word/styles.xml','word/numbering.xml')},E.tostring(d.find('w:body/w:sectPr',ns),method='c14n'))
def build(folder,rows):
    folder.mkdir(parents=True,exist_ok=False);save(folder/'content.json',{'paragraphs':rows})
    doc=style.base('en')
    for p in rows:style.para(doc,p['text'],p['kind'],'en',p.get('date'),p.get('label'))
    path=folder/'resume.docx';style.save(doc,path)
    assert core(path)==core(BASE.parent/'assets/blank-english-template.docx')
    (folder/'resume.txt').write_text(plain(rows));save(folder/'style-check.json',{'exact_styles_numbering_section_match':True,'geometry':MAXBODY,'fixed_constructor_font_spacing_margin_policy':True,'measurement_scope':'canonical styles, numbering and section properties compared; fixed paragraph constructors used'})
REG=None; BOLD=None

def configure_fonts(regular,bold):
    global REG,BOLD
    REG=fitz.Font(fontfile=str(regular)); BOLD=fitz.Font(fontfile=str(bold))

def estimated_lines(p):
    font=BOLD if p['kind'] in ('name','section','entry') else REG
    size=18 if p['kind']=='name' else 12 if p['kind']=='section' else 8 if p['kind']=='marker' else 10.5
    width=WIDTH-(36 if p['kind']=='bullet' else 0)
    text=(p.get('label','')+' ' if p.get('label') else '')+p['text']
    lines=1;used=0
    for word in text.split():
        w=font.text_length(word,fontsize=size);gap=font.text_length(' ',fontsize=size) if used else 0
        if used and used+gap+w>width:lines+=1;used=w
        else:used+=gap+w
    if p.get('date'):
        dw=BOLD.text_length(p['date'],fontsize=10.5)
        if used+dw+6>width:lines+=1
    return lines

def map_paragraphs(pdf,rows):
    tokens=[];baselines={}
    for page_index,page in enumerate(pdf):
        for block in page.get_text('dict')['blocks']:
            if block.get('type')!=0:continue
            for li,line in enumerate(block['lines']):
                baselines[(page_index,block['number'],li)]=median(s['origin'][1] for s in line['spans'])
        for word in page.get_text('words',sort=False):
            if word[4] in ('\uf09f','•'):continue
            tokens.append({'page':page_index,'box':list(word[:4]),'text':word[4],'baseline':baselines.get((page_index,word[5],word[6]),word[3])})
    cursor=0;result=[];failures=[]
    for p in rows:
        wanted=((p.get('label','')+' ' if p.get('label') else '')+p['text']+('\t'+p['date'] if p.get('date') else '')).split();consumed=[];rejoins=[]
        for token in wanted:
            if cursor>=len(tokens):failures.append({'paragraph':p['id'],'reason':'PDF ended early'});break
            if tokens[cursor]['text']==token:consumed.append(tokens[cursor]);cursor+=1;continue
            found=False
            for count in (2,3):
                pieces=tokens[cursor:cursor+count]
                if len(pieces)!=count or not all(x['text'].endswith(('-','–','—')) for x in pieces[:-1]):continue
                if not all(a['page']!=b['page'] or abs(a['baseline']-b['baseline'])>.8 for a,b in zip(pieces,pieces[1:])):continue
                if ''.join(x['text'] for x in pieces)==token:
                    consumed.extend(pieces);rejoins.append({'source_literal':token,'pdf_parts':[x['text'] for x in pieces]});cursor+=count;found=True;break
            if not found:
                failures.append({'paragraph':p['id'],'expected':token,'actual':tokens[cursor]['text'],'reason':'real token mismatch; no whitespace deletion or silent resync'})
                return result,failures
        levels=sorted(set((x['page'],round(x['baseline'],2)) for x in consumed))
        last=[x for x in consumed if (x['page'],round(x['baseline'],2))==levels[-1]] if levels else []
        left=MAXBODY['margin_left_pt']+(36 if p['kind']=='bullet' else 0)
        available=WIDTH-(36 if p['kind']=='bullet' else 0)
        ratio=(max(x['box'][2] for x in last)-left)/available if last else None
        result.append({'id':p['id'],'kind':p['kind'],'text':ptext(p),'physical_lines':len(levels),'line_positions':levels,'estimated_lines':estimated_lines(p),'source_verified_layout_rejoins':rejoins,
                       'last_line': ' '.join(x['text'] for x in last),'last_line_width_ratio':ratio,
                       'short_tail_class':('single_line_not_subject_to_prose_ratio' if len(levels)<=1 else 'very_short_prose_tail' if ratio is not None and ratio<.15 else 'short_prose_tail_advisory' if ratio is not None and ratio<.5 else 'normal') if p['kind']=='bullet' else 'heading_or_date_not_prose',
                       'short_tail_is_not_automatically_a_defect':True})
    if cursor!=len(tokens):failures.append({'reason':'extra PDF words','remaining':len(tokens)-cursor})
    return result,failures

def measure(folder):
    rows=read(folder/'content.json')['paragraphs'];pdf=fitz.open(folder/'resume.pdf');mapped,failures=map_paragraphs(pdf,rows)
    counts=Counter(p['kind'] for p in rows);lines=Counter()
    for p in mapped:lines[p['kind']]+=p['physical_lines']
    pitches=[]
    for p in mapped:
        if p['kind']=='bullet':
            pitches += [b[1]-a[1] for a,b in zip(p['line_positions'],p['line_positions'][1:]) if a[0]==b[0] and 8<b[1]-a[1]<25]
    pitch=median(pitches) if pitches else 15.6
    pages=[]
    for i,page in enumerate(pdf):
        words=page.get_text('words');bottom=max(w[3] for w in words);top=min(w[1] for w in words)
        outside=[w for w in words if w[0]<MAXBODY['margin_left_pt']-.8 or w[2]>page.rect.width-MAXBODY['margin_right_pt']+.8 or w[1]<MAXBODY['margin_top_pt']-.8 or w[3]>page.rect.height-MAXBODY['margin_bottom_pt']+.8]
        pages.append({'page':i+1,'top_glyph_pt':top,'bottom_glyph_pt':bottom,'body_used_pct':round((bottom-MAXBODY['margin_top_pt'])/HEIGHT*100,2),'unused_bottom_body_mm':round((page.rect.height-MAXBODY['margin_bottom_pt']-bottom)*25.4/72,2),'outside_body_words':len(outside)})
        page.get_pixmap(matrix=fitz.Matrix(1.4,1.4),alpha=False).save(folder/f'page-{i+1:02}.png')
    doc=Document(folder/'resume.docx');expected=[(p.get('label','')+' ' if p.get('label') else '')+p['text']+('\t'+p['date'] if p.get('date') else '') for p in rows]
    assert [p.text for p in doc.paragraphs]==expected
    spacing=[]
    for row,p in zip(rows,doc.paragraphs):
        spacing.append({'id':row['id'],'before_pt':p.paragraph_format.space_before.pt if p.paragraph_format.space_before else 0,'after_pt':p.paragraph_format.space_after.pt if p.paragraph_format.space_after else 0,'line_rule':str(p.paragraph_format.line_spacing_rule),'keep_with_next':bool(p.paragraph_format.keep_with_next),'keep_together':bool(p.paragraph_format.keep_together)})
    (folder/'docx-body.txt').write_text('\n'.join(expected)+'\n');raw='\n'.join(p.get_text('text',sort=False) for p in pdf);(folder/'pdf-body.txt').write_text(raw)
    q={'pages':len(pdf),'geometry':MAXBODY,'usable_width_pt':WIDTH,'usable_height_pt':HEIGHT,'nominal_body_grid_rows':HEIGHT/15.6,'measured_body_pitch_pt':pitch,
       'paragraph_counts':dict(counts),'actual_lines_by_kind':dict(lines),'physical_lines_total':sum(lines.values()),'paragraphs':mapped,'token_mapping_failures':failures,'all_content_words_preserved':not failures,
       'spacing':spacing,'explicit_before_after_spacing_total_pt':sum(x['before_pt']+x['after_pt'] for x in spacing),'empty_separator_paragraphs':sum(not ptext(p).strip() for p in rows),'pages_detail':pages,
       'word_count_reference_only':len(plain(rows).split()),'approx_lines_before_render':sum(estimated_lines(p) for p in rows),'style_unchanged':core(folder/'resume.docx')==core(BASE.parent/'assets/blank-english-template.docx'),'style_check_scope':'canonical styles.xml, numbering.xml and section properties; fixed constructors control paragraph formatting',
       'original_word_pdf_render_engine':'Configured LibreOffice only; no native Word/ATS or cross-engine claim','paid_model_calls_declaration':0,'declaration_scope':'This deterministic workflow includes no model client; surrounding assistant and OS are not audited'}
    save(folder/'measurement.json',q)
    return q

