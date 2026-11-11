"""Bounded generation intake. Never repair syntax, types or personal facts.

Only one exact, boolean self-assessment extension is preview-recoverable.
Everything unknown is preserved and blocks projection, not silently discarded.
"""
from copy import deepcopy
import json
from pathlib import Path
from resume_controls.common import create_evidence_dir, digest, text_hash, save, file_hash, save_evidence_bytes
from resume_controls.schemas import GENERATION, validate

VERSION = 'generation-intake-v1'

def strict_json(text):
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('duplicate_json_key:'+key)
            out[key]=value
        return out
    return json.loads(text, object_pairs_hook=pairs,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite_json:'+x)))

def extensions(schema,value,path=()):
    result=[]
    if schema.get('type')=='object' and isinstance(value,dict):
        properties=schema['properties']
        for key,item in value.items():
            here=path+(key,)
            if key not in properties:
                known=here==('resume','sections_order_ok') and type(item) is bool
                result.append({'path':list(here),'json_pointer':'/'+ '/'.join(str(x).replace('~','~0').replace('/','~1') for x in here),
                    'value':deepcopy(item),'value_sha256':digest(item),
                    'rule':'boolean_section_order_self_assessment' if known else None,
                    'preview_isolation_allowed':known,'truth_or_acceptance_authority':False,
                    'status':'quarantined_untrusted_self_assessment' if known else 'unrecognized_extension_requires_review'})
            else:result.extend(extensions(properties[key],item,here))
    elif schema.get('type')=='array' and isinstance(value,list):
        for i,item in enumerate(value):result.extend(extensions(schema['items'],item,path+(i,)))
    return result

def ingest(payload,*,directory):
    root=Path(directory);create_evidence_dir(root)
    report={'schema_version':VERSION,'status':'needs_response_review','preview_allowed':False,
        'original_schema_pass':False,'candidate_schema_pass':False,'extensions':[],
        'transformations':[],'no_automatic_retry':True,'no_facts_rewritten':True,
        'semantic_truth_certified':False,'final_acceptance':False,'response_review_pending':False}
    try:
        if isinstance(payload,str):
            save_evidence_bytes(root/'ORIGINAL-RESPONSE.txt',payload.encode('utf-8'))
            report.update(input_kind='raw_json_text',raw_utf8_sha256=file_hash(root/'ORIGINAL-RESPONSE.txt'),duplicate_keys_checked=True)
            parsed=strict_json(payload)
        elif isinstance(payload,dict):
            # A parsed-only callback cannot prove anything about its prior wire bytes.
            report.update(input_kind='caller_parsed_object',raw_utf8_sha256=None,duplicate_keys_checked=False,
                raw_wire_unavailable=True)
            parsed=deepcopy(payload)
            json.dumps(parsed,allow_nan=False)
        else:raise ValueError('raw_json_text_or_parsed_generation_object_required')
        save(root/'ORIGINAL-PAYLOAD.json',parsed);report['original_payload_sha256']=digest(parsed)
        try:validate(GENERATION,parsed);report['original_schema_pass']=True
        except ValueError as exc:report['original_schema_error']=str(exc)
        extras=extensions(GENERATION,parsed);report['extensions']=extras
        candidate=deepcopy(parsed)
        if any(not item['preview_isolation_allowed'] for item in extras):
            raise ValueError('unrecognized_extensions_preserved_no_projection')
        for item in extras:
            # No broad strip-extra-fields pass. Exact allowlisted rule only.
            del candidate['resume']['sections_order_ok']
            report['transformations'].append({'operation':'isolate_untrusted_extension',
                'path':item['path'],'value_sha256':item['value_sha256'],'rule':item['rule']})
        validate(GENERATION,candidate)
        report.update(status='recovered_preview_pending_response_review' if extras else 'schema_valid',
            preview_allowed=True,candidate_schema_pass=True,candidate_sha256=digest(candidate),
            response_review_pending=bool(extras))
        save(root/'PREVIEW-CANDIDATE.json',candidate)
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        report['reason']=str(exc);report['response_review_pending']=True;candidate=None
    save(root/'REPORT.json',report)
    lines=['Response intake / 响应接收报告',
        'Status / 状态: '+report['status'],
        'Raw payload is retained. No automatic retry or factual certification.',
        '原始内容已保留；没有自动重试，也没有自动认定事实正确。']
    for item in report['extensions']:
        lines.append(item['json_pointer']+' = '+json.dumps(item['value'],ensure_ascii=False)+'; '+item['status'])
    if report.get('reason'):lines.append(report['reason'])
    if report['status']=='recovered_preview_pending_response_review':
        lines.append('Preview excludes the quarantined self-assessment. Review the original payload and report; this is not a schema pass of the model response.')
        lines.append('预览隔离了模型自评字段，需核对原始内容和报告；不能算作模型原始响应通过结构检查。')
    elif not report['preview_allowed']:
        lines.append('No preview was created. Preserve the original payload and resolve the response error before projection.')
        lines.append('未生成预览。原始内容已保留，需要先审查响应错误，不能丢弃未知事实后继续。')
    save_evidence_bytes(root/'REVIEW-NOTICE.txt',('\n'.join(lines)+'\n').encode('utf-8'))
    return candidate,report


def history_pending(value):
    """Monotonic display flag only; ancestry metadata can never grant acceptance."""
    if isinstance(value,dict):
        return any(value.get(k) is True for k in ('response_review_pending','response_contract_pending','prior_response_contract_pending')) or any(history_pending(x) for x in value.values())
    return isinstance(value,list) and any(history_pending(x) for x in value)

def saved_lineage(directory):
    from resume_controls.common import read
    root=Path(directory)
    paths=('response-intake/REPORT.json','FLOW-CONTEXT.json','RESULT.json')
    return {'prior_run':str(root),'prior_records':{name:read(root/name) for name in paths if (root/name).exists()}}
