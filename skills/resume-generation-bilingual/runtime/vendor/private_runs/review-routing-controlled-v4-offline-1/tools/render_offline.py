"""Private offline rebuild. No model client/credential loader, finite render attempts.
Content review is separate: accepted rendering never means semantic truth.
"""
from pathlib import Path
import json,sys,copy,re,hashlib,subprocess,os,tempfile,zipfile,shutil,time
from lxml import etree as E
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pymupdf as fitz
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'english-runtime/scripts'))
import style_core as en
import onepage
import chinese_format as zh
from layout_patch import decode_emphasis,punctuation_font_fix
import text_mapping
from fidelity import read,write
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','mc':'http://schemas.openxmlformats.org/markup-compatibility/2006','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','v':'urn:schemas-microsoft-com:vml'}
from native_runtime import font_directory, renderer_path, environment, check_environment, convert_docx, backend_name
F=font_directory()
_missing=[str(F/f) for f in ('times.ttf','timesbd.ttf','simkai.ttf','wingding.ttf') if not (F/f).is_file()]
if _missing: raise ValueError('Required fonts missing; run native.py doctor: '+', '.join(_missing))
FONT_R=fitz.Font(fontfile=str(F/'times.ttf'));FONT_B=fitz.Font(fontfile=str(F/'timesbd.ttf'));FONT_Z=fitz.Font(fontfile=str(F/'simkai.ttf'))
RENDERER=str(renderer_path())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def text_width(text,lang):
 if lang=='en':return FONT_B.text_length(text,fontsize=10.5)
 return sum((FONT_Z if ord(c)>255 else FONT_B).text_length(c,fontsize=12) for c in text)
def structure(rows,lang,*,fold_functional_headings=True):
 out=copy.deepcopy(rows);logs=[];width=538.6 if lang=='zh' else onepage.WIDTH
 for row in out:
  for field in ['text','date']:
   if field not in row:continue
   before=row[field];row[field]=decode_emphasis(before) if row['kind'] in ['entry','section'] else before
   if field=='date' and lang=='en':row[field]=onepage.short_dates(row[field])
   if row[field]!=before:logs.append({'id':row['id'],'field':field,'before':before,'after':row[field],'rule':'balanced presentation emphasis and date month abbreviation only','execution':'automatic structure'})
 # Legacy callers can fold an undated functional subheading. A source-bound
 # preview preserves separate headings and exact label text for the saved audit.
 functional_sections = [r for r in out if r['kind']=='section' and re.search(r'skills|tools|systems|技能|工具',r['text'],re.I)] if fold_functional_headings else []
 for section in functional_sections:
  i=out.index(section);end=next((j for j in range(i+1,len(out)) if out[j]['kind']=='section'),len(out));entries=[r for r in out[i+1:end] if r['kind']=='entry'];bullets=[r for r in out[i+1:end] if r['kind']=='bullet']
  if len(entries)==1 and not entries[0].get('date') and bullets:
   e=entries[0];b=bullets[0];old=copy.deepcopy(b)
   if e['text'].strip() and e['text'].strip().lower()!=section['text'].strip().lower():b['label']=e['text'].rstrip(':：')+('：' if lang=='zh' else ':')
   out.remove(e);logs.append({'id':e['id'],'before':e,'after':b,'rule':'fold undated functional heading into first evidence label; preserve words','execution':'automatic structure'})
 physical=[]
 for row in out:
  date=row.get('date','')
  if row['kind']=='entry' and date and text_width(row['text'],lang)+text_width(date,lang)+(36 if lang=='zh' else 12)>width:
   title=copy.deepcopy(row);title['date']='';physical.append(title);d=copy.deepcopy(row);d.update(id=row['id']+'#date',text=date,date='',right_aligned=True,source_id=row['id']);physical.append(d)
   logs.append({'id':row['id'],'before':row,'after':[title,d],'rule':'crowded complete date moved to right-aligned own paragraph; same font/size/pitch','estimated_width_pt':text_width(row['text'],lang)+text_width(date,lang),'execution':'automatic structure'})
  else:physical.append(row)
 return physical,logs

