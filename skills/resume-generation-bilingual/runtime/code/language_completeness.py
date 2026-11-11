"""Language-completeness precheck and exact, caller-authorized name substitution.

This checks visible Han-script residue in English, not all possible language or
translation errors. Original names are not hallucinations. Bindings are trusted
caller input from source review/user choices, never model self-authorization.
"""
from copy import deepcopy
import hashlib,json,re
from pathlib import Path

VERSION='language-completeness-v1'
BINDINGS_VERSION='language-name-bindings-v1'
_MODULE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
HAN=re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]+')
AUX={'selection_note','necessary_question','optional_question','state'}
AUTHORITIES=['source_supplied_english','source_declared_official','user_confirmed_official',
 'verified_official','user_approved_transliteration','user_approved_descriptive',
 'user_requested_original_script','source_reviewed_technical_literal']
CATEGORIES=['person_name','institution_name','organization_name','project_name','technical_literal','other_name']
KEYS={'binding_id','source_text','output_text','category','authority','authority_reference','source_refs','unit_ids'}
REF_SCHEMA={'type':'object','properties':{'source_id':{'type':'string'},'quote':{'type':'string'}},'required':['source_id'],'additionalProperties':False}
BINDINGS_SCHEMA={'type':'object','properties':{'schema_version':{'const':BINDINGS_VERSION},'entries':{'type':'array','items':{'type':'object','properties':{
 'binding_id':{'type':'string','minLength':1},'source_text':{'type':'string','minLength':1},'output_text':{'type':'string','minLength':1},'category':{'enum':CATEGORIES},'authority':{'enum':AUTHORITIES},'authority_reference':{'type':'string'},'source_refs':{'type':'array','items':REF_SCHEMA,'minItems':1},'unit_ids':{'type':'array','items':{'type':'string'},'uniqueItems':True}},'required':sorted(KEYS),'additionalProperties':False}}},'required':['schema_version','entries'],'additionalProperties':False}
LANGUAGE_OUTPUT_GUIDANCE=(
 'Deliver English resume prose in English. Prefer explicitly supplied English names; use official names '
 'only with a reliable source or explicit user confirmation. Never invent an official school, company, '
 'project or personal English name. If a necessary name has no confirmed English form, preserve the '
 'source identity in a usable draft and clearly surface a language choice: the user may supply a known '
 'English name or authorize a transliteration/descriptive, non-official rendering. Do not silently '
 'call a mixed-language draft complete English, and do not delete institutions to hide the problem. '
 'A request for English alone is not approval of an invented official name. Respect explicit choices '
 'to retain an original-script name and distinguish source-literal technical tokens from untranslated '
 'prose. Do not infer nationality, native language, prestige or qualifications from a name. Chinese '
 'resumes may retain suitable English technical terms and source-supplied names. Translation choices '
 'still require full source review; a script check cannot certify fluent or faithful translation.'
)
def language_output_guidance(language):
 if language=='en':return 'Requested resume language is English (en). '+LANGUAGE_OUTPUT_GUIDANCE
 if language=='zh':return (
  'Requested resume language is Chinese (zh). Deliver Chinese resume prose, including ordinary '
  'section headings and descriptive labels, in Chinese. Chinese prose is not an English-language '
  'completion defect. Preserve supported personal and official proper names and suitable technical '
  'terms in their source-supplied or explicitly chosen form; do not force translations of names or '
  'technical labels. The availability of an English name alone does not require replacing a Chinese '
  'name in a Chinese resume. Never invent an official translated name. Respect explicit caller name '
  'bindings and original-script choices. A translation or name choice must not add qualifications, '
  'nationality, prestige or authority. Do not delete identities to hide uncertainty. Missing optional '
  'English names does not block a Chinese draft. Translation choices still require full source '
  'review; a script check cannot certify fluent or faithful translation.')
 raise ValueError('supported_language_required')

OPTIONAL_INPUT_GUIDANCE=(
 '提供以下信息通常能让结果更准确，但都不是基本生成的必填项：已知的学校、机构和项目官方英文名；'
 '希望使用的本人英文姓名或拼写。若不知道官方英名，可以稍后选择是否允许音译或明确非官方的描述性译法。'
 '中文简历的校徽和证件照也是可选项，仅在你主动提供并开启时使用；不会据此评价学校，缺失不阻止基本生成。'
)

