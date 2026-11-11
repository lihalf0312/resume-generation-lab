"""Complete ordered Chinese extraction mapping,including unconsumed PDF text.
Never delete all spaces or remove punctuation to force a match.
"""
import re
from pathlib import Path
from docx import Document
from check_chinese_text import canonical

def locate(needle,hay,start=0):
 at=hay.find(needle,start)
 if at>=0:return at,at+len(needle),[]
 pat=[];edges=[]
 for i,c in enumerate(needle):
  pat.append(re.escape(c))
  if i+1<len(needle) and ((c in '”’' and '\u3400'<=needle[i+1]<='\u9fff') or ('\u3400'<=c<='\u9fff' and needle[i+1] in '£€$')):
   pat.append(' ?');edges.append({'after_source_character':i,'boundary':needle[i:i+2]})
 m=re.compile(''.join(pat)).search(hay,start)
 return (m.start(),m.end(),edges) if m else (-1,-1,[])

def gap_records(text,location,start,full=None):
 # Whitespace is layout; a standalone bullet/numbering glyph may be a renderer
 # generated list marker. A bullet adjacent to content cannot hide that content.
 ignored=[];unexpected=[];cursor=0
 for m in re.finditer(r'(?<!\S)[•\uf09f](?!\S)',text):
  absolute=start+m.start();after=start+m.end()
  if full is not None and ((absolute>0 and not full[absolute-1].isspace()) or (after<len(full) and not full[after].isspace())):continue
  if text[cursor:m.start()].strip():unexpected.append({'location':location,'start':start+cursor,'text':text[cursor:m.start()]})
  ignored.append({'location':location,'start':start+m.start(),'text':m.group(),'reason':'standalone delivery/list marker only'});cursor=m.end()
 if text[cursor:].strip():unexpected.append({'location':location,'start':start+cursor,'text':text[cursor:]})
 return unexpected,ignored

def check(docx,pdftext):
 paras=[p.text for p in Document(docx).paragraphs];hay=canonical(Path(pdftext).read_text());pos=0;missing=[];adapt=[];spacing=[];extra=[];ignored=[];matched=[]
 for i,text in enumerate(paras):
  needle=canonical(text)
  if not needle:continue
  at,end,edges=locate(needle,hay,pos)
  if at<0:missing.append({'paragraph':i,'text':text})
  else:
   gaps,marks=gap_records(hay[pos:at],f'before paragraph {i}',pos,hay);extra.extend(gaps);ignored.extend(marks);matched.append({'paragraph':i,'start':at,'end':end});pos=end
   if edges:adapt.append({'paragraph':i,'observed_auto_spacing_edges':edges,'source_normalized':needle,'matched_pdf_normalized':hay[at:end]})
  if re.search(r'(?<=[A-Za-z]) {2,}(?=[A-Za-z])',text):spacing.append({'paragraph':i,'kind':'authored_multiple_ascii_spaces_review','text':text})
 gaps,marks=gap_records(hay[pos:],'trailing PDF text',pos,hay);extra.extend(gaps);ignored.extend(marks)
 return {'word_pdf_body_match_in_order':not missing and not extra,'source_paragraphs_all_found':not missing,'unmatched':missing,'unexpected_pdf_text':extra,'ignored_delivery_characters':ignored,'matched_pdf_ranges':matched,'spacing_candidates':spacing,'observed_render_spacing_adaptations':adapt,'method':'Complete ordered paragraph coverage plus prefix/interparagraph/trailing range checks; only whitespace and explicitly recorded standalone list glyphs exempt. Preserve ordinary Latin/Han word boundaries and all punctuation; documented physical CJK newline/DE-DN/curlyquote-currency spacing exceptions retained with evidence.','not_all_spaces_deleted':True,'native_word_or_ats_verified':False}
