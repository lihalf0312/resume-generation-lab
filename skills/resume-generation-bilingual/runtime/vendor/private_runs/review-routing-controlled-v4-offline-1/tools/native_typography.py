"""Word-only stable section separators. A new layout, never prior acceptance."""
from pathlib import Path
import hashlib
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

def separator_collisions(pdf_path):
    """Conservative line-through-glyph diagnostic; not a visual approval."""
    import pymupdf as fitz
    findings=[]
    with fitz.open(pdf_path) as pdf:
        for index,page in enumerate(pdf):
            lines=[]
            for drawing in page.get_drawings():
                for item in drawing.get('items',[]):
                    if item[0]=='l':
                        a,b=item[1],item[2]
                        if abs(a.y-b.y)<1 and abs(a.x-b.x)>100:
                            lines.append((min(a.x,b.x),max(a.x,b.x),(a.y+b.y)/2))
            for x0,x1,y in lines:
                hits=[]
                for block in page.get_text('rawdict')['blocks']:
                    for line in block.get('lines',[]):
                        for span in line['spans']:
                            for char in span['chars']:
                                if not char['c'].strip():continue
                                a,b,c,d=char['bbox']
                                if c>x0 and a<x1 and b+(d-b)*0.2<y<d-(d-b)*0.2:
                                    hits.append(char['c'])
                if hits:
                    findings.append({'page':index+1,'line':[x0,y,x1,y],'intersected_text':''.join(hits)})
    return {'method':'Long horizontal PDF paths intersecting the central 60 percent of non-whitespace glyph boxes',
            'findings':findings,'visual_review_still_required':True,
            'blocking_findings':[{'route':'layout_review','code':'separator_intersects_text','closed':False,
                                 'blocks_current_draft':True,**x} for x in findings]}

def apply_word_section_borders(path, rows):
    path=Path(path)
    document=Document(path)
    if len(document.paragraphs)!=len(rows):
        raise ValueError('Exact row/paragraph correspondence required for native separators.')
    before=[p.text for p in document.paragraphs]
    records=[]
    for row,paragraph in zip(rows,document.paragraphs):
        if row['kind']!='section':continue
        removed=0
        for run in list(paragraph._p):
            if run.tag!=qn('w:r'):continue
            for child in list(run):
                if child.tag.endswith('}AlternateContent'):
                    # Only remove the already-known section line drawings.
                    drawings=list(child.iter(qn('wp:docPr')))
                    if drawings and all(x.get('name','').startswith('Section line ') for x in drawings):
                        run.remove(child);removed+=1
            if len(run)==0:paragraph._p.remove(run)
        if removed!=2:
            raise ValueError('Expected exactly two known section separator drawings, found '+str(removed))
        props=paragraph._p.get_or_add_pPr()
        for old in list(props):
            if old.tag==qn('w:pBdr'):props.remove(old)
        borders=OxmlElement('w:pBdr')
        for name in ('top','bottom'):
            edge=OxmlElement('w:'+name)
            for attribute,value in {'val':'single','sz':'4','space':'2','color':'000000'}.items():
                edge.set(qn('w:'+attribute),value)
            borders.append(edge)
        props.append(borders)
        paragraph.paragraph_format.space_before=Pt(6)
        paragraph.paragraph_format.space_after=Pt(6)
        paragraph.paragraph_format.keep_with_next=True
        records.append({'id':row['id'],'removed_floating_lines':removed,
                        'top_and_bottom_border_pt':0.5,'border_gap_pt':2,
                        'space_before_pt':6,'space_after_pt':6})
    if before!=[p.text for p in document.paragraphs]:
        raise AssertionError('Native separator adaptation changed text.')
    document.save(path)
    return {'schema':'native-word-section-separators-v1','backend':'word',
            'sections':records,'text_preserved':True,'font_sizes_preserved':True,
            'page_geometry_preserved':True,'prior_visual_acceptance_reusable':False,
            'native_visual_review':'pending','module_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
