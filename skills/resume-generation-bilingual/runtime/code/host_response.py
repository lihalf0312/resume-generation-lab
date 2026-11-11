"""Receive caller-declared host output. No model/transport/billing verification."""
from pathlib import Path
from copy import deepcopy
from resume_controls.schemas import obj,HASH,validate
from resume_controls.common import create_evidence_dir,digest,text_hash,save,save_evidence_bytes

VERSION='host-assisted-response-binding-v1'
ORIGIN='host_assisted'
SCHEMA=obj({'schema_version':{'const':VERSION},'origin':{'const':ORIGIN},
    'request_sha256':HASH,'request_file_sha256':HASH,'response_sha256':HASH,
    'source_case_sha256':HASH,'language':{'enum':['en','zh']},
    'generation_mode':{'enum':['full','compact_experimental']},
    'verification':{'const':'caller_declaration_and_file_consistency_only'}})

def declaration(source,language,request_text,response_text,*,mode='full'):
    import product as p
    if not isinstance(request_text,str) or not isinstance(response_text,str):raise ValueError('exact_utf8_request_and_response_text_required')
    request=p.strict_json(request_text)
    p.validate_prepared(request,source,language,mode=mode)
    # Do not parse/coerce a bad response here. The normal strict intake keeps
    # its original bytes and reports a readable needs_response_review result.
    return {'schema_version':VERSION,'origin':ORIGIN,'request_sha256':request['input_sha256'],
        'request_file_sha256':text_hash(request_text),'response_sha256':text_hash(response_text),
        'source_case_sha256':digest(source),'language':language,'generation_mode':mode,
        'verification':'caller_declaration_and_file_consistency_only'}

def _write_inputs(root,request_text,response_text,binding):
    create_evidence_dir(root)
    for name,value in (('REQUEST.json',request_text),('RESPONSE.txt',response_text)):
        save_evidence_bytes(root/name,value.encode('utf-8'))
    save(root/'HOST-DECLARATION.json',binding)

def bind(source,language,*,request_text,response_text,directory,mode='full'):
    """Explicit local caller declaration; never fabricates a provider receipt."""
    root=Path(directory);binding=declaration(source,language,request_text,response_text,mode=mode)
    _write_inputs(root,request_text,response_text,binding)
    notice={'origin':ORIGIN,'binding':str(root/'HOST-DECLARATION.json'),
        'request':str(root/'REQUEST.json'),'response':str(root/'RESPONSE.txt'),
        'request_actually_seen_by_host_verified':False,'model_identity_verified':False,
        'API_transport_verified':False,'billing_verified':False,'new_API_calls':0,
        'meaning':'Caller declared these files belong together. Hash equality proves only file consistency, not who generated the response.'}
    save(root/'BINDING-NOTICE.json',notice);return notice

def consume(source,language,*,request_text,response_text,declaration_text,directory,target_role,
            mode='full',presentation=None,header_assets=None,renderer=None,review_receipt=None):
    import product as p
    import workflow_v3 as w
    binding=p.strict_json(declaration_text);validate(SCHEMA,binding)
    expected=declaration(source,language,request_text,response_text,mode=mode)
    if binding!=expected:raise ValueError('host_source_request_response_or_origin_binding_mismatch')
    p.validate_target(target_role,source['jd_text'])
    request=p.strict_json(request_text);root=Path(directory)
    _write_inputs(root,request_text,response_text,binding)
    provenance={'origin':ORIGIN,'caller_declaration':deepcopy(binding),
        'prepared_context_matches_source_language_mode':True,'supplied_file_hashes_match':True,
        'request_actually_seen_by_host_verified':False,'model_identity_verified':False,
        'API_transport_verified':False,'billing_verified':False,'new_API_calls':0,
        'manual_content_cannot_be_promoted_to_verified_model_output':True}
    save(root/'HOST-PROVENANCE.json',provenance)
    result=w.preview(source,language,response_text,directory=root/'deliverable',target_role=target_role,
        basis=request['context']['runtime_date_basis'],origin=ORIGIN,provenance=provenance,
        presentation=presentation,header_assets=header_assets,renderer=renderer,review_receipt=review_receipt,
        language_bindings=request['context'].get('language_bindings'),document_kind='user_resume')
    result.update(host_assisted_origin=ORIGIN,host_identity_and_transport_verified=False,
        new_API_calls=0,prepared_request_sha256=binding['request_sha256'])
    save(root/'RESULT.json',result);return result
