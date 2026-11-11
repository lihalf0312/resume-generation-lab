"""Compare extraction while preserving Latin word spaces and authored Han spaces."""
import re,json
from pathlib import Path
from docx import Document
CJK=r'[\u3400-\u9fff\u3000-\u303f\uff01-\uff65]'
def canonical(text):
 text=re.sub('('+CJK+')\n(?='+CJK+')',r'\1',text)
 text=re.sub(r'[ \t\r\n]+',' ',text).strip()
 text=re.sub('('+CJK+') *(?=[A-Za-z0-9])',r'\1 ',text)
 text=re.sub('([A-Za-z0-9]) *(?='+CJK+')',r'\1 ',text)
 return text
def check(docx,pdftext):
 paras=[p.text for p in Document(docx).paragraphs];hay=canonical(Path(pdftext).read_text());pos=0;missing=[];spacing=[]
 for i,text in enumerate(paras):
  if re.search(r'(?<=[A-Za-z]) {2,}(?=[A-Za-z])',text):spacing.append({'paragraph':i,'kind':'authored_multiple_ascii_word_spaces','text':text})
  needle=canonical(text)
  if not needle:continue
  at=hay.find(needle,pos)
  if at<0:missing.append({'paragraph':i,'text':text})
  else:pos=at+len(needle)
 return {'word_pdf_body_match_in_order':not missing,'unmatched':missing,'spacing_candidates':spacing,'method':'Collapse whitespace to single spaces; rejoin physical CJK-to-CJK lines; canonical one space only at Han/fullwidth-punctuation vs Latin/digit boundaries permitted by template autoSpaceDE/DN. Latin word boundaries and authored Han-to-Han spaces retained.','not_all_spaces_deleted':True,'native_word_or_ats_verified':False}
assert canonical('data base')!=canonical('database')
assert canonical('中 文')!=canonical('中文')
assert canonical('36份')==canonical('36 份')
assert canonical('Python数据')==canonical('Python 数据')
