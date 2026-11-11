"""Explicit existing KaiTi for Han in English documents; Latin keeps its face."""

def has_han(text):
    return any('\u3400'<=c<='\u9fff' or '\uf900'<=c<='\ufaff' or '\U00020000'<=c<='\U0002fa1f' for c in text)

def configure(path):
    from docx import Document
    from docx.oxml.ns import qn
    doc=Document(path);before=[p.text for p in doc.paragraphs];changes=[]
    for pi,p in enumerate(doc.paragraphs):
        for ri,r in enumerate(p.runs):
            if not has_han(r.text):continue
            fonts=r._element.get_or_add_rPr().get_or_add_rFonts()
            prior=fonts.get(qn('w:eastAsia'))
            latin={k:fonts.get(qn('w:'+k)) for k in ('ascii','hAnsi','cs')}
            fonts.set(qn('w:eastAsia'),'楷体')
            assert latin=={k:fonts.get(qn('w:'+k)) for k in latin}
            changes.append({'paragraph':pi,'run':ri,'text':r.text,'eastAsia_before':prior,
                'eastAsia_after':'楷体','latin_faces_unchanged':latin,'font_size_pt':r.font.size.pt if r.font.size else None})
    assert [p.text for p in doc.paragraphs]==before
    if changes:doc.save(path)
    return {'policy':'existing_KaiTi_for_Han_English_v1','changes':changes,'text_unchanged':True,
            'font_installation':False,'allowed_font_list_changed':False,'latin_fonts_or_sizes_changed':False}
