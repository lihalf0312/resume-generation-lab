"""Evidence for Word's existing bold; never thickens or edits the output PDF.

KaiTi: create a diagnostic copy with only the exact Word stroke runs turned
off, verify identical glyphs/fonts/positions and compare same-box pixels.
Latin: verify each actual glyph uses the embedded bold face and retain crops.
Neither route marks visibly_bold true: that requires review of the actual crop.
"""
from pathlib import Path
import hashlib,json,re
import pymupdf as fitz

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def compact(text):return ''.join(c for c in text if not c.isspace())

def targets_from_rows(rows):
    result=[]
    for row in rows:
        if row.get('label'):
            result.append({'id':row['id'],'kind':'label','text':row['label'],
                           'context_text':row['label']+' '+row['text']})
        elif row['kind']=='section':
            result.append({'id':row['id'],'kind':'section','text':row['text'],'context_text':row['text']})
        elif row.get('entry_emphasis') and row['entry_emphasis']['text'] in row['text']:
            result.append({'id':row.get('source_id',row['id']),'kind':'entry_primary',
                           'text':row['entry_emphasis']['text'],'context_text':row['text']})
    return result

def page_chars(page):
    return [{'c':c['c'],'bbox':c['bbox'],'origin':c['origin'],'font':span['font'],'size':span['size']}
            for block in page.get_text('rawdict')['blocks'] for line in block.get('lines',[])
            for span in line['spans'] for c in span['chars'] if not c['c'].isspace()]

def locate(pdf,target):
    needle=compact(target['context_text']);primary=compact(target['text'])
    if needle.count(primary)!=1:raise ValueError('native_bold_target_not_unique_in_context:'+target['id'])
    offset=needle.index(primary);hits=[]
    for page_number,page in enumerate(pdf):
        if target['kind']=='section':
            for block in page.get_text('rawdict')['blocks']:
                for line in block.get('lines',[]):
                    chars=[{'c':c['c'],'bbox':c['bbox'],'origin':c['origin'],'font':span['font'],'size':span['size']}
                           for span in line['spans'] for c in span['chars'] if not c['c'].isspace()]
                    if ''.join(c['c'] for c in chars)==needle:
                        hits.append((page_number,chars[offset:offset+len(primary)]))
            continue
        chars=page_chars(page);hay=''.join(x['c'] for x in chars);start=0
        while True:
            at=hay.find(needle,start)
            if at<0:break
            hits.append((page_number,chars[at+offset:at+offset+len(primary)]));start=at+1
    if len(hits)!=1:raise ValueError('native_bold_target_context_not_unique:'+target['id'])
    index,selected=hits[0]
    if len({round(c['origin'][1],1) for c in selected})!=1:
        raise ValueError('native_bold_target_wrap_requires_review:'+target['id'])
    box=fitz.Rect(selected[0]['bbox'])
    for char in selected[1:]:box|=fitz.Rect(char['bbox'])
    return {**target,'page':index+1,'bbox':list(box),'glyph_fonts':sorted({c['font'] for c in selected}),
            'actual_glyph_sizes':sorted({c['size'] for c in selected})}

def _font_hashes(pdf):
    result={}
    for page in pdf:
        for font in page.get_fonts(full=True):
            data=pdf.extract_font(font[0])[3]
            if not data:raise ValueError('native_bold_unembedded_font:'+font[3])
            result[font[3].split('+')[-1]]=hashlib.sha256(data).hexdigest()
    return result

def _crop(pdf,target,path):
    pix=pdf[target['page']-1].get_pixmap(matrix=fitz.Matrix(4,4),
        clip=fitz.Rect(target['bbox'])+(-1,-1,1,1),colorspace=fitz.csGRAY,alpha=False)
    pix.save(path)
    return sum(255-x for x in pix.samples)

