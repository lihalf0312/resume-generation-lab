"""Optional local-only Chinese header images, composed with the frozen v4 renderer.

No asset discovery, network requests, school ranking, model input or implicit display.
Only the first name paragraph carries anchored images; all body paragraphs keep flowing.
"""
from pathlib import Path
from copy import deepcopy
import hashlib, io, json, os, re, warnings

VERSION = 'optional-zh-header-assets-v2-position'
MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 20_000_000
# Page-relative points within the existing Chinese header blank area, not body space.
SLOTS = {'school_logo': {'x': 28.5, 'y': 28.5, 'w': 150.0, 'h': 58.0},
         'portrait': {'x': 440.3, 'y': 22.5, 'w': 54.0, 'h': 70.0}}
ALLOWED_STAGES = {'current_student', 'recent_graduate'}

def sha_bytes(value): return hashlib.sha256(value).hexdigest()
def sha_file(path): return sha_bytes(Path(path).read_bytes())
def digest(value): return sha_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
def write(path, value): Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def local_path(value):
    if not isinstance(value,str) or re.match(r'^\w+://',value) or value.startswith(('\\\\','//')):
        raise ValueError('header_asset_requires_explicit_local_absolute_path')
    if os.name != 'nt' and re.match(r'^[A-Za-z]:[\\/]',value):
        value='/mnt/'+value[0].lower()+'/'+value[3:].replace('\\','/')
    p=Path(value)
    if not p.is_absolute(): raise ValueError('header_asset_path_must_be_absolute')
    if not p.is_file(): raise ValueError('header_asset_file_missing')
    return p.resolve()

def prepare_assets(config, language, *, allow_synthetic_test_assets=False):
    # English ignores the optional input, without opening or decoding any image.
    if language != 'zh' or not config: return []
    if not isinstance(config,dict) or set(config)-{'education_status','portrait','school_logo'}:
        raise ValueError('invalid_header_asset_options')
    from PIL import Image, ImageOps
    assets=[]
    for role in ('school_logo','portrait'):
        option=config.get(role)
        if option is None: continue
        if not isinstance(option,dict) or set(option)-{'show','path','origin','sha256','library_file_id'}:
            raise ValueError('invalid_header_asset_descriptor:'+role)
        if type(option.get('show',False)) is not bool: raise ValueError('explicit_boolean_show_required:'+role)
        if option.get('show') is not True: continue
        if role=='school_logo' and config.get('education_status') not in ALLOWED_STAGES:
            raise ValueError('school_logo_requires_user_declared_student_or_recent_graduate')
        origin=option.get('origin')
        if origin != 'user_upload' and not (allow_synthetic_test_assets and origin=='synthetic_test'):
            raise ValueError('header_asset_must_be_explicit_user_upload:'+role)
        path=local_path(option.get('path'))
        if path.stat().st_size>MAX_BYTES or path.stat().st_size==0: raise ValueError('header_asset_size_limit:'+role)
        data=path.read_bytes();original_hash=sha_bytes(data)
        if option.get('sha256') and option['sha256']!=original_hash: raise ValueError('header_asset_hash_changed:'+role)
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            try:
                with Image.open(io.BytesIO(data)) as im:
                    if im.format not in ('PNG','JPEG') or getattr(im,'n_frames',1)!=1: raise ValueError('header_asset_requires_static_png_or_jpeg:'+role)
                    if im.width*im.height>MAX_PIXELS or max(im.size)>12000: raise ValueError('header_asset_pixel_limit:'+role)
                    im.load();normalized=ImageOps.exif_transpose(im).convert('RGBA' if 'A' in im.getbands() else 'RGB')
                    pixels=normalized.size
                    normalized.info.clear()  # Do not embed source EXIF, location or comment metadata.
                    output=io.BytesIO();normalized.save(output,format='PNG')
            except (Image.DecompressionBombWarning,Image.DecompressionBombError) as exc:
                raise ValueError('header_asset_pixel_limit:'+role) from exc
        slot=SLOTS[role];scale=min(slot['w']/pixels[0],slot['h']/pixels[1]);w,h=pixels[0]*scale,pixels[1]*scale
        x=slot['x']+(slot['w']-w)/2 if role=='portrait' else slot['x']
        box=[x,slot['y'],x+w,slot['y']+h]
        assets.append({'role':role,'source_path':str(path),'source_sha256':original_hash,
          'library_file_id':option.get('library_file_id'),'origin':origin,'explicit_show':True,
          'education_status':config.get('education_status') if role=='school_logo' else None,
          'pixel_size':list(pixels),'box_pt':box,'fit':'contain_no_crop_no_distortion',
          'normalized_sha256':sha_bytes(output.getvalue()),'_png_bytes':output.getvalue(),
          'local_normalization':'EXIF orientation respected; embedded copy has no source EXIF metadata'})
    return assets

