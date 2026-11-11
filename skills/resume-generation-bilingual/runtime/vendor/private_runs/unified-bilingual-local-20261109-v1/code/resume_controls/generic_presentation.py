"""Generic local rendering adapter over the unchanged v4 typography engine.

Target text is supplied and source-bound, never inferred from a case/person.
Known PDF-bold limitations preserve a readable PDF and explicit review blocker.
No generated facts, model clients, credentials or accounting functions.
"""
from pathlib import Path
from copy import deepcopy
import importlib.util, json, shutil, subprocess, sys, tempfile
from .common import digest, file_hash, text_hash
from .citations import locate
from .english_cjk_font import configure as configure_english_cjk, has_han

VERSION = 'generic-source-bound-presentation-product-cjk-v1'
STYLE = Path(__file__).resolve().parents[3] / 'bilingual-style-20261109-v4/style_renderer.py'


def presentation_source_gate(rendered, material, jd, receipt=None):
    payload={'document_version':rendered['candidate_version'], 'source_sha256':text_hash(material),
             'jd_sha256':text_hash(jd), 'identity':rendered.get('identity_binding'),
             'target':rendered.get('target_binding'), 'primary_names':rendered.get('stable_primary_names',{})}
    binding=digest(payload)
    valid=isinstance(receipt,dict) and set(receipt)=={
        'schema_version','binding_sha256','decision','reviewer','issues','reviewed_components'}
    if valid:
        valid=(receipt['schema_version']=='presentation-source-review-v1'
               and receipt['binding_sha256']==binding and receipt['decision']=='passed'
               and isinstance(receipt['reviewer'],str) and bool(receipt['reviewer'].strip())
               and receipt['issues']==[]
               and isinstance(receipt['reviewed_components'],list)
               and all(isinstance(x,str) for x in receipt['reviewed_components'])
               and sorted(receipt['reviewed_components'])==['identity','primary_names','target'])
    return {'binding_sha256':binding,'review_payload':payload,'passed':bool(valid),
            'receipt':deepcopy(receipt),'automatic_source_truth_certified':False,
            'reason':'explicit_matching_review' if valid else 'missing_blocked_or_mismatched_presentation_review'}


def validate_identity(doc, sidecar, material, *, generated_contract=False):
    name = doc['nodes'][0]
    binding = (sidecar or {}).get('identity')
    if not binding:
        if generated_contract:
            return {'stable_id':name['id'], 'text':name['text'],
                    'origin':'model_supplied_name_not_source_certified', 'source_review_status':'pending'}
        raise ValueError('explicit_identity_source_binding_required')
    if binding.get('text') != name['text'] or binding.get('stable_id',name['id']) != name['id']:
        raise ValueError('identity_binding_does_not_match_candidate')
    refs=binding.get('source_refs',[])
    if not refs: raise ValueError('identity_personal_source_reference_required')
    locations=[]
    for ref in refs:
        location=locate(material,ref,'')
        if location['status']!='unique': raise ValueError('identity_reference_not_unique_personal_material')
        selected=ref.get('quote') or location['matches'][0]['text']
        if name['text'] not in selected: raise ValueError('identity_name_not_explicitly_supplied_in_source')
        locations.append(location)
    return {**deepcopy(binding), 'stable_id':name['id'], 'source_locations':locations,
            'origin':'explicit_source_supplied_name', 'source_review_status':'pending'}


def normalize_sidecar(doc, sidecar=None, *, allowed_versions=()):
    """Accept stable IDs directly; positional keys are a compatibility import."""
    from .unified import paths
    result = deepcopy(sidecar or {}); mapping = paths(doc); reverse = {v:k for k,v in mapping.items()}
    for field in ['bullet_labels', 'entry_primary', 'bullet_breaks', 'heading_breaks']:
        direct = result.pop('stable_' + field, {})
        source = list(result.get(field, {}).items()) + list(direct.items())
        normalized = {}
        for key, value in source:
            rid = reverse.get(key, key)
            if rid not in mapping: raise ValueError('presentation_unknown_stable_or_positional_id:' + key)
            if rid in normalized: raise ValueError('presentation_duplicate_node_binding:' + key)
            normalized[rid] = deepcopy(value)
        result[field] = normalized
    bound = result.get('candidate_version')
    if bound:
        from .document import version
        if bound not in {version(doc), *allowed_versions}: raise ValueError('presentation_candidate_version_changed')
    return result