def overlay(before,after,labels):
 with zipfile.ZipFile(R/'templates/confirmed-chinese-separators.docx') as z:profile=E.fromstring(z.read('word/document.xml'))
 profiles=[copy.deepcopy(p.xpath('./w:r/mc:AlternateContent',namespaces=N)) for p in profile.xpath('/w:document/w:body/w:p',namespaces=N) if p.xpath('./w:r/mc:AlternateContent',namespaces=N)]
 assert len(profiles)==4 and all(len(x)==2 for x in profiles)
 with zipfile.ZipFile(before) as z:files={k:z.read(k) for k in z.namelist()}
 doc=E.fromstring(files['word/document.xml']);old=doc.xpath('//w:t/text()',namespaces=N);headers=doc.xpath('/w:document/w:body/w:p[w:pPr/w:pBdr]',namespaces=N);assert len(headers)==len(labels);logs=[]
 for i,p in enumerate(headers):
  border=p.find('w:pPr/w:pBdr',N);border.getparent().remove(border)
  for j,ac in enumerate(copy.deepcopy(profiles[min(i,3)])):
   for el in ac.xpath('.//wp:docPr',namespaces=N):el.set('id',str(8192+i*2+j));el.set('name',f'Section line {i+1}-{j+1}')
   for el in ac.xpath('.//v:line',namespaces=N):
    el.set('id',f'SectionLine{i}_{j}')
    for key in list(el.attrib):
     if E.QName(key).localname=='spid':el.set(key,'_x0000_s'+str(8192+i*2+j))
   E.SubElement(p,'{'+N['w']+'}r').append(ac)
  logs.append({'module':labels[i],'profile':min(i,3)+1,'geometry_and_spacing':'confirmed paired independent line objects unchanged'})
 assert doc.xpath('//w:t/text()',namespaces=N)==old
 files['word/document.xml']=E.tostring(doc,encoding='UTF-8',xml_declaration=True,standalone=True)
 with zipfile.ZipFile(after,'w',zipfile.ZIP_DEFLATED) as z:
  for k,v in files.items():z.writestr(k,v)
 return logs

def make_doc(folder,content,lang):
 rows,logs=structure(content['rows'],lang)
 heading=[{'id':'name','kind':'name','text':content['name']},{'id':'target','kind':'contact','text':('求职意向：' if lang=='zh' else 'Target: ')+content['target_role']},{'id':'synthetic','kind':'marker','text':'合成开发样本｜非真实候选人' if lang=='zh' else 'SYNTHETIC DEVELOPMENT SAMPLE | NOT A REAL CANDIDATE'}]
 rows=heading+rows
 doc=en.base('en') if lang=='en' else Document(R/'templates/resume-template-zh.docx')
 if lang=='zh':
  for child in list(doc._element.body):
   if E.QName(child).localname!='sectPr':doc._element.body.remove(child)
 for row in rows:
  p=(en.para if lang=='en' else zh.para)(doc,row['text'],row['kind'],lang,row.get('date') or None,row.get('label'))
  if row.get('right_aligned'):p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
 for field in ['author','last_modified_by','title','subject','comments','keywords','category','identifier','version']:setattr(doc.core_properties,field,'')
 if lang=='en':en.save(doc,folder/'resume.docx')
 else:
  doc.save(folder/'before-line-overlay.docx');write(folder/'separator-assignments.json',overlay(folder/'before-line-overlay.docx',folder/'before-punctuation-fix.docx',[r['text'] for r in rows if r['kind']=='section']));write(folder/'punctuation-font-changes.json',punctuation_font_fix(folder/'before-punctuation-fix.docx',folder/'resume.docx'))
 write(folder/'content.json',{'paragraphs':rows});write(folder/'STRUCTURE_CHANGES.json',logs)
 (folder/'docx-body.txt').write_text('\n'.join(p.text for p in Document(folder/'resume.docx').paragraphs)+'\n')
 expected=[(('• ' if lang=='zh' and r['kind']=='bullet' else '')+(r.get('label','')+' ' if r.get('label') else '')+r['text']+('\t'+r['date'] if r.get('date') else '')) for r in rows]
 assert [p.text for p in Document(folder/'resume.docx').paragraphs]==expected
 return rows