def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
def text_hash(value):return hashlib.sha256(value.encode('utf-8')).hexdigest()

def _source(source):
 if not isinstance(source,dict)or set(source)!={'case_id','source_language','material_text','jd_text'}or any(not isinstance(x,str)for x in source.values()):raise ValueError('four_key_source_required')
 return digest(source)

def _document(value,source,language):
 from resume_controls import document as d
 if language not in ('en','zh'):raise ValueError('supported_language_required')
 if isinstance(value,dict)and 'raw_document'in value:
  from deliverable_review import audit_review
  audit_review(value,None,source,value['runtime_date_basis'])
  doc=value['raw_document'];units=[deepcopy(u)for u in value['units']if u['kind']not in AUX];version=value['version']
 else:
  doc=value;d.validate(doc);d.validate_intent_context(doc,source['jd_text']);version=d.version(doc)
  units=[{'id':n['id'],'kind':'body'if n['kind']=='sentence'else n['kind'],'text':n['text'],'text_sha256':text_hash(n['text']),'owner_id':n['parent']}for n in doc['nodes']]
 if doc['language']!=language:raise ValueError('candidate_language_mismatch')
 return doc,units,version

def _validated_bindings(bindings,source):
 from resume_controls.citations import locate
 if bindings is None:return [],[]
 if not isinstance(bindings,dict)or set(bindings)!={'schema_version','entries'}or bindings['schema_version']!=BINDINGS_VERSION or not isinstance(bindings['entries'],list):return [],[{'binding_id':None,'reason':'invalid_binding_envelope'}]
 valid=[];errors=[];seen=set()
 for b in bindings['entries']:
  ident=b.get('binding_id')if isinstance(b,dict)else None
  try:
   if not isinstance(b,dict)or set(b)!=KEYS:raise ValueError('binding_fields')
   if any(not isinstance(b[k],str)or not b[k].strip()for k in ['binding_id','source_text','output_text']):raise ValueError('nonempty_name_fields_required')
   if ident in seen:raise ValueError('duplicate_binding_id')
   seen.add(ident)
   if b['category']not in CATEGORIES or b['authority']not in AUTHORITIES:raise ValueError('unknown_category_or_authority')
   if not isinstance(b['authority_reference'],str):raise ValueError('authority_reference_string_required')
   if not isinstance(b['unit_ids'],list)or any(not isinstance(x,str)or not x for x in b['unit_ids'])or len(set(b['unit_ids']))!=len(b['unit_ids']):raise ValueError('explicit_unit_scope_invalid')
   if not isinstance(b['source_refs'],list)or not b['source_refs']:raise ValueError('personal_source_reference_required')
   locations=[];selected=[]
   for ref in b['source_refs']:
    loc=locate(source['material_text'],ref,source['jd_text'],personal=True)
    if loc['status']!='unique':raise ValueError('name_reference_not_unique_personal_material')
    selected.append(ref.get('quote')or loc['matches'][0]['text']);locations.append(loc)
   if not any(b['source_text']in text for text in selected):raise ValueError('original_name_not_in_selected_source')
   authority=b['authority']
   if authority in ('source_supplied_english','source_declared_official'):
    if not any(b['output_text']in text for text in selected):raise ValueError('english_form_not_explicit_in_selected_source')
   elif not b['authority_reference'].strip():raise ValueError('caller_confirmation_or_review_reference_required')
   if authority=='verified_official'and not re.match(r'^https?://[^/\s]+',b['authority_reference']):raise ValueError('verified_official_source_url_required')
   retain=authority in ('user_requested_original_script','source_reviewed_technical_literal')
   if retain and b['output_text']!=b['source_text']:raise ValueError('retained_literal_must_be_unchanged')
   if authority=='source_reviewed_technical_literal'and b['category']!='technical_literal':raise ValueError('technical_exception_requires_technical_category')
   if not retain and HAN.search(b['output_text']):raise ValueError('english_name_binding_still_contains_han')
   if any(x['source_text']==b['source_text']and x['output_text']!=b['output_text']and (not x['unit_ids']or not b['unit_ids']or set(x['unit_ids'])&set(b['unit_ids']))for x in valid):raise ValueError('conflicting_name_choices')
   valid.append({**deepcopy(b),'source_locations':locations,
    'official_status':('claimed_by_caller_or_source_requires_review'if authority in ('source_declared_official','user_confirmed_official','verified_official')else'not_claimed'),
    'authority_automatically_verified':False})
  except (ValueError,KeyError,TypeError)as exc:errors.append({'binding_id':ident,'reason':str(exc)})
 return valid,errors

