"""General document transformations. Never edits personal factual strings.
Fullwidth Chinese punctuation resolves to the already-configured East Asian font;
no body font/size, paragraph pitch or margin reduction.
"""
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from pathlib import Path
import copy,re
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
N={'w':W[1:-1]};PUNCT='，。；：！？、'
def decode_emphasis(text):
 # Balanced inline emphasis is presentation syntax. Unbalanced/literal stars stay.
 return re.sub(r'\*\*([^*\n]+)\*\*',r'\1',text)
def punctuation_font_fix(source,target):
 with ZipFile(source) as z:files={k:z.read(k) for k in z.namelist()}
 d=E.fromstring(files['word/document.xml']);before=''.join(d.xpath('//w:t/text()',namespaces=N));changes=[]
 for run in list(d.xpath('//w:r[w:t]',namespaces=N)):
  if any(E.QName(x).localname not in ['rPr','t'] for x in run):continue
  text=''.join(run.xpath('./w:t/text()',namespaces=N));parts=[x for x in re.split('(['+PUNCT+'])',text) if x]
  if not text or len(parts)<2 and not (len(text)==1 and text in PUNCT):continue
  prop=run.find(W+'rPr');rf=prop.find(W+'rFonts') if prop is not None else None
  if rf is None or not rf.get(W+'eastAsia'):raise ValueError('Explicit East Asian font required; no silent font fallback')
  ea=rf.get(W+'eastAsia');parent=run.getparent();index=parent.index(run);parent.remove(run)
  for offset,t in enumerate(parts):
   child=E.Element(W+'r');pr=copy.deepcopy(prop);child.append(pr)
   if len(t)==1 and t in PUNCT:
    fonts=pr.find(W+'rFonts')
    for script in ['ascii','hAnsi','cs','eastAsia']:fonts.set(W+script,ea)
    changes.append({'character':t,'font':ea,'size_half_points':pr.find(W+'sz').get(W+'val') if pr.find(W+'sz') is not None else None,'reason':'Resolve punctuation unambiguously to existing East Asian font in mixed-script run.'})
   node=E.SubElement(child,W+'t');node.text=t;node.set('{http://www.w3.org/XML/1998/namespace}space','preserve');parent.insert(index+offset,child)
 assert ''.join(d.xpath('//w:t/text()',namespaces=N))==before
 files['word/document.xml']=E.tostring(d,encoding='UTF-8',xml_declaration=True,standalone=True)
 if Path(target).exists():raise ValueError('Preserve prior DOCX')
 with ZipFile(target,'w',ZIP_DEFLATED) as z:
  for k,v in files.items():z.writestr(k,v)
 return changes