def validate_target(binding, jd_text):
    if not isinstance(binding, dict): raise ValueError('explicit_source_bound_target_role_required')
    text, literal = binding.get('text'), binding.get('source_text')
    if (not isinstance(text, str) or not text.strip() or text != text.strip() or len(text)>160
            or '\n' in text or '\r' in text or not isinstance(literal,str) or not literal.strip()):
        raise ValueError('target_role_text_or_source_phrase_invalid')
    refs = binding.get('source_refs')
    if not isinstance(refs, list) or not refs: raise ValueError('target_role_JD_reference_required')
    locations=[]
    for ref in refs:
        if not isinstance(ref,dict) or not ref.get('source_id','').startswith('JD:'):
            raise ValueError('target_role_must_reference_JD_not_personal_qualification')
        location=locate('', ref, jd_text, personal=False)
        if location['status']!='unique': raise ValueError('target_role_JD_reference_not_unique')
        selected=ref.get('quote') or location['matches'][0]['text']
        if literal not in selected: raise ValueError('target_role_source_phrase_not_in_selected_JD_evidence')
        locations.append(location)
    if text != literal and binding.get('translation_basis') != 'explicit_descriptive_translation':
        raise ValueError('target_role_translation_must_be_explicit_not_guessed')
    return {**deepcopy(binding), 'source_locations':locations, 'jd_sha256':text_hash(jd_text),
            'role':'application_intent_not_personal_fact', 'automatic_semantic_certification':False}


