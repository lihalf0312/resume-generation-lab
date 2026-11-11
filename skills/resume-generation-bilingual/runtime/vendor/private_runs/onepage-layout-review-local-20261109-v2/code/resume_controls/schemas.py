"""Authoritative v3 wire definitions; exports, prompts and validators share these objects."""
import re
from .common import finite_number,digest
VERSION='controlled-v4-review-routing-1'
QUOTE_MAX=1024
NOTE_MAX=1200
RECOVERY_METADATA={'stage':'exact_current_schema_stage_only','source_map_sha256':'exact_current_source_map_hash_only','important_omissions_note':'null_only','language_advice_extra':'null_only','note':'null_or_exact_unused_only'}
MAX_REVIEW_FACTS=160
MAX_BILINGUAL_FACTS=240
FACETS=['actor','period_grade','quantity_unit','status_scope','ability_medium','qualification','causality']
VERDICTS=['supported','contradicted','missing_support','ambiguous']
ID={'type':'string','pattern':r'^u_[a-f0-9]{20}$'}
HASH={'type':'string','pattern':r'^[a-f0-9]{64}$'}
def obj(props,required=None):return {'type':'object','properties':props,'required':list(props) if required is None else required,'additionalProperties':False}
def arr(item,minimum=0,maximum=200):return {'type':'array','items':item,'minItems':minimum,'maxItems':maximum}
def string(maximum=1000,minimum=1):return {'type':'string','minLength':minimum,'maxLength':maximum}
REF=obj({'source_id':{'type':'string','pattern':r'^(M|JD):L[0-9]{4,}$'},'quote':string(QUOTE_MAX)},['source_id'])
RESUME=obj({'name':string(120),'sections':arr(obj({'heading':string(120),'purpose':{'enum':['education','experience','projects','skills','summary','other']},'items':arr(obj({'heading':string(240,0),'date':string(100,0),'bullets':arr(string(900),0,80)}),1,25)}),1,12)})
GENERATION=obj({'schema_version':{'const':VERSION},'resume':RESUME,'state':{'enum':['ready','awaiting_user']},'necessary_questions':arr(string(300),0,5),'optional_questions':arr(string(300),0,5),'selection_notes':arr(string(300),0,12)})
COMMON={'op':{'enum':['replace','delete','move']},'target_id':ID,'original_hash':HASH,'reason':string(350),'source_refs':arr(REF,0,6)}
REPLACE=obj({**COMMON,'op':{'const':'replace'},'text':string(1500,0)})
DELETE=obj({**COMMON,'op':{'const':'delete'}})
MOVE=obj({**COMMON,'op':{'const':'move'},'new_parent_id':ID,'after_id':{'oneOf':[ID,{'type':'null'}]},'purpose':{'enum':['role_affiliation','selection_order']}})
# Affected descendants are computed by the program, not redundantly declared by the model.
PATCH=obj({'schema_version':{'const':VERSION},'base_version':HASH,'operations':arr({'oneOf':[REPLACE,DELETE,MOVE]},1,40)})
CHECK=obj({'id':ID,'judgment':{'enum':VERDICTS},'evidence':arr(REF,0,4),'note':string(NOTE_MAX)})
OMISSION=obj({'source_ref':REF,'reason':string(NOTE_MAX),'material':{'type':'boolean'}})
ADVICE=obj({'id':ID,'note':string(NOTE_MAX)})
REVIEW=obj({'schema_version':{'const':VERSION},'candidate_version':HASH,'checks':arr(CHECK,0,MAX_REVIEW_FACTS),'complete':{'type':'boolean'},'incomplete_reason':string(200,0),'important_omissions':arr(OMISSION,0,8),'language_advice':arr(ADVICE,0,8),'unresolved_claim_ids':arr(ID,0,30),'awaiting_user_questions':arr(string(250),0,5),'job_fit_gaps':arr(obj({'jd_ref':REF,'note':string(NOTE_MAX)}),0,8)})
LANG={'enum':['en','zh']}
BILINGUAL=obj({'schema_version':{'const':VERSION},'candidate_versions':obj({'en':HASH,'zh':HASH}),'checks':arr(obj({**CHECK['properties'],'language':LANG}),0,MAX_BILINGUAL_FACTS),'complete':{'type':'boolean'},'incomplete_reason':string(200,0),'important_omissions':arr(obj({**OMISSION['properties'],'language':LANG}),0,12),'language_advice':arr(obj({**ADVICE['properties'],'language':LANG}),0,12),'unresolved_claims':arr(obj({'id':ID,'language':LANG}),0,40),'awaiting_user_questions':arr(obj({'question':string(250),'language':LANG}),0,8),'job_fit_gaps':arr(obj({'jd_ref':REF,'note':string(NOTE_MAX)}),0,8),'comparisons':arr(obj({'en_id':ID,'zh_id':ID,'category':{'enum':['translation_difference','reasonable_omission','source_ambiguity','unsupported_addition','contradiction','compatible']},'note':string(NOTE_MAX)}),0,20)})
SCHEMAS={'generate':GENERATION,'review':REVIEW,'patch':PATCH,'final_review':REVIEW,'bilingual_review':BILINGUAL}
def exported():return {'protocol_version':VERSION,'quote_max':QUOTE_MAX,'note_max':NOTE_MAX,'recovery_metadata':RECOVERY_METADATA,'schemas':SCHEMAS}
def protocol_hash():return digest(exported())

def validate(schema,value,path='$'):
 if 'oneOf'in schema:
  passed=0
  for choice in schema['oneOf']:
   try:validate(choice,value,path);passed+=1
   except ValueError:pass
  if passed!=1:raise ValueError('schema_oneOf:'+path)
  return
 if 'const'in schema and value!=schema['const']:raise ValueError('schema_const:'+path)
 if 'enum'in schema and value not in schema['enum']:raise ValueError('schema_enum:'+path)
 t=schema.get('type')
 good={'object':lambda:isinstance(value,dict),'array':lambda:isinstance(value,list),'string':lambda:isinstance(value,str),'boolean':lambda:type(value)is bool,'integer':lambda:type(value)is int,'number':lambda:finite_number(value),'null':lambda:value is None}
 if t and not good[t]():raise ValueError('schema_type:'+path)
 if t=='object':
  if set(schema.get('required',[]))-set(value):raise ValueError('schema_required:'+path)
  if schema.get('additionalProperties')is False and set(value)-set(schema['properties']):raise ValueError('schema_undeclared_field:'+path)
  for k,v in value.items():
   if k in schema['properties']:validate(schema['properties'][k],v,path+'.'+k)
 if t=='array':
  if not schema.get('minItems',0)<=len(value)<=schema.get('maxItems',10**9):raise ValueError('schema_array_length:'+path)
  for i,v in enumerate(value):validate(schema['items'],v,path+'['+str(i)+']')
 if t=='string':
  if not schema.get('minLength',0)<=len(value)<=schema.get('maxLength',10**9):raise ValueError('schema_string_length:'+path)
  if 'pattern'in schema and re.fullmatch(schema['pattern'],value)is None:raise ValueError('schema_pattern:'+path)
 return value
