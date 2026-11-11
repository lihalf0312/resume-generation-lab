"""Pure measured template constructors, unchanged. No person-specific functions."""
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

def node(parent,name,**a):
    n=OxmlElement('w:'+name)
    for k,v in a.items():n.set(qn('w:'+k),str(v))
    parent.append(n);return n

def run(p,text,size=None,bold=False,lang='en',color='000000'):
    r=p.add_run(text);r.font.name='Times New Roman';r.font.size=Pt(size or (12 if lang=='zh' else 10.5))
    r.font.bold=bold;r.font.color.rgb=RGBColor.from_string(color)
    rp=r._element.get_or_add_rPr();rf=rp.rFonts
    rf.set(qn('w:ascii'),'Times New Roman');rf.set(qn('w:hAnsi'),'Times New Roman')
    rf.set(qn('w:cs'),'Times New Roman');rf.set(qn('w:eastAsia'),'楷体' if lang=='zh' else 'Times New Roman')
    return r

def base(lang):
    doc=Document();sec=doc.sections[0]
    sec.page_width=Twips(11906);sec.page_height=Twips(16838)
    for side in ['top','bottom']:setattr(sec,side+'_margin',Twips(567 if lang=='zh' else 964))
    for side in ['left','right']:setattr(sec,side+'_margin',Twips(567 if lang=='zh' else 1134))
    sec.header_distance=Twips(851);sec.footer_distance=Twips(992)
    sp=sec._sectPr
    for old in sp.findall(qn('w:docGrid')):sp.remove(old)
    node(sp,'docGrid',type='lines',linePitch=312,charSpace=0)
    cols=sp.find(qn('w:cols'));cols.set(qn('w:num'),'1');cols.set(qn('w:space'),'425')
    # Replace python-docx default paragraph spacing, rather than accidentally inheriting it.
    styles=doc.styles.element
    for old in styles.findall(qn('w:docDefaults')):styles.remove(old)
    dd=OxmlElement('w:docDefaults');styles.insert(0,dd)
    rp=node(node(dd,'rPrDefault'),'rPr')
    node(rp,'rFonts',ascii='Times New Roman',hAnsi='Times New Roman',cs='Times New Roman',eastAsia='楷体' if lang=='zh' else 'Times New Roman')
    node(rp,'sz',val=24 if lang=='zh' else 21);node(node(node(dd,'pPrDefault'),'pPr'),'spacing',before=0,after=0)
    normal=doc.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(12 if lang=='zh' else 10.5)
    pf=normal.paragraph_format;pf.space_before=Pt(0);pf.space_after=Pt(0)
    pf.widow_control=False;pf.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    if lang=='zh':node(normal.element.get_or_add_pPr(),'spacing',line=0,lineRule='atLeast')
    # Only one clean list level: measured left override 720, hanging 442 twips.
    nr=doc.part.numbering_part.element
    for e in list(nr):nr.remove(e)
    abstract=node(nr,'abstractNum',abstractNumId=0)
    node(abstract,'multiLevelType',val='singleLevel')
    level=node(abstract,'lvl',ilvl=0);node(level,'start',val=1)
    node(level,'numFmt',val='bullet');node(level,'lvlText',val='\uf09f');node(level,'lvlJc',val='left')
    node(node(level,'pPr'),'ind',left=442,hanging=442)
    node(node(level,'rPr'),'rFonts',ascii='Wingdings',hAnsi='Wingdings')
    num=node(nr,'num',numId=1);node(num,'abstractNumId',val=0)
    for k in ['author','last_modified_by','title','subject','comments','keywords','category','identifier','version']:
        setattr(doc.core_properties,k,'')
    doc.core_properties.created=datetime.now(timezone.utc);doc.core_properties.modified=datetime.now(timezone.utc)
    doc.core_properties.revision=1
    node(doc.settings.element,'autoHyphenation',val=0)
    if lang=='zh':node(doc.settings.element,'characterSpacingControl',val='doNotCompress')
    return doc

def para(doc,text='',kind='body',lang='en',date=None,label=None):
    p=doc.add_paragraph();pp=p._p.get_or_add_pPr();pf=p.paragraph_format
    node(pp,'autoSpaceDE',val=1);node(pp,'autoSpaceDN',val=1)
    if kind=='name':
        pf.alignment=WD_ALIGN_PARAGRAPH.CENTER;pf.keep_with_next=True
        run(p,text,18,lang=='en',lang)
    elif kind in ['contact','marker']:
        pf.alignment=WD_ALIGN_PARAGRAPH.CENTER;pf.keep_with_next=True
        run(p,text,8 if kind=='marker' else None,False,lang,'555555' if kind=='marker' else '000000')
    elif kind=='section':
        pf.keep_with_next=True
        borders=node(pp,'pBdr')
        if lang=='zh':node(borders,'top',val='single',sz=4,space=1,color='000000')
        node(borders,'bottom',val='single',sz=4 if lang=='zh' else 6,space=1,color='000000')
        run(p,text,14 if lang=='zh' else 12,True,lang)
    elif kind=='entry':
        pf.keep_with_next=True
        pf.tab_stops.add_tab_stop(Twips(10772 if lang=='zh' else 9638),WD_TAB_ALIGNMENT.RIGHT)
        run(p,text,None,True,lang)
        if date:run(p,'\t'+date,None,True,lang)
    elif kind=='bullet':
        if lang=='en':
            np=node(pp,'numPr');node(np,'ilvl',val=0);node(np,'numId',val=1)
            pf.left_indent=Twips(720);pf.first_line_indent=Twips(-442)
        else:run(p,'• ',None,False,lang)
        if label:run(p,label+' ',None,True,lang)
        run(p,text,None,False,lang)
        pf.keep_together=True
    elif kind=='gap':
        run(p,'',None,False,lang)
    else:run(p,text,None,False,lang)
    return p

def save(doc,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    assert not path.exists()
    doc.save(path)
    # Do not retain even the generic library thumbnail. No source images are ever loaded.
    with zipfile.ZipFile(path) as z:members={n:z.read(n) for n in z.namelist()}
    members.pop('docProps/thumbnail.jpeg',None)
    from lxml import etree as E
    for name in ['_rels/.rels','[Content_Types].xml']:
        x=E.fromstring(members[name])
        for e in list(x):
            if 'thumbnail' in str(e.attrib) or e.get('Extension')=='jpeg':x.remove(e)
        members[name]=E.tostring(x,encoding='UTF-8',xml_declaration=True,standalone=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in members.items():z.writestr(n,v)