def preflight_header_assets(config, language, *, allow_synthetic_test_assets=False):
    assets=prepare_assets(config,language,allow_synthetic_test_assets=allow_synthetic_test_assets)
    return {'status':'ready' if assets else 'not_requested_or_not_applicable',
            'roles':[a['role'] for a in assets],
            'asset_set_sha256':digest({a['role']:a['source_sha256'] for a in assets}),
            'private_local_only':True,'sent_to_model':False}

def inject_docx(docx_path, assets):
    from docx import Document
    from docx.shared import Pt
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    docx_path=Path(docx_path);doc=Document(docx_path);before=[p.text for p in doc.paragraphs]
    if not doc.paragraphs: raise ValueError('header_asset_requires_name_paragraph_anchor')
    image_dir=docx_path.parent/'header-assets';image_dir.mkdir(exist_ok=False)
    for a in assets:
        path=image_dir/(a['role']+'.png');path.write_bytes(a['_png_bytes']);a['embedded_path']=str(path)
        x0,y0,x1,y1=a['box_pt'];run=doc.paragraphs[0].add_run();shape=run.add_picture(str(path),width=Pt(x1-x0),height=Pt(y1-y0))
        inline=shape._inline;anchor=OxmlElement('wp:anchor')
        for key,value in {'distT':'0','distB':'0','distL':'0','distR':'0','simplePos':'0','relativeHeight':'0','behindDoc':'0','locked':'0','layoutInCell':'1','allowOverlap':'0'}.items():anchor.set(key,value)
        simple=OxmlElement('wp:simplePos');simple.set('x','0');simple.set('y','0');anchor.append(simple)
        for tag,value in [('H',x0),('V',y0)]:
            pos=OxmlElement('wp:position'+tag);pos.set('relativeFrom','page');off=OxmlElement('wp:posOffset');off.text=str(int(round(value*12700)));pos.append(off);anchor.append(pos)
        anchor.append(deepcopy(inline.find(qn('wp:extent'))));effect=OxmlElement('wp:effectExtent')
        for key in ('l','t','r','b'):effect.set(key,'0')
        anchor.append(effect);anchor.append(OxmlElement('wp:wrapNone'))
        prop=deepcopy(inline.find(qn('wp:docPr')));prop.set('name','Optional '+a['role']);prop.set('descr','User-selected '+a['role']+' image');anchor.append(prop)
        anchor.append(deepcopy(inline.find(qn('wp:cNvGraphicFramePr'))));anchor.append(deepcopy(inline.find(qn('a:graphic'))))
        inline.getparent().replace(inline,anchor)
    doc.save(docx_path)
    if [p.text for p in Document(docx_path).paragraphs]!=before:raise ValueError('header_images_changed_document_text')
    return [{k:v for k,v in a.items() if k!='_png_bytes'} for a in assets]