def measure(pdf_path,rows,output_dir,language):
    source=Path(pdf_path);out=Path(output_dir);source_hash=sha(source)
    if (out/'VISUAL_BOLD_EVIDENCE.json').exists():raise ValueError('native_bold_evidence_already_exists')
    targets=targets_from_rows(rows)
    with fitz.open(source) as actual:
        located=[locate(actual,t) for t in targets];font_hashes=_font_hashes(actual)
        if language=='en':
            proofs=[]
            for target in located:
                fonts=target['glyph_fonts']
                if len(fonts)!=1 or 'Bold' not in fonts[0] or fonts[0] not in font_hashes:
                    raise ValueError('native_english_bold_face_requires_review:'+target['id'])
                crop=out/(target['id'].replace('#','_')+'-native-bold.png')
                ink=_crop(actual,target,crop)
                proofs.append({**target,'embedded_bold_face':True,'embedded_font_sha256':font_hashes[fonts[0]],
                    'visual_evidence_path':str(crop),'visual_evidence_sha256':sha(crop),'bold_ink':ink,
                    'visibly_bold':False,'visual_review':'pending'})
            report={'status':'passed','evidence_kind':'embedded_bold_with_visual_inspection',
                'method':'Every actual target glyph uses the embedded Times New Roman bold face; retain same-PDF crop for mandatory visual inspection.',
                'labels':[t for t in proofs if t['kind']=='label'],'headings':[t for t in proofs if t['kind']!='label']}
        else:
            regular_path=out/'resume-native-regular-diagnostic.pdf'
            if regular_path.exists():raise ValueError('native_regular_diagnostic_already_exists')
            diagnostic=fitz.open(source);changed_counts={t['id']:0 for t in located}
            for index,page in enumerate(diagnostic):
                local=[t for t in located if t['page']==index+1]
                resources={f[4]:f[3] for f in page.get_fonts(full=True)}
                def remove_stroke(match):
                    block=match.group(0)
                    face=re.search(rb'/(\w+)\s+([-\d.]+)\s+Tf',block)
                    matrix=re.search(rb'1\s+0\s+0\s+1\s+([-\d.]+)\s+([-\d.]+)\s+Tm',block)
                    if not face or not matrix or b'2 Tr' not in block:return block
                    if 'KaiTi' not in resources.get(face[1].decode(),''):return block
                    x,y=float(matrix[1]),page.rect.height-float(matrix[2]);size=float(face[2])
                    matching=[t for t in local if fitz.Rect(t['bbox']).x0-.2<=x<fitz.Rect(t['bbox']).x1-.2
                              and fitz.Rect(t['bbox']).y0<=y<=fitz.Rect(t['bbox']).y1
                              and any(abs(size-s)<.1 for s in t['actual_glyph_sizes'])]
                    if len(matching)>1:raise ValueError('native_bold_ambiguous_stroke_block')
                    if not matching:return block
                    if len(re.findall(rb'\b2 Tr\b',block))!=1:raise ValueError('native_bold_unknown_stream_syntax')
                    changed_counts[matching[0]['id']]+=1
                    return block.replace(b'2 Tr',b'0 Tr',1)
                raw=page.read_contents();modified=re.sub(rb'BT\s.*?\sET',remove_stroke,raw,flags=re.S)
                xref=diagnostic.get_new_xref();diagnostic.update_object(xref,'<<>>');diagnostic.update_stream(xref,modified);page.set_contents(xref)
            if any(count<1 for count in changed_counts.values()):raise ValueError('native_bold_target_without_known_stroke:'+repr(changed_counts))
            diagnostic.save(regular_path,garbage=3,deflate=True);diagnostic.close()
            with fitz.open(regular_path) as regular:
                fingerprint=lambda pdf:[[(c['c'],tuple(c['origin']),c['font'],c['size']) for c in page_chars(p)] for p in pdf]
                if fingerprint(actual)!=fingerprint(regular):raise ValueError('native_diagnostic_glyph_positions_changed')
                if font_hashes!=_font_hashes(regular):raise ValueError('native_diagnostic_embedded_fonts_changed')
                proofs=[]
                for target in located:
                    name=target['id'].replace('#','_');a=out/(name+'-native-regular.png');b=out/(name+'-native-bold.png')
                    regular_ink=_crop(regular,target,a);bold_ink=_crop(actual,target,b)
                    if not bold_ink>regular_ink>0:raise ValueError('native_bold_no_same_text_ink_increase:'+target['id'])
                    proofs.append({**target,'regular_image_path':str(a),'bold_image_path':str(b),
                        'regular_ink':regular_ink,'bold_ink':bold_ink,'increase_ratio':bold_ink/regular_ink-1,
                        'unchanged_glyph_positions':True,'known_stroke_blocks':changed_counts[target['id']],
                        'visibly_bold':False,'visual_review':'pending'})
                changed=outside=0
                for index,(a,b) in enumerate(zip(regular,actual)):
                    boxes=[fitz.Rect(t['bbox'])+(-1,-1,1,1) for t in located if t['page']==index+1]
                    pa=a.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY,alpha=False)
                    pb=b.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY,alpha=False)
                    for i,(va,vb) in enumerate(zip(pa.samples,pb.samples)):
                        if va==vb:continue
                        changed+=1;point=fitz.Point((i%pa.width+.5)/2,(i//pa.width+.5)/2)
                        if not any(point in box for box in boxes):outside+=1
                if outside:raise ValueError('native_bold_diagnostic_changed_pixels_outside_targets')
            report={'status':'passed','evidence_kind':'pixel_ab',
                'method':'Unmodified Word output vs diagnostic copy with only exact KaiTi target stroke modes disabled; same-text 4x pixel A/B, identical glyph positions and embedded fonts; visual review required.',
                'source_pdf_sha256':sha(regular_path),'diagnostic_pdf':str(regular_path),'glyph_positions_unchanged':True,
                'embedded_font_hashes_unchanged':True,'pixel_scope_check':{'changed_pixels':changed,'changed_pixels_outside_target_boxes':outside,'scale':2},
                'labels':[t for t in proofs if t['kind']=='label'],'headings':[t for t in proofs if t['kind']!='label']}
    if sha(source)!=source_hash:raise AssertionError('Original Word PDF was changed')
    report.update(pdf_sha256=source_hash,checked_labels=len(report['labels']),checked_headings=len(report['headings']),
                  output_pdf_changed=False,font_substitution=False,visual_review='pending',
                  evidence_path=str(out/'VISUAL_BOLD_EVIDENCE.json'))
    (out/'VISUAL_BOLD_EVIDENCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