def _category(unit,node,span):
 kind=unit['kind'];text=unit['text']
 if kind=='name':return 'person_name'
 if kind=='entry':
  delimiter=re.search(r'[|｜\n]',text)
  if delimiter and span.start()>delimiter.start():return 'role_or_education_description'
  return {'education':'institution_name','experience':'organization_name','projects':'project_name'}.get(node.get('purpose'),'name_or_activity_needs_review')
 return {'body':'term_or_prose_needs_review','label':'label_or_technical_term','section':'section_heading','date':'date_format'}.get(kind,'text_needs_review')

def _source_candidates(text,source):
 from resume_controls.citations import index_source,locate
 result=[]
 for block in index_source(source['material_text']):
  if text in block['text']:
   ref={'source_id':block['id'],'quote':text};result.append({'reference':ref,'source_block':block,'location':locate(source['material_text'],ref,source['jd_text']), 'literal_location_only_not_semantic_proof':True})
 return result

def audit_language(doc_or_deliverable,source,language,bindings=None):
 source_hash=_source(source);doc,units,version=_document(doc_or_deliverable,source,language);entries,errors=_validated_bindings(bindings,source)
 nodes={n['id']:n for n in doc['nodes']};findings=[];accepted=[]
 for b in entries:
  if any(i not in nodes for i in b['unit_ids']):errors.append({'binding_id':b['binding_id'],'reason':'binding_target_not_in_current_document'})
 if language=='en':
  for unit in units:
   target=unit['owner_id']if unit['kind']=='label'else unit['id'];node=nodes[target]
   for span in HAN.finditer(unit['text']):
    applied=[]
    for b in entries:
     if b['unit_ids']and target not in b['unit_ids']:continue
     at=unit['text'].find(b['source_text'])
     while at>=0:
      if at<=span.start()and span.end()<=at+len(b['source_text']):applied.append(b);break
      at=unit['text'].find(b['source_text'],at+1)
    applied.sort(key=lambda b:len(b['source_text']),reverse=True)
    b=applied[0]if applied else None
    structural_category=_category(unit,node,span)
    if b and b['authority']=='source_reviewed_technical_literal'and structural_category in ('person_name','institution_name','organization_name','project_name'):
     errors.append({'binding_id':b['binding_id'],'reason':'name_slot_cannot_be_exempted_as_technical_literal'});b=None
    category=b['category']if b else structural_category
    item={'span_id':'lang_'+digest({'unit':unit['id'],'text_hash':unit['text_sha256'],'start':span.start(),'end':span.end()})[:20],
     'unit_id':unit['id'],'target_id':target,'unit_kind':unit['kind'],'unit_text':unit['text'],'unit_text_sha256':unit['text_sha256'],
     'span':{'start':span.start(),'end':span.end(),'text':span.group()},'category':category,
     'classification_basis':'explicit_binding'if b else'document_structure_hint_requires_semantic_review',
     'source_candidates':_source_candidates(b['source_text']if b else span.group(),source),
     'original_script_is_not_itself_a_factual_error':True,'binding_id':b['binding_id']if b else None}
    if b and b['authority']in ('user_requested_original_script','source_reviewed_technical_literal'):
     item.update(status='explicit_exception',authority=b['authority'],official_status=b['official_status'],review_question=None);accepted.append(item)
    else:
     item.update(status='confirmed_english_form_not_applied'if b else'language_choice_pending',authority=b['authority']if b else None,
      review_question=('Apply the explicitly confirmed English form, then re-review the new version.'if b else
       'Confirm the appropriate English rendering or an explicit original-script/technical-literal exception. A known official name is helpful but not mandatory; transliteration/descriptive naming needs a clear choice and must not be called official.'))
     findings.append(item)
 pending=bool(findings or errors)
 result={'schema_version':VERSION,'language':language,'candidate_version':version,'source_case_sha256':source_hash,
  'bindings_sha256':digest(bindings),'module_sha256':_MODULE_SHA256,'language_pending':pending,'precheck_passed':not pending,
  'preview_allowed':True,'basic_generation_blocked':False,'findings':findings,'accepted_exceptions':accepted,
  'binding_errors':errors,'validated_bindings':entries,'questions_required_for_completion':[x['review_question']for x in findings],
  'status':('language_choice_pending'if pending else'english_with_explicit_exceptions'if accepted else'no_han_residue_detected'if language=='en'else'chinese_script_policy_no_extra_restriction'),
  'scan_scope':'Visible Han-script residues in English; not a general language classifier. Chinese may contain Latin technical terms and names.',
  'semantic_language_certified':False,'official_names_automatically_certified':False,
  'full_source_review_still_required':True,'optional_input_guidance':OPTIONAL_INPUT_GUIDANCE}
 return {**result,'language_audit_version':digest(result)}

