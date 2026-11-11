"""Carry explicit language-name inputs through stages; do not certify names."""
from copy import deepcopy
from resume_controls.common import digest

def attach_language_context(request,source,language,bindings=None):
    from language_completeness import build_language_context,language_output_guidance,OPTIONAL_INPUT_GUIDANCE
    q=deepcopy(request);q.pop('input_sha256',None)
    contract=build_language_context(source,language,bindings)
    current=q['context'].get('language_input_contract')
    if current is not None and current!=contract:raise ValueError('language_contract_changed_between_stages')
    q['context']['language_input_contract']=contract
    q['context']['language_bindings']=deepcopy(bindings)
    for guide in (language_output_guidance(language),OPTIONAL_INPUT_GUIDANCE):
        if guide not in q['context']['rules']:q['context']['rules']+='\n'+guide
    return {**q,'input_sha256':digest(q)}

def language_audit(document,source,language,bindings=None):
    from language_completeness import audit_language
    return audit_language(document,source,language,bindings)

def presentation_name_evidence(binding):
    """Keep name evidence separate from evidence about the holder's experience.

    The complete source and all refs remain in the language binding and PATCH.
    A primary-name display reference must actually contain the chosen name, or
    explicitly record an already-authorized translation rather than imply it was
    literal source text. This helper does not approve a name or certify a source.
    """
    literal=[r for r in binding['source_refs'] if binding['output_text'] in r.get('quote','')]
    if literal:return {'source_refs':deepcopy(literal)}
    if binding['authority'] in ('user_approved_transliteration','user_approved_descriptive',
            'user_confirmed_official','verified_official'):
        return {'source_refs':deepcopy(binding['source_refs']),
                'translation_basis':'explicit_descriptive_translation'}
    raise ValueError('name_display_requires_literal_or_explicit_authorized_translation')

def apply_name_bindings(source,language,generation,raw_document,basis,*,bindings,directory,
                        target_role,presentation,origin='offline_editor_revision',review_stage=None,provenance=None,document_kind='synthetic_development'):
    """Local exact name substitution, never a model call or source approval.

The caller supplies the explicit name choices and source-bound identity/primary
presentation. Auxiliary text is preserved and included in the next complete
review, so an old selection note cannot silently become approved after renaming.
"""
    from pathlib import Path
    import product as p
    from resume_controls import document as d
    from resume_controls.patches import apply_patch
    from language_completeness import build_language_patch
    from workflow_v3 import preview
    p.validate_source(source);d.validate(raw_document)
    if raw_document['language']!=language or d.to_resume(raw_document)!=generation['resume']:
        raise ValueError('name_binding_snapshot_mismatch')
    patch=build_language_patch(raw_document,source,bindings)
    root=Path(directory);p.create_evidence_dir(root)
    p.save(root/'LANGUAGE-BINDINGS.json',bindings)
    p.save(root/'LANGUAGE-PRECHECK-BEFORE.json',language_audit(raw_document,source,language,bindings))
    revised=deepcopy(raw_document);audit=None
    if patch:
        p.save(root/'NAME-PATCH.json',patch)
        revised,audit=apply_patch(raw_document,patch,source['material_text'],source['jd_text'])
        p.save(root/'NAME-PATCH-AUDIT.json',audit)
    updated=deepcopy(generation);updated['resume']=d.to_resume(revised)
    sidecar=deepcopy(presentation or {})
    if sidecar.get('candidate_version') not in (None,d.version(raw_document)):
        raise ValueError('name_binding_presentation_version_mismatch')
    if 'candidate_version' in sidecar:sidecar['candidate_version']=d.version(revised)
    nodes={n['id']:n for n in revised['nodes']}
    for ident,rule in sidecar.get('stable_entry_primary',{}).items():
        matches=[b for b in bindings.get('entries',[]) if ident in b['unit_ids'] and b['source_text']==rule['text']]
        if matches:
            b=matches[0];rule.pop('translation_basis',None)
            rule.update(text=b['output_text'],source_text=nodes[ident]['text'],**presentation_name_evidence(b),
                language_authority=b['authority'],official_name_claimed=b['authority'] in ('source_declared_official','user_confirmed_official','verified_official'))
    identity=sidecar.get('identity')
    if identity:
        ident=identity.get('stable_id',raw_document['nodes'][0]['id'])
        matches=[b for b in bindings.get('entries',[]) if ident in b['unit_ids'] and b['source_text']==identity['text']]
        if matches:
            identity.pop('translation_basis',None)
            identity.update(text=matches[0]['output_text'],**presentation_name_evidence(matches[0]))
    p.save(root/'UPDATED-PRESENTATION.json',sidecar)
    p.save(root/'NAME-TRANSFORM-LINEAGE.json',{'origin':origin,'before_version':d.version(raw_document),
        'after_version':d.version(revised),'source_case_sha256':p.digest(source),'new_model_API_calls':0,
        'only_explicit_name_substitutions':True,'auxiliary_fields_unchanged':True,
        'full_source_and_visual_reviews_required':True,'official_names_automatically_certified':False})
    return preview(source,language,updated,directory=root/'deliverable',target_role=target_role,basis=basis,
        origin=origin,initial_document=revised,presentation=sidecar,language_bindings=bindings,
        review_stage=review_stage,document_kind=document_kind,provenance={'prior_provenance':deepcopy(provenance),'local_name_patch_sha256':p.digest(patch),
            'new_model_API_calls':0,'not_a_new_model_response':True,'official_names_automatically_certified':False})