def measure(docx,pdfpath,rows,lang,output):
 pdf=fitz.open(pdfpath);raw='\n'.join(page.get_text('text',sort=False) for page in pdf);(output/'pdf-body.txt').write_text(raw);mapping=text_mapping.check(docx,output/'pdf-body.txt')
 if lang=='en':
  onepage.configure_fonts(F/'times.ttf',F/'timesbd.ttf');mapped,errors=onepage.map_paragraphs(pdf,rows)
  mapping={'word_pdf_body_match_in_order':not errors,'unmatched':errors,'spacing_candidates':[],'source_verified_physical_wrap_rejoins':[{'paragraph_id':p['id'],'rejoins':p['source_verified_layout_rejoins']} for p in mapped if p['source_verified_layout_rejoins']],'method':'Strict ordered word mapping; rejoin source-identical hyphen pieces only across measured physical lines; no whitespace deletion/silent resync','not_all_spaces_deleted':True}
 fonts=[];page_details=[]
 for pi,page in enumerate(pdf):
  offpage=[];outside=[];chars=[];lines=[]
  margin=28.35 if lang=='zh' else 56.7;topmargin=28.35 if lang=='zh' else 48.2
  for block in page.get_text('rawdict',clip=fitz.INFINITE_RECT())['blocks']:
   for line in block.get('lines',[]):
    text=''.join(c['c'] for s in line['spans'] for c in s['chars']);lines.append({'text':text,'bbox':list(line['bbox'])})
    for span in line['spans']:
     for c in span['chars']:
      if c['c'].isspace():continue
      x0,y0,x1,y1=c['bbox'];chars.append(c)
      if x0<-.5 or y0<-.5 or x1>page.rect.width+.5 or y1>page.rect.height+.5:offpage.append({'character':c['c'],'bbox':list(c['bbox'])})
      if x0<margin-.85 or x1>page.rect.width-margin+.85:outside.append({'character':c['c'],'bbox':list(c['bbox'])})
  for xref,ext,typ,name,*rest in page.get_fonts(full=True):fonts.append({'name':name,'embedded':bool(pdf.extract_font(xref)[3])})
  bottom=max((x['bbox'][3] for x in chars),default=0);punctonly=bool(outside) and all(x['character'] in '，。；：、！？）》】」』”“‘’）,.!?;:)' for x in outside)
  page_details.append({'page':pi+1,'text_lines':lines,'last_line':lines[-1] if lines else None,'body_utilization_pct':round((bottom-topmargin)/(page.rect.height-2*topmargin)*100,2),'page_bottom_whitespace_mm':round((page.rect.height-bottom)*25.4/72,2),'off_page_characters':offpage,'outside_body_characters':outside,'hanging_punctuation_only':punctonly,'hanging_punctuation_is_not_missing_or_clipped':punctonly and not offpage,'nonpunctuation_body_overflow':bool(outside) and not punctonly,'date_orphan_month_lines':[l for l in lines if l['text'].strip()=='月']})
  page.get_pixmap(matrix=fitz.Matrix(1.15,1.15),alpha=False).save(output/f'page-{pi+1:02d}.png')
 allowed={'TimesNewRoman','TimesNewRomanPS','Wingdings','KaiTi','KaiTi_GB2312'}
 visible_fonts={span['font'] for page in pdf for block in page.get_text('dict')['blocks'] for line in block.get('lines',[]) for span in line['spans'] if span['text'].strip()}
 unexpected=[name for name in visible_fonts if not any(x in re.sub('[^A-Za-z0-9_]','',name) for x in allowed)]
 fontok=all(f['embedded'] for f in fonts) and not unexpected
 word=Document(docx);sec=word.sections[0];geometry={k:round(getattr(sec,k).pt,3) for k in ['page_width','page_height','top_margin','bottom_margin','left_margin','right_margin']}
 sizes=sorted({run.font.size.pt for p in word.paragraphs for run in p.runs if run.font.size is not None});actualclip=any(p['off_page_characters'] for p in page_details);overflow=any(p['nonpunctuation_body_overflow'] for p in page_details);orphan=any(p['date_orphan_month_lines'] for p in page_details)
 q={'pages':len(pdf),'word_pdf_mapping':mapping,'fonts':fonts,'unexpected_fonts':unexpected,'fonts_validated':fontok,'geometry_pt':geometry,'explicit_run_font_sizes_pt':sizes,'pages_detail':page_details,'actual_clipping_detected':actualclip,'nonpunctuation_body_overflow':overflow,'date_month_orphan':orphan,'balanced_markdown_remaining':bool(re.search(r'\*\*[^*]+\*\*','\n'.join(p.text for p in word.paragraphs))),'content_truth_automatically_validated':False,'native_word_or_ats_verified':False,'pdf_font_validation_scope':'All fonts must be embedded; only fonts actually drawing non-whitespace glyphs are checked against the typeface allowlist. Full font inventory retained.','visible_glyph_fonts':sorted(visible_fonts)}
 write(output/'measurement.json',q)
 return q

