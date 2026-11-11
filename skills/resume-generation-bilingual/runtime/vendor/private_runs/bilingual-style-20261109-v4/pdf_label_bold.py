"""Local same-font PDF synthetic bold for exact approved KaiTi targets.
English glyphs already using true bold faces are not thickened a second time.
"""
from pathlib import Path
import re,json,sys,hashlib
import pymupdf as fitz
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def compact(text):return ''.join(c for c in text if not c.isspace())
def page_chars(page):
    return [{'c':c['c'],'bbox':c['bbox'],'origin':c['origin'],'font':sp['font'],'size':sp['size']} for block in page.get_text('rawdict')['blocks'] for line in block.get('lines',[]) for sp in line['spans'] for c in sp['chars'] if not c['c'].isspace()]
def locate_target(doc,target):
    needle=compact(target['context_text']);primary=compact(target['text'])
    if needle.count(primary)!=1:raise ValueError('Primary must occur once in exact context')
    offset=needle.index(primary);hits=[]
    for pi,page in enumerate(doc):
        chars=page_chars(page);text=''.join(x['c'] for x in chars);start=0
        while True:
            found=text.find(needle,start)
            if found<0:break
            selected=chars[found+offset:found+offset+len(primary)]
            hits.append((pi,selected));start=found+1
    if len(hits)!=1:raise ValueError('Target context must resolve once: '+target['id'])
    pi,selected=hits[0];ys={round(x['origin'][1],1) for x in selected}
    if len(ys)!=1:raise ValueError('A primary target must fit a single measured line: '+target['id'])
    rect=fitz.Rect(selected[0]['bbox'])
    for c in selected[1:]:rect|=fitz.Rect(c['bbox'])
    kai=[c for c in selected if 'KaiTi' in c['font']]
    if not kai:raise ValueError('No KaiTi target glyphs: '+target['id'])
    return {**target,'page':pi,'bbox':list(rect),'kai_char_boxes':[list(c['bbox']) for c in kai]}
def embolden_targets(source,destination,targets):
    source,destination=Path(source),Path(destination)
    if destination.exists():raise ValueError('New destination required')
    doc=fitz.open(source);located=[locate_target(doc,x) for x in targets]
    for pi,page in enumerate(doc):
        local=[x for x in located if x['page']==pi]
        fonts={f[4]:f[3] for f in page.get_fonts(full=True)}
        counts={x['id']:0 for x in local}
        def patch(match):
            block=match.group(0)
            pos=re.search(rb'([-\d.]+) ([-\d.]+) Td\s+/(\w+) ([-\d.]+) Tf',block)
            if not pos:return block
            x,y=float(pos[1]),float(pos[2]);font=pos[3].decode();size=float(pos[4])
            if 'KaiTi' not in fonts.get(font,''):return block
            baseline=page.rect.height-y
            for target in local:
                box=fitz.Rect(target['bbox'])
                if box.x0-.2<=x<box.x1-.2 and box.y0<=baseline<=box.y1 and abs(size-target['font_size'])<.01:
                    if b' Tr' in block:raise ValueError('Existing rendering mode needs review')
                    counts[target['id']]+=1
                    stroke=round(.32*size/12,6)
                    return block.replace(b'BT',f'{stroke} w\n0 0 0 RG\nBT\n2 Tr'.encode(),1).replace(b'ET',b'0 Tr\nET',1)
            return block
        raw=page.read_contents();modified=re.sub(rb'BT\s.*?\sET',patch,raw,flags=re.S)
        if any(n<1 for n in counts.values()):raise ValueError('Unmodified target: '+repr(counts))
        xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,modified);page.set_contents(xref)
        for t in local:t['drawing_blocks_changed']=counts[t['id']]
    doc.save(destination,garbage=3,deflate=True)
    regular=fitz.open(source);bold=fitz.open(destination)
    def fingerprint(d):
        return [[(c['c'],tuple(c['origin']),c['font'],c['size']) for c in page_chars(p)] for p in d]
    assert fingerprint(regular)==fingerprint(bold),'Glyph text, positions, fonts or sizes changed'
    def font_fingerprints(d):
        return sorted({(f[3],hashlib.sha256(d.extract_font(f[0])[3]).hexdigest()) for p in d for f in p.get_fonts(full=True)})
    assert font_fingerprints(regular)==font_fingerprints(bold)
    proofs=[]
    for t in located:
        pi=t['page'];box=fitz.Rect(t['bbox'])+(-1,-1,1,1)
        a=regular[pi].get_pixmap(matrix=fitz.Matrix(4,4),clip=box,colorspace=fitz.csGRAY,alpha=False)
        b=bold[pi].get_pixmap(matrix=fitz.Matrix(4,4),clip=box,colorspace=fitz.csGRAY,alpha=False)
        ai=sum(255-x for x in a.samples);bi=sum(255-x for x in b.samples)
        assert bi>ai,'No visible ink change'
        name=t['id'].replace('#','_')
        a.save(destination.parent/f'{name}-regular.png');b.save(destination.parent/f'{name}-bold.png')
        proofs.append({**t,'page':pi+1,'regular_ink':ai,'bold_ink':bi,'increase_ratio':round(bi/ai-1,4),'unchanged_glyph_positions':True,'visibly_bold':False})
    changed=outside=0;scale=2
    for pi,(a,b) in enumerate(zip(regular,bold)):
        pa=a.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False);pb=b.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False)
        boxes=[fitz.Rect(t['bbox'])+(-1,-1,1,1) for t in located if t['page']==pi]
        for i,(va,vb) in enumerate(zip(pa.samples,pb.samples)):
            if va==vb:continue
            changed+=1;point=fitz.Point((i%pa.width+.5)/scale,(i//pa.width+.5)/scale)
            if not any(point in x for x in boxes):outside+=1
    assert outside==0,'Unexpected changes outside approved target regions'
    report={'status':'passed','evidence_kind':'pixel_ab','method':'Same embedded KaiTi glyphs with size-proportional local PDF fill+stroke; true-bold Latin faces excluded; same-text 4x pixel A/B plus visual review required','increase_ratio_definition':'bold_ink / regular_ink - 1','checked_labels':sum(t['kind']=='label' for t in proofs),'checked_headings':sum(t['kind']!='label' for t in proofs),'source_pdf_sha256':sha(source),'pdf_sha256':sha(destination),'glyph_positions_unchanged':True,'embedded_font_hashes_unchanged':True,'font_substitution':False,'font_installation':False,'double_text_overlay':False,'pixel_scope_check':{'changed_pixels':changed,'changed_pixels_outside_target_boxes':outside,'scale':scale},'labels':[t for t in proofs if t['kind']=='label'],'headings':[t for t in proofs if t['kind']!='label']}
    (destination.parent/'VISUAL_BOLD_EVIDENCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
