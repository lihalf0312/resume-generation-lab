"""Label-only proposals: exact unchanged bodies; fresh full review mandatory."""
from copy import deepcopy
from pathlib import Path
from resume_controls import document as d
from resume_controls.bullet_labels import parse_bullet
from resume_controls.citations import wire_blocks,locate
from resume_controls.common import create_evidence_dir,digest,text_hash,save
from resume_controls.schemas import obj,arr,string,HASH,ID,REF,validate

VERSION='source-bound-label-only-v1'
SCHEMA=obj({'schema_version':{'const':VERSION},'request_sha256':HASH,
    'proposals':arr(obj({'target_id':ID,'original_sha256':HASH,'label':string(48),
        'source_refs':arr(REF,1,6),'reason':string(500)}),1,40)})

def prepare(source,language,generation,document,basis):
    from deliverable_review import build_deliverable
    delivery=build_deliverable(generation,document,source,basis)
    targets=[];blocked=[]
    for node in document['nodes']:
        if node['kind']!='sentence':continue
        parsed=parse_bullet(node['text'],language)
        if parsed['parse_status']=='parsed':continue
        item={'target_id':node['id'],'original_sha256':text_hash(node['text']),
            'body':node['text'],'body_utf8_sha256':text_hash(node['text']),'reason':parsed['reason']}
        # Malformed/repeated markdown is ambiguous. Do not reclassify part as body.
        (targets if parsed['reason']=='missing_explicit_prefix' else blocked).append(item)
    context={'source_blocks':wire_blocks(source['material_text'],source['jd_text']),
        'source_sha256':text_hash(source['material_text']),'jd_sha256':text_hash(source['jd_text']),
        'language':language,'document_version':d.version(document),'generation_sha256':digest(generation),
        'deliverable_version':delivery['version'],'runtime_date_basis':deepcopy(basis),
        'targets':targets,'blocked_ambiguous_prefixes':blocked,'output_schema':SCHEMA,
        'rules':'Propose only a short objective topic label for each chosen listed target. Cite exact personal M: material and check the exact unchanged body. No invented outcome, skill level, seniority or qualification. The complete original body, including any plain colon phrase, is retained byte-for-byte. Never submit body edits, strip plain prefixes, or modify existing valid labels. If no supported label is clear, leave it pending. Quotes prove location only; every proposal needs a new independent complete-deliverable review and fresh render.'}
    q={'stage':'label_only_proposal','context':context}
    return {**q,'input_sha256':digest(q)}

def apply(source,language,generation,document,basis,request,response):
    if request!=prepare(source,language,generation,document,basis):raise ValueError('label_request_source_or_candidate_changed')
    validate(SCHEMA,response)
    if response['request_sha256']!=request['input_sha256']:raise ValueError('stale_label_proposal')
    targets={t['target_id']:t for t in request['context']['targets']};nodes=d.units(document)
    revised=deepcopy(document);out=d.units(revised);seen=set();changes=[]
    for item in response['proposals']:
        ident=item['target_id']
        if ident in seen or ident not in targets:raise ValueError('label_target_duplicate_or_not_missing')
        seen.add(ident);old=nodes[ident]['text']
        if item['original_sha256']!=text_hash(old):raise ValueError('label_body_changed')
        label=item['label']
        candidate='**'+label+('：**' if language=='zh' else ':** ')+old
        parsed=parse_bullet(candidate,language)
        if parsed['parse_status']!='parsed' or parsed['body'].encode('utf-8')!=old.encode('utf-8'):
            raise ValueError('label_invalid_or_body_not_byte_preserved')
        locations=[]
        for ref in item['source_refs']:
            if not ref['source_id'].startswith('M:') or not ref.get('quote','').strip():raise ValueError('exact_personal_source_quote_required')
            located=locate(source['material_text'],ref,source['jd_text'])
            if located['status']!='unique':raise ValueError('label_source_quote_not_uniquely_located')
            locations.append(located)
        out[ident]['text']=candidate
        changes.append({**deepcopy(item),'before':old,'after':candidate,'body_byte_preserved':True,
            'source_locations':locations,'semantic_label_support':'pending_independent_review'})
    d.validate(revised);result=deepcopy(generation);result['resume']=d.to_resume(revised)
    # The only differences are the explicit label prefixes on listed nodes.
    for old in document['nodes']:
        if old['id'] not in seen and out[old['id']]!=old:raise ValueError('unrelated_node_changed')
    return result,revised,{'schema_version':VERSION,'request_sha256':request['input_sha256'],
        'changes':changes,'all_original_body_bytes_preserved':True,'auxiliary_unchanged':True,
        'fresh_complete_review_required':True,'semantic_truth_certified':False,'final_acceptance':False}

def revise(source,language,generation,document,basis,*,directory,target_role,origin,
        stage=None,response=None,presentation=None,header_assets=None,renderer=None,language_bindings=None,provenance=None,document_kind='synthetic_development'):
    import workflow_v3 as w
    root=Path(directory);create_evidence_dir(root)
    request=prepare(source,language,generation,document,basis);save(root/'REQUEST.json',request)
    if stage is not None and response is not None:raise ValueError('one_label_proposal_origin_required')
    if not request['context']['targets'] or (stage is None and response is None):
        result={'status':'needs_label_review','pdf':None,'callback_calls':0,'final_acceptance':False,
            'reason':'no_unambiguous_missing_label_targets' if not request['context']['targets'] else 'explicit_label_proposal_required',
            'original_preview_unchanged':True}
        save(root/'RESULT.json',result);return result
    calls=0
    try:
        if stage is not None:calls=1;response=stage('label-only-proposal',deepcopy(request))
        save(root/'RESPONSE.json',response)
        revised,raw,audit=apply(source,language,generation,document,basis,request,response)
        save(root/'APPLICATION.json',audit);save(root/'DERIVED-GENERATION.json',revised)
    except Exception as exc:
        result={'status':'label_proposal_invalid','reason':str(exc),'callback_calls':calls,
            'no_automatic_retry':True,'final_acceptance':False,'original_preview_unchanged':True}
        save(root/'RESULT.json',result);return result
    result=w.preview(source,language,revised,directory=root/'deliverable',target_role=target_role,
        basis=basis,origin=origin,presentation=presentation,header_assets=header_assets,renderer=renderer,initial_document=raw,document_kind=document_kind,
        language_bindings=language_bindings,provenance={'label_only_application_sha256':digest(audit),
            'prior_provenance':deepcopy(provenance),'new_model_validation':False})
    result.update(revision_route='label_only',callback_calls=calls,all_original_body_bytes_preserved=True,
        label_proposals_pending_complete_review=True,final_acceptance=False)
    save(root/'RESULT.json',result);return result