def load_style(target, *, document_kind='synthetic_development'):
    if document_kind not in ('synthetic_development','user_resume'):
        raise ValueError('explicit_document_kind_required')
    spec=importlib.util.spec_from_file_location('generic_v4_local_instance',STYLE)
    module=importlib.util.module_from_spec(spec)
    sys.path.insert(0,str(STYLE.parent));spec.loader.exec_module(module)
    original_rows=module.rows_from_candidate
    original_fingerprint=module.style_fingerprint
    original_make_doc=module.make_doc
    def rows(candidate,lang,presentation=None):
        content=original_rows(candidate,lang,presentation)
        content['target_role']=target['text']
        return content
    module.rows_from_candidate=rows
    module.style_fingerprint=lambda:digest({'base_style':original_fingerprint(),
        'adapter_sha256':file_hash(__file__),'version':VERSION,'document_kind':document_kind,
        'native_backend':module.engine.backend_name(),
        'native_runtime_sha256':file_hash(module.BASE/'tools/native_runtime.py'),
        'native_typography_sha256':file_hash(module.BASE/'tools/native_typography.py'),
        'native_bold_sha256':file_hash(module.BASE/'tools/native_bold.py'),
        'native_word_export_sha256':file_hash(module.BASE/'tools/word_export.py'),
        'english_cjk_policy_sha256':file_hash(Path(__file__).with_name('english_cjk_font.py'))})
    def make_doc(folder, content, lang, presentation=None):
        rows=original_make_doc(folder,content,lang,presentation)
        if document_kind=='user_resume':
            from docx import Document
            doc=Document(folder/'resume.docx')
            indices=[i for i,row in enumerate(rows) if row['kind']=='marker']
            for i in reversed(indices):
                paragraph=doc.paragraphs[i]._element;paragraph.getparent().remove(paragraph)
            rows=[row for row in rows if row['kind']!='marker']
            doc.save(folder/'resume.docx')
            (folder/'content.json').write_text(json.dumps({'paragraphs':rows},ensure_ascii=False,indent=2),encoding='utf-8')
            (folder/'docx-body.txt').write_text('\n'.join(p.text for p in doc.paragraphs)+'\n',encoding='utf-8')
        if lang=='en':
            module.save(folder/'ENGLISH-CJK-FONT-POLICY.json',configure_english_cjk(folder/'resume.docx'))
        if lang=='zh' and module.engine.backend_name()=='word':
            from native_typography import apply_word_section_borders
            module.save(folder/'NATIVE-SECTION-SEPARATORS.json',apply_word_section_borders(folder/'resume.docx',rows))
        return rows
    module.make_doc=make_doc
    def render(candidate,lang,output_dir,presentation=None):
        folder=Path(output_dir).resolve();folder.mkdir(parents=True,exist_ok=False)
        content=module.rows_from_candidate(candidate,lang,presentation)
        module.save(folder/'candidate.json',candidate);module.save(folder/'presentation.json',presentation or {})
        module.save(folder/'target-binding.json',target)
        module.save(folder/'environment.json',module.engine.check_environment())
        module.save(folder/'PRESENTATION_NORMALIZATIONS.json',content['presentation_normalizations'])
        actual_rows=module.make_doc(folder,content,lang,presentation)
        attempt=folder/'attempt-01';attempt.mkdir()
        proc=module.engine.convert_docx(folder/'resume.docx',attempt)
        module.save(attempt/'process.json',{'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
        pdf=attempt/'resume.pdf'
        if proc.returncode or not pdf.exists():raise ValueError('fixed_renderer_failed_no_retry')
        bold=None;blockers=[];native_bold_targets=[]
        if lang=='zh' or any(has_han(row['text']) for row in actual_rows):
            helper_spec=importlib.util.spec_from_file_location('generic_bold_helper',STYLE.parent/'pdf_label_bold.py')
            helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
            targets=[]
            for row in actual_rows:
                if row.get('label'):
                    # Full exact row context distinguishes repeated topical labels.
                    targets.append({'id':row['id'],'kind':'label','text':row['label'],
                                    'context_text':row['label']+' '+row['text'],'font_size':12 if lang=='zh' else 10.5})
                elif row['kind']=='section':
                    targets.append({'id':row['id'],'kind':'section','text':row['text'],
                                    'context_text':row['text'],'font_size':14 if lang=='zh' else 12})
                elif row.get('entry_emphasis') and row['entry_emphasis']['text'] in row['text']:
                    targets.append({'id':row.get('source_id',row['id']),'kind':'entry_primary',
                                    'text':row['entry_emphasis']['text'],'context_text':row['text'],'font_size':12 if lang=='zh' else 10.5})
                elif row['kind']=='name' and lang=='en' and has_han(row['text']):
                    targets.append({'id':row['id'],'kind':'name','text':row['text'],'context_text':row['text'],'font_size':18})
            # Word exports its own KaiTi bold. The old PDF helper recognizes
            # LibreOffice stream syntax only and would risk thickening it twice.
            # Native bold remains an explicit visual review target, never auto-pass.
            native_bold_targets=[t for t in targets if not has_han(t['text']) or module.engine.backend_name()=='word']
            targets=[t for t in targets if t not in native_bold_targets]
            if targets:
                pdf.rename(attempt/'resume-regular.pdf')
                try:
                    bold=helper.embolden_targets(attempt/'resume-regular.pdf',pdf,targets)
                    bold['evidence_path']=str(attempt/'VISUAL_BOLD_EVIDENCE.json')
                    for entry in bold.get('labels',[]):
                        entry['regular_image_path']=str(attempt/(entry['id'].replace('#','_')+'-regular.png'))
                        entry['bold_image_path']=str(attempt/(entry['id'].replace('#','_')+'-bold.png'))
                    # Fresh pixel evidence is still visually unreviewed.
                    (attempt/'VISUAL_BOLD_EVIDENCE.json').write_text(json.dumps(bold,ensure_ascii=False,indent=2),encoding='utf-8')
                except (ValueError,AssertionError) as exc:
                    if pdf.exists():pdf.rename(attempt/'resume-bold-unverified.pdf')
                    shutil.copyfile(attempt/'resume-regular.pdf',pdf)
                    blockers.append({'route':'layout_review','code':'generic_bold_requires_review',
                        'reason':str(exc),'closed':False,'blocks_current_draft':True,
                        'preserved_regular_pdf':True,'text_not_rewritten':True})
                    module.save(attempt/'BOLD-REVIEW-REQUIRED.json',blockers)
        if module.engine.backend_name()=='word':
            from native_bold import measure as measure_native_bold
            try:
                bold=measure_native_bold(pdf,actual_rows,attempt,lang)
            except (ValueError,AssertionError) as exc:
                blockers.append({'route':'layout_review','code':'native_bold_requires_review',
                    'reason':str(exc),'closed':False,'blocks_current_draft':True,
                    'original_word_pdf_preserved':True,'text_not_rewritten':True})
                module.save(attempt/'NATIVE-BOLD-REVIEW-REQUIRED.json',blockers)
        measurement=module.engine.measure(folder/'resume.docx',pdf,actual_rows,lang,attempt)
        if lang=='zh':
            from native_typography import separator_collisions
            collisions=separator_collisions(pdf)
            measurement['section_separator_collisions']=collisions
            blockers.extend(collisions['blocking_findings'])
            alignment=module.measure_chinese_label_alignment(pdf,folder/'resume.docx',actual_rows)
            measurement['chinese_label_alignment']=alignment
            blockers.extend(alignment.get('blocking_findings',[]))
        if bold:measurement['visual_bold']=bold
        measurement.update(pdf_path=str(pdf),presentation_normalizations=content['presentation_normalizations'],
            render_backend=module.engine.backend_name(),native_word_export_verified=module.engine.backend_name()=='word',ats_verified=False,
            style_version=VERSION,style_fingerprint=module.style_fingerprint(),
            typography_fingerprint=module.typography_fingerprint(),new_API_calls=0,visual_review='pending',
            generic_render_findings=blockers,target_binding=target,document_kind=document_kind)
        measurement['native_non_CJK_bold_targets']={'targets':native_bold_targets,
            'status':'visual_review_pending' if native_bold_targets else 'not_applicable',
            'note':'Native bold runs retained; Word KaiTi is not processed by the LibreOffice-only outline helper; visual review is still required, never font-flag-only acceptance.'}
        module.save(folder/'STYLE_MEASUREMENT.json',measurement)
        return measurement
    module.render_candidate=render
    return module
