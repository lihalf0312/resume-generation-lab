"""Structured local diagnostics: first blocker plus every independently found error."""
class ContractError(ValueError):
 def __init__(self,errors):
  self.errors=errors;super().__init__(errors[0]['code']+':'+errors[0]['path'])
def issue(path,code,**detail):return {'path':path,'code':code,**detail}
def schema_errors(schema,value,path='$'):
 from .schemas import validate
 if 'oneOf'in schema:
  choices=schema['oneOf'];selected=[s for s in choices if isinstance(value,dict) and s.get('properties',{}).get('op',{}).get('const')==value.get('op')]
  if len(selected)==1:return schema_errors(selected[0],value,path)
  try:validate(schema,value,path);return []
  except ValueError as exc:return [issue(path,str(exc).split(':')[0])]
 out=[];t=schema.get('type')
 try:
  shallow={k:v for k,v in schema.items() if k not in ['properties','required','items','minItems','maxItems','additionalProperties']}
  if t=='object':shallow.update(properties={},additionalProperties=True)
  if t=='array':shallow['items']={}
  validate(shallow,value,path)
 except (ValueError,TypeError) as exc:return [issue(path,str(exc).split(':')[0])]
 if t=='object':
  for k in schema.get('required',[]):
   if k not in value:out.append(issue(path+'.'+k,'schema_required'))
  for k,v in value.items():
   if k not in schema['properties']:
    if not schema.get('additionalProperties',True):out.append(issue(path+'.'+k,'schema_undeclared_field'))
   else:out.extend(schema_errors(schema['properties'][k],v,path+'.'+k))
 if t=='array':
  if not schema.get('minItems',0)<=len(value)<=schema.get('maxItems',10**9):out.append(issue(path,'schema_array_length',actual=len(value)))
  for i,v in enumerate(value):out.extend(schema_errors(schema['items'],v,f'{path}[{i}]'))
 return out
