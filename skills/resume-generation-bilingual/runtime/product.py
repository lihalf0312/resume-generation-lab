"""Offline product assembly. A caller owns every transport, budget and approval.

No network client, auto retry, ledger, inferred clock or automatic truth verdict.
"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import argparse, json, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RUNTIME = HERE / 'vendor/private_runs/unified-bilingual-local-20261109-v1'
sys.path[:0] = [str(HERE/'code'),str(HERE/'profiles'), str(RUNTIME/'code')]
from resume_controls.common import create_evidence_dir, digest, file_hash, read, read_evidence_bytes, save, text_hash
from resume_controls.requests import load_skill, preflight, _base
from resume_controls.generation_plan import generation_request
from resume_controls.schemas import GENERATION, validate
from resume_controls.citations import wire_blocks
from resume_controls import document as d
from resume_controls.unified import run
from resume_controls.patches import apply_patch
from resume_controls.generic_presentation import validate_target
from compact_generation import compact_request, output_rules
from runtime_date_basis import add_runtime_date_basis
from runtime_context import attach_clock,validate_clock,assert_clock

from workflow_cli_args import MODES
SKILL = RUNTIME/'skill/resume-generation'

def strict_json(text):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError('duplicate_json_key:'+k)
            out[k]=v
        return out
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite_json:'+x)))

def validate_source(source):
    if set(source) != {'case_id','source_language','material_text','jd_text'}:
        raise ValueError('source_only_four_key_case_required')
    if any(not isinstance(v,str) or not v.strip() for v in source.values()):
        raise ValueError('nonempty_source_strings_required')

def clock_reference(*, observed_at=None, timezone=None):
    """Caller must obtain observed_at from its trusted runtime clock, not a source.

    No local timezone guessing and no baked-in audit date. An aware ISO instant
    plus a real IANA zone permits correct dates across midnight/DST boundaries.
    """
    if observed_at is None:
        if timezone is not None: raise ValueError('timezone_without_clock')
        return {'as_of_date':None,'timezone':None,'authority':'unknown','observed_at':None}
    if not isinstance(observed_at,str) or 'T' not in observed_at:
        raise ValueError('aware_iso_clock_instant_required')
    dt=datetime.fromisoformat(observed_at.replace('Z','+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('aware_iso_clock_instant_required')
    try: zone=ZoneInfo(timezone) if isinstance(timezone,str) else None
    except (ZoneInfoNotFoundError,ValueError) as exc:
        raise ValueError('known_iana_timezone_required') from exc
    if zone is None: raise ValueError('known_iana_timezone_required')
    return {'as_of_date':dt.astimezone(zone).date().isoformat(),'timezone':timezone,
            'authority':'caller_supplied_runtime_clock','observed_at':dt.isoformat()}

def prepare(source, language, *, mode='full', observed_at=None, timezone=None,language_bindings=None):
    validate_source(source)
    if mode not in MODES: raise ValueError('explicit_supported_generation_mode_required')
    baseline=generation_request(source,language,load_skill(SKILL))
    request=compact_request(baseline,digest) if mode=='compact_experimental' else deepcopy(baseline)
    from deliverable_review import GENERATION_CONSISTENCY_GUIDANCE
    request['context']['rules']+='\n'+GENERATION_CONSISTENCY_GUIDANCE
    request['context']['complete_deliverable_protocol']='complete-deliverable-product-v2'
    from language_flow import attach_language_context
    request=attach_language_context(request,source,language,language_bindings)
    clock=clock_reference(observed_at=observed_at,timezone=timezone)
    request=attach_clock(request,clock)
    validate_prepared(request,source,language,mode=mode)
    manifest={'schema':'bilingual-product-request-1','mode':mode,'experimental':mode!='full',
        'input_sha256':request['input_sha256'],'source_sha256':text_hash(source['material_text']),
        'jd_sha256':text_hash(source['jd_text']),'schema_sha256':digest(GENERATION),
        'source_ids':[b['id'] for b in request['context']['source_blocks']],
        'runtime_date_basis':request['context']['runtime_date_basis'],
        'date_fix_real_model_tested':False,'paid_execution_authorized':False,
        'source_review_required':True,'layout_review_required':True,
        'compact_guide_sha256':file_hash(HERE/'profiles/GENERATION_GUIDE.md') if mode!='full' else None,
        'model_quality_improvement_established':False}
    return request,manifest

def validate_prepared(request,source,language,*,mode):
    validate_source(source)
    if mode not in MODES: raise ValueError('unsupported_generation_mode')
    clean={k:v for k,v in request.items() if k!='input_sha256'}
    if digest(clean)!=request.get('input_sha256'): raise ValueError('request_digest_changed')
    if clean['stage']!='generate': raise ValueError('generation_only')
    # Compact uses the unchanged base structural/source checker, never pretends
    # to satisfy the full overlay's verbatim long-guidance requirements.
    (preflight if mode=='full' else _base.preflight)(clean)
    base=generation_request(source,language,load_skill(SKILL))['context']
    c=clean['context']
    allowed={'rules','skill_files','runtime_date_basis','runtime_date_basis_sha256','complete_deliverable_protocol','language_input_contract','language_bindings'}
    if set(c)!=set(base)|{'runtime_date_basis','runtime_date_basis_sha256','complete_deliverable_protocol','language_input_contract','language_bindings'}:
        raise ValueError('context_fields_changed')
    if any(c[k]!=v for k,v in base.items() if k not in allowed):
        raise ValueError('source_schema_language_or_template_changed')
    expected=compact_request({'stage':'generate','context':base},digest)['context'] if mode!='full' else base
    from deliverable_review import GENERATION_CONSISTENCY_GUIDANCE
    expected=deepcopy(expected);expected['rules']+='\n'+GENERATION_CONSISTENCY_GUIDANCE
    expected['complete_deliverable_protocol']='complete-deliverable-product-v2'
    from language_flow import attach_language_context
    expected=attach_language_context({'stage':'generate','context':expected},source,language,c['language_bindings'])['context']
    if c['language_input_contract']!=expected['language_input_contract']:raise ValueError('language_input_contract_changed')
    clock=c['runtime_date_basis']
    trusted=clock_reference(observed_at=clock.get('observed_at'),timezone=clock.get('timezone'))
    if clock!=trusted: raise ValueError('runtime_date_clock_mismatch')
    assert_clock(request,trusted)
    wanted=attach_clock({'stage':'generate','context':expected},trusted)['context']
    if c['rules']!=wanted['rules'] or c['skill_files']!=wanted['skill_files']:
        raise ValueError('generation_profile_changed')
    return True

def consume(source,language,result,*,directory,target_role,presentation=None,
            header_assets=None,origin='new_model_response',renderer=None,document_kind='synthetic_development',
            body_review=None,label_review=None,presentation_review=None,request_transform=None,allow_pending_preview=False,raw_document=None):
    """Same schema/stable IDs/real renderer for either generator profile."""
    validate_source(source); validate(GENERATION,result)
    if language not in ('en','zh'):raise ValueError('language_required')
    if origin not in ('new_model_response','host_assisted','manual_development_fixture','synthetic_fake_new_contract','offline_editor_revision'):
        raise ValueError('explicit_origin_required')
    if result['state']=='awaiting_user' and not allow_pending_preview:
        # Do not silently turn unresolved source questions into a ready document.
        directory=Path(directory);create_evidence_dir(directory)
        pending={'status':'awaiting_user','generation':result,'pdf':None,'new_model_calls':0,
                 'automatic_source_truth_certified':False}
        save(directory/'RESULT.json',pending);return pending
    if raw_document is None:
        raw,_=d.ingest(result['resume'],source['case_id']+'-'+language+'-product',language,
                       intent_context=d.goal_context(source['jd_text']))
    else:
        d.validate(raw_document);d.validate_intent_context(raw_document,source['jd_text'])
        if raw_document['language']!=language or d.to_resume(raw_document)!=result['resume']:
            raise ValueError('explicit_stable_document_generation_mismatch')
        raw=deepcopy(raw_document)
    args={} if renderer is None else {'renderer':renderer}
    if request_transform:args['request_transform']=request_transform
    def no_generation(*a): raise AssertionError('saved_response_must_not_generate')
    try:
        out=run(source=source,language=language,skill=load_skill(SKILL),directory=directory,
            stage=no_generation,key_prefix='product-replay',generation_origin=origin,document_kind=document_kind,
            initial_document=raw,initial_generation_state=result['state'],target_role=target_role,presentation=presentation,header_assets=header_assets,
            review_stage=(lambda key,request:body_review) if body_review else None,
            label_review_stage=(lambda key,request:label_review) if label_review else None,
            presentation_review=presentation_review,**args)
    except ValueError as exc:
        # Preserve hard mechanical failures, rather than certifying a readable
        # diagnostic preview or quietly changing fonts/content. No retry.
        if str(exc)!='render_mechanical_integrity_blocked':raise
        root=Path(directory);rendered=read(root/'round-00/render-result.json')
        bundle=read(root/'round-00/visible-label-bundle.json')
        from resume_controls.requests import build
        from resume_controls.bullet_labels import build_label_review
        body_request=build('final_review',skill=load_skill(SKILL),
            material_text=source['material_text'],jd_text=source['jd_text'],candidate=bundle['render_document'])
        save(root/'body-review-request.json',request_transform(body_request) if request_transform else body_request)
        if not bundle['pending_items']:
            label_request=build_label_review(bundle,skill=load_skill(SKILL),
                material_text=source['material_text'],jd_text=source['jd_text'])
            save(root/'label-review-request.json',request_transform(label_request) if request_transform else label_request)
        m=rendered['measurement']
        out={'status':'needs_layout_review','language':language,'page_count':m['pages'],
            'pdf':rendered['pdf'],'pdf_sha256':rendered['pdf_sha256'],'diagnostic_preview_only':True,
            'mechanical_integrity_passed':False,'mechanical_failure':str(exc),
            'fonts_validated':m.get('fonts_validated'),'unexpected_fonts':m.get('unexpected_fonts'),
            'source_review_status':'pending_independent_receipts','callback_calls':{'generate':0,'patch':0},
            'automatic_source_truth_certified':False,'model_quality_improvement_established':False}
        save(root/'RESULT.json',out)
    save(Path(directory)/'GENERATION-STATE.json',{'state':result['state'],
        'necessary_questions':result['necessary_questions'],'optional_questions':result['optional_questions'],
        'selection_notes':result['selection_notes'],'notes_not_covered_by_visible_body_review':True})
    return out

def _legacy_body_preview_generate(source,language,*,stage,key,directory,target_role,mode='full',observed_at=None,timezone=None,**render_options):
    """One caller-owned callback, no retry. Return source/layout pending as observed."""
    validate_source(source);validate_target(target_role,source['jd_text'])
    if render_options.get('header_assets'):
        from resume_controls.header_assets import preflight_header_assets
        preflight_header_assets(render_options['header_assets'],language)
    root=Path(directory);create_evidence_dir(root)
    request,manifest=prepare(source,language,mode=mode,observed_at=observed_at,timezone=timezone)
    save(root/'REQUEST.json',request);save(root/'REQUEST-MANIFEST.json',manifest)
    try:
        result=stage(key,deepcopy(request));save(root/'RESPONSE.json',result)
        return consume(source,language,result,directory=root/'render',target_role=target_role,
            request_transform=lambda q:attach_clock(q,request['context']['runtime_date_basis']),**render_options)
    except Exception as exc:
        save(root/'FAILURE.json',{'reason':str(exc),'no_automatic_retry':True,
             'callback_outcome':'inspect_caller_evidence_before_retry','new_transport_created':False})
        raise

def verify_receipt(directory,source,language,context,*,preserve_invalid_for_preview=False):
    """Strict replay of persisted actual generation. No repair or modeled re-run."""
    directory=Path(directory);validate_source(source)
    freeze=read(directory/'FREEZE.json')
    for name in ('request.json','response.json','parsed.json'):
        if freeze['files'].get(name)!=file_hash(directory/name):raise ValueError('receipt_hash_changed:'+name)
    q=read(directory/'request.json');p=read(directory/'parsed.json');r=read(directory/'response.json')
    if q['call_id']!=freeze['call_id'] or q['case_id']!=source['case_id'] or q['language']!=language:
        raise ValueError('receipt_identity_mismatch')
    if q['source_sha256']!=text_hash(source['material_text']) or q['jd_sha256']!=text_hash(source['jd_text']):
        raise ValueError('receipt_source_mismatch')
    if digest(q['body'])!=q['body_sha256']:raise ValueError('body_hash_mismatch')
    body=q['body']; provider=q['provider']
    if provider=='openai':
        messages=[(m['role'],p['text']) for m in body['input'] for p in m.get('content',[]) if p.get('type')=='input_text']
    else:messages=[(m['role'],m['content']) for m in body['messages']]
    texts=[text for role,text in messages if role=='user']
    contexts=[]
    for text in texts:
        try: c=strict_json(text)
        except ValueError:continue
        if isinstance(c,dict) and 'source_blocks' in c:contexts.append(c)
    if len(contexts)!=1:raise ValueError('one_exact_request_context_required')
    sent=contexts[0];c=deepcopy(context)
    expected_user={k:v for k,v in c.items() if k not in ('rules','skill_files','template_parameters')}
    if digest(c)!=q['context_sha256'] or sent!=expected_user or c['source_blocks']!=wire_blocks(source['material_text'],source['jd_text']):
        raise ValueError('receipt_context_source_ids_mismatch')
    privileged='\n'.join(t for role,t in messages if role in ('developer','system'))
    if c['rules'] not in privileged:raise ValueError('receipt_generation_rules_missing')
    carrier=next((json.JSONDecoder().raw_decode(t)[0] for role,t in messages
                  if role in ('developer','system') and t.startswith('{')),None)
    if not carrier or any(carrier.get(k)!=c[k] for k in ('skill_files','template_parameters')):
        raise ValueError('receipt_skill_or_template_changed')
    if c['output_schema']!=GENERATION or c['requested_language']!=('English' if language=='en' else 'Chinese'):
        raise ValueError('receipt_schema_or_language_mismatch')
    if r.get('http_status')!=200 or r.get('transport_unknown') is not False:
        raise ValueError('confirmed_response_required')
    b=r['body']
    if provider=='openai':
        if b.get('status')!='completed':raise ValueError('completed_response_required')
        text=''.join(p['text'] for m in b['output'] for p in m.get('content',[]) if p.get('type')=='output_text')
    else:
        if len(b['choices'])!=1 or b['choices'][0]['finish_reason']!='stop':raise ValueError('complete_single_choice_required')
        text=b['choices'][0]['message']['content']
    raw_parse_error=None
    try:result=strict_json(text)
    except (ValueError,TypeError) as exc:
        if not preserve_invalid_for_preview:raise
        result=None;raw_parse_error=str(exc)
    if not preserve_invalid_for_preview:validate(GENERATION,result)
    if ((not p.get('contract_pass') and not preserve_invalid_for_preview)
            or (raw_parse_error is None and p.get('result')!=result)
            or p.get('result_kind')=='controlled_v4_patch'):
        raise ValueError('saved_generation_does_not_match_raw_response')
    profile='compact_experimental' if set(c['skill_files'])=={'GENERATION_GUIDE.md'} else 'full'
    return (text if preserve_invalid_for_preview else result),{'original_contract_pass':p.get('contract_pass'),
        'original_contract_error':p.get('contract_error'),'raw_response_retained_for_intake':preserve_invalid_for_preview,
        'raw_parse_error':raw_parse_error,'parsed_cache_compared':raw_parse_error is None,
        'call_id':q['call_id'],'provider':provider,'model':b.get('model'),'mode':profile,
        'response_sha256':file_hash(directory/'response.json'),'freeze_sha256':file_hash(directory/'FREEZE.json'),
        'source_sha256':q['source_sha256'],'jd_sha256':q['jd_sha256'],
        'runtime_date_basis_received':c.get('runtime_date_basis'),
        'date_fix_real_model_tested':False,'new_model_calls':0,'manual_body_edits':False}

def consume_patch(source,language,base,patch,*,directory,target_role,origin,**options):
    """Use the original controlled-v4 validator/applicator; never repair a patch."""
    validate_source(source)
    if origin not in ('new_model_response','manual_development_fixture','synthetic_fake_new_contract','offline_editor_revision'):
        raise ValueError('explicit_patch_origin_required')
    if base['language']!=language:raise ValueError('patch_language_mismatch')
    revised,audit=apply_patch(base,patch,source['material_text'],source['jd_text'])
    root=Path(directory);create_evidence_dir(root)
    save(root/'PATCH.json',patch);save(root/'PATCH-APPLICATION.json',audit)
    save(root/'DERIVED-STABLE-DOCUMENT.json',revised)
    save(root/'PATCH-PROVENANCE.json',{'origin':origin,'transport_verification':'caller_owned',
        'schema_and_stable_base_validated':True,'source_semantics_automatically_certified':False})
    def never(*a):raise AssertionError('patch_replay_must_not_generate')
    return run(source=source,language=language,skill=load_skill(SKILL),directory=root/'render',
        stage=never,key_prefix='product-patch',generation_origin=origin,
        initial_document=revised,target_role=target_role,**options)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['prepare','render-receipt','render-saved'])
    p.add_argument('--source',type=Path,required=True);p.add_argument('--language',choices=['en','zh'],required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=MODES,default='full')
    p.add_argument('--observed-at');p.add_argument('--timezone')
    p.add_argument('--receipt',type=Path);p.add_argument('--response',type=Path)
    p.add_argument('--context',type=Path,help='Frozen generation context matching receipt.context_sha256')
    p.add_argument('--origin',choices=['manual_development_fixture','synthetic_fake_new_contract'])
    for name in ['target-role','presentation','header-assets','body-review','label-review','presentation-review']:
        p.add_argument('--'+name,type=Path)
    a=p.parse_args();source=read(a.source)
    if a.command=='prepare':
        if any((a.receipt,a.response,a.header_assets)):raise ValueError('local_assets_and_responses_not_request_inputs')
        q,m=prepare(source,a.language,mode=a.mode,observed_at=a.observed_at,timezone=a.timezone)
        create_evidence_dir(a.output);save(a.output/'REQUEST.json',q);save(a.output/'MANIFEST.json',m)
        print(json.dumps(m,ensure_ascii=False));return
    if a.observed_at or a.timezone:raise ValueError('do_not_retrofit_clock_into_historical_response')
    if not a.target_role:raise ValueError('explicit_source_bound_target_required')
    if a.command=='render-receipt':
        if not a.receipt or not a.context or a.response or a.origin:raise ValueError('receipt_and_frozen_context_required')
        response,provenance=verify_receipt(a.receipt,source,a.language,read(a.context));origin='new_model_response'
    else:
        if not a.response or not a.origin or a.receipt:raise ValueError('explicit_manual_or_fake_origin_required')
        response=strict_json(read_evidence_bytes(a.response).decode('utf-8'));origin=a.origin
        provenance={'origin':origin,'new_model_calls':0,'date_fix_real_model_tested':False}
    kwargs={name:read(getattr(a,name)) for name in ['presentation','header_assets','body_review','label_review','presentation_review'] if getattr(a,name)}
    result=consume(source,a.language,response,directory=a.output,target_role=read(a.target_role),origin=origin,**kwargs)
    save(a.output/'PROVENANCE.json',provenance)
    print(json.dumps({k:result.get(k) for k in ['status','language','page_count','pdf','pdf_sha256']},ensure_ascii=False))

def generate(*args,**kwargs):
    """Public v3 entry includes complete review and source-directed repair planning."""
    from workflow_v3 import generate as complete_generate
    return complete_generate(*args,**kwargs)

def bind_host_response(*args,**kwargs):
    from host_response import bind
    return bind(*args,**kwargs)

def consume_host_response(*args,**kwargs):
    from host_response import consume
    return consume(*args,**kwargs)

def revise_labels(*args,**kwargs):
    from label_recovery import revise as label_only
    return label_only(*args,**kwargs)

def revise(*args,**kwargs):
    from workflow_v3 import revise_saved
    return revise_saved(*args,**kwargs)

def apply_name_bindings(*args,**kwargs):
    from language_flow import apply_name_bindings as apply
    return apply(*args,**kwargs)

if __name__=='__main__':
    from workflow_v3 import cli
    cli()