def render(instance,lang,version='v01'):
 folder=R/'rendered'/instance/lang/version
 if (folder/'ACCEPTED_RENDER.json').exists():
  receipt=read(folder/'ACCEPTED_RENDER.json')
  if sha(folder/'resume.docx')!=receipt['docx_sha256'] or sha(folder/receipt['pdf'])!=receipt['pdf_sha256']:raise ValueError('Accepted artifact mutated')
  return read(folder/'RENDER_STATUS.json')
 if not folder.exists():
  folder.mkdir(parents=True);content=read(R/'drafts'/instance/lang/(version+'-reviewed-rows.json'));make_doc(folder,content,lang)
 rows=read(folder/'content.json')['paragraphs']
 for number in range(1,4):
  attempt=folder/f'render-attempt-{number:02d}'
  if attempt.exists():continue
  attempt.mkdir();write(attempt/'started.json',{'attempt':number,'max_attempts':3,'docx_sha256':sha(folder/'resume.docx')});start=time.monotonic()
  try:
   with tempfile.TemporaryDirectory(prefix='bilingual-offline-lo-') as tmp:
    q=subprocess.run([RENDERER,'--headless','--norestore','--nodefault','--nologo','-env:UserInstallation='+Path(tmp).as_uri(),'--convert-to','pdf:writer_pdf_Export','--outdir',str(attempt),str(folder/'resume.docx')],env=environment(),capture_output=True,text=True,timeout=90)
   write(attempt/'process.json',{'returncode':q.returncode,'stdout':q.stdout,'stderr':q.stderr,'elapsed_seconds':round(time.monotonic()-start,2)})
   if q.returncode or not (attempt/'resume.pdf').exists():raise ValueError('Renderer did not produce PDF')
   m=measure(folder/'resume.docx',attempt/'resume.pdf',rows,lang,attempt)
   if not m['fonts_validated']:raise ValueError('Font validation failed after measurement; render not accepted')
   # A deterministic text/content mismatch is not repaired by repeating conversion.
   accepted=m['word_pdf_mapping']['word_pdf_body_match_in_order'] and not m['actual_clipping_detected']
   r={'instance':instance,'language':lang,'version':version,'pages':m['pages'],'render_accepted':accepted,'text_mapping_pass':m['word_pdf_mapping']['word_pdf_body_match_in_order'],'fonts_pass':m['fonts_validated'],'actual_clipping':m['actual_clipping_detected'],'nonpunctuation_overflow':m['nonpunctuation_body_overflow'],'date_month_orphan':m['date_month_orphan'],'one_page_layout_pass':accepted and m['pages']==1 and not m['nonpunctuation_body_overflow'] and not m['date_month_orphan'],'content_status':read(R/'facts'/f'{instance}.json')['languages'][lang]['status'],'visual_review':'pending','docx':str((folder/'resume.docx').relative_to(R)),'pdf':str((attempt/'resume.pdf').relative_to(R)),'measurement':str((attempt/'measurement.json').relative_to(R)),'no_paid_model_call_this_round':True}
   write(attempt/'RESULT.json',{'accepted_render':accepted,'measurement_is_not_acceptance':True})
   write(folder/'RENDER_STATUS.json',r)
   if accepted:write(folder/'ACCEPTED_RENDER.json',{'docx_sha256':sha(folder/'resume.docx'),'pdf':str((attempt/'resume.pdf').relative_to(folder)),'pdf_sha256':sha(attempt/'resume.pdf'),'font_and_measurement_passed':True,'semantic_quality_proven':False,'one_page_final':r['one_page_layout_pass']})
   return r
  except Exception as ex:
   write(attempt/'FAILED.json',{'type':type(ex).__name__,'reason':str(ex),'accepted':False,'evidence_retained':True})
 # Do not accept measurement existence as completed state.
 return {'instance':instance,'language':lang,'version':version,'render_accepted':False,'reason':'Three finite render attempts exhausted; preserved failures, restore config then new scoped recovery review required.'}

def main():
 config=check_environment()
 if not (R/'RENDER_ENVIRONMENT.json').exists():write(R/'RENDER_ENVIRONMENT.json',config)
 result=[]
 for row in read(R/'inputs-manifest.json')['groups']:
  for lang in ['en','zh']:
   try:r=render(row['instance'],lang)
   except Exception as ex:r={'instance':row['instance'],'language':lang,'render_accepted':False,'error':type(ex).__name__,'reason':str(ex)}
   result.append(r);print(json.dumps({k:r.get(k) for k in ['instance','language','pages','text_mapping_pass','one_page_layout_pass','error','reason']},ensure_ascii=False),flush=True)
 if not (R/'RENDER_INDEX-v01.json').exists():write(R/'RENDER_INDEX-v01.json',result)
if __name__=='__main__':main()