def build_language_patch(raw_document,source,bindings):
 """Exact longest-match substitutions in caller-scoped units; no naming invention.

 Return a controlled-v4 PATCH or None. Empty unit_ids is generation context only,
 never permission to substitute across every occurrence. Invalid binding => fail
 closed. Every new output still needs rendering and complete source review.
 """
 from resume_controls import document as d
 from resume_controls.schemas import VERSION as CONTROLLED, PATCH, validate
 _source(source);d.validate(raw_document);d.validate_intent_context(raw_document,source['jd_text'])
 if raw_document['language']!='en':return None
 entries,errors=_validated_bindings(bindings,source)
 if errors:raise ValueError('invalid_language_bindings:'+json.dumps(errors,ensure_ascii=False))
 nodes={n['id']:n for n in raw_document['nodes']}
 for b in entries:
  if any(i not in nodes for i in b['unit_ids']):raise ValueError('language_binding_target_not_in_document')
  if any(nodes[i]['kind']=='date'for i in b['unit_ids']):raise ValueError('name_mapping_cannot_target_date')
 ops=[]
 for n in raw_document['nodes']:
  eligible=[b for b in entries if n['id']in b['unit_ids']and b['source_text']!=b['output_text']]
  eligible.sort(key=lambda b:len(b['source_text']),reverse=True)
  text=n['text'];at=0;parts=[];used=[]
  while at<len(text):
   def matches(b):
    name=b['source_text'];end=at+len(name)
    if not text.startswith(name,at):return False
    word=lambda c:c.isascii()and(c.isalnum()or c=='_')
    if word(name[0])and at>0 and word(text[at-1]):return False
    if word(name[-1])and end<len(text)and word(text[end]):return False
    return True
   b=next((b for b in eligible if matches(b)),None)
   if b:parts.append(b['output_text']);at+=len(b['source_text']);used.append(b)
   else:parts.append(text[at]);at+=1
  new=''.join(parts)
  if new==text:continue
  refs=[]
  for b in used:
   for ref in b['source_refs']:
    if ref not in refs:refs.append(deepcopy(ref))
  ops.append({'op':'replace','target_id':n['id'],'original_hash':text_hash(text),'text':new,
   'reason':'Apply explicit caller-confirmed scoped name mappings only. Preserve all other text. Authority is recorded separately in language bindings; no automatic official-name certification.',
   'source_refs':refs})
 if not ops:return None
 patch={'schema_version':CONTROLLED,'base_version':d.version(raw_document),'operations':ops}
 validate(PATCH,patch)
 return patch


def build_language_context(source,language,bindings=None):
 """Bound generation/review context; optional inputs never become required files."""
 source_hash=_source(source)
 if language not in ('en','zh'):raise ValueError('supported_language_required')
 entries,errors=_validated_bindings(bindings,source)
 value={'schema_version':VERSION,'requested_language':language,
  'source_case_sha256':source_hash,'bindings_sha256':digest(bindings),'module_sha256':_MODULE_SHA256,
  'rules':language_output_guidance(language),'optional_input_guidance':OPTIONAL_INPUT_GUIDANCE,
  'explicit_name_bindings':entries,'binding_errors':errors,
  'bindings_are_trusted_caller_input_not_model_authorization':True,
  'basic_generation_blocked':False,'official_names_required_as_input':False,
  'photo_or_school_logo_required_as_input':False,'source_and_jd_unchanged':True,
  'semantic_language_certified':False,'official_names_automatically_certified':False}
 return {**value,'context_sha256':digest(value)}