def inspect_pdf(pdf_path, manifest, rows, output_dir):
    import pymupdf as fitz
    pdf=fitz.open(pdf_path);page=pdf[0];output_dir=Path(output_dir);findings=[];details=[]
    actual=page.get_image_info(xrefs=True)
    glyphs=[c for b in page.get_text('rawdict')['blocks'] for l in b.get('lines',[]) for sp in l['spans'] for c in sp['chars'] if c['c'].strip()]
    first_section=next((r['text'] for r in rows if r['kind']=='section'),None)
    hits=page.search_for(first_section) if first_section else []
    body_top=min((r.y0 for r in hits),default=None)
    if body_top is None: findings.append({'code':'header_body_boundary_unverified','route':'layout_review','blocks_current_draft':True})
    if len(actual)!=len(manifest):findings.append({'code':'unexpected_header_image_count','route':'layout_review','blocks_current_draft':True,'expected':len(manifest),'actual':len(actual)})
    for a in manifest:
        box=fitz.Rect(a['box_pt']);matches=[x for x in actual if max(abs(v-w) for v,w in zip(x['bbox'],box))<.3]
        overlaps=[c for c in glyphs if not (box & fitz.Rect(c['bbox'])).is_empty]
        in_page=box.x0>=0 and box.y0>=0 and box.x1<=page.rect.width and box.y1<=page.rect.height
        clear_body=body_top is not None and box.y1+5<=body_top
        if len(matches)!=1:findings.append({'code':'header_image_position_unverified','role':a['role'],'route':'layout_review','blocks_current_draft':True})
        if overlaps:findings.append({'code':'header_image_text_overlap','role':a['role'],'glyph_count':len(overlaps),'route':'layout_review','blocks_current_draft':True})
        if not clear_body or not in_page:findings.append({'code':'header_image_outside_available_header','role':a['role'],'route':'layout_review','blocks_current_draft':True})
        details.append({'role':a['role'],'expected_box_pt':list(box),'actual_box_pt':matches[0]['bbox'] if len(matches)==1 else None,'text_overlap_count':len(overlaps),'clear_of_body':clear_body,'inside_page':in_page,'source_sha256':a['source_sha256'],'normalized_sha256':a['normalized_sha256']})
    zoom=output_dir/'header-zoom.png';page.get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(20,20,page.rect.width-20,125),alpha=False).save(zoom)
    mechanical='passed' if not findings else 'blocked'
    findings.append({'code':'header_asset_visual_review_pending','route':'layout_review','blocks_current_draft':True,'closed':False})
    return {'status':'review_required','mechanical_status':mechanical,'pdf_sha256':sha_file(pdf_path),
            'page_count':len(pdf),'body_start_y_pt':body_top,'assets':details,
            'visual_evidence_path':str(zoom),'visual_evidence_sha256':sha_file(zoom),
            'visual_review':'pending','blocking_findings':findings,'no_body_reflow_requested':True}

def render_with_header_assets(style_module, candidate, language, directory, presentation,
                              header_assets=None, *, allow_synthetic_test_assets=False):
    assets=prepare_assets(header_assets,language,allow_synthetic_test_assets=allow_synthetic_test_assets)
    if not assets:return style_module.render_candidate(candidate,language,directory,presentation)
    if getattr(style_module,'_header_asset_render_active',False):raise ValueError('header_asset_module_instance_must_not_be_shared_concurrently')
    original=style_module.make_doc;capture={}
    def with_assets(folder,content,lang,pres=None):
        rows=original(folder,content,lang,pres);capture['rows']=rows;capture['manifest']=inject_docx(Path(folder)/'resume.docx',assets);return rows
    style_module._header_asset_render_active=True;style_module.make_doc=with_assets
    try:measurement=style_module.render_candidate(candidate,language,directory,presentation)
    finally:style_module.make_doc=original;style_module._header_asset_render_active=False
    directory=Path(directory);manifest=capture['manifest'];pdf=Path(measurement['pdf_path'])
    write(directory/'HEADER_ASSET_MANIFEST.json',{'version':VERSION,'assets':manifest,'private_local_only':True,'sent_to_model':False})
    review=inspect_pdf(pdf,manifest,capture['rows'],directory)
    write(directory/'HEADER_ASSET_REVIEW.json',review)
    measurement['header_asset_review']=review
    measurement['header_asset_set_sha256']=digest({a['role']:a['source_sha256'] for a in manifest})
    measurement['header_asset_module_sha256']=sha_file(__file__)
    measurement['base_style_fingerprint']=measurement['style_fingerprint']
    measurement['style_fingerprint']=digest({'base':measurement['base_style_fingerprint'],'module':sha_file(__file__),'version':VERSION,'slots':SLOTS,'selected_roles':[a['role'] for a in manifest]})
    write(directory/'STYLE_MEASUREMENT.json',measurement)
    return measurement

def record_visual_review(directory, expected_pdf_sha256, *, passed, note):
    """Call only after actually viewing the saved page and header zoom pixels."""
    directory=Path(directory);m=json.loads((directory/'STYLE_MEASUREMENT.json').read_text());review=m['header_asset_review']
    if sha_file(m['pdf_path'])!=expected_pdf_sha256 or review['pdf_sha256']!=expected_pdf_sha256:raise ValueError('header_visual_review_pdf_changed')
    if type(passed) is not bool or not isinstance(note,str) or not note.strip():raise ValueError('explicit_visual_result_and_note_required')
    review['visual_review']='passed' if passed else 'failed';review['visual_review_note']=note
    review['blocking_findings']=[x for x in review['blocking_findings'] if x['code']!='header_asset_visual_review_pending']
    if not passed:review['blocking_findings'].append({'code':'header_asset_visual_review_failed','route':'layout_review','blocks_current_draft':True})
    review['status']='passed' if not review['blocking_findings'] else 'blocked'
    write(directory/'HEADER_ASSET_REVIEW.json',review);write(directory/'STYLE_MEASUREMENT.json',m);return review
