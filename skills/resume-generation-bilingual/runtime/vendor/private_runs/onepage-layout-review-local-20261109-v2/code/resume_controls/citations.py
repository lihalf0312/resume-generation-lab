"""Annotated complete source blocks. Literal identity never certifies entailment."""
from .common import text_hash,digest
from .schemas import REF,validate

def index_source(text,namespace='M'):
 if namespace not in ['M','JD']:raise ValueError('source_namespace')
 out=[];offset=0
 for i,line in enumerate(text.splitlines(keepends=True),1):
  value=line.rstrip('\r\n')
  if value.strip():out.append({'id':f'{namespace}:L{i:04d}','source_type':'personal_material' if namespace=='M' else 'job_requirement','start':offset,'end':offset+len(value),'text':value,'text_sha256':text_hash(value)})
  offset+=len(line)
 return out

def catalogue(material_text,jd_text=''):return index_source(material_text)+index_source(jd_text,'JD')
def wire_blocks(material_text,jd_text):return [{k:b[k] for k in ['id','source_type','text','text_sha256']} for b in catalogue(material_text,jd_text)]
def locate(text,reference,jd_text='',personal=True):
 validate(REF,reference);blocks=catalogue(text,jd_text);sid=reference['source_id'];block=next((b for b in blocks if b['id']==sid),None)
 common={'semantic_support_certified':False,'whitespace_deleted':False,'requested_source_id':sid}
 if personal and sid.startswith('JD:'):return {**common,'status':'JD_cannot_support_personal_fact','matches':[]}
 if not block:return {**common,'status':'missing_source_id','matches':[]}
 quote=reference.get('quote')
 if quote is None:return {**common,'status':'unique','matches':[block],'mode':'full_original_block_selected_by_ID'}
 matches=[];at=block['text'].find(quote)
 while at>=0:
  matches.append({'source_id':sid,'source_type':block['source_type'],'start':block['start']+at,'end':block['start']+at+len(quote),'quote':quote,'text_sha256':text_hash(quote)});at=block['text'].find(quote,at+1)
 elsewhere=[b['id'] for b in blocks if b['id']!=sid and quote in b['text']]
 return {**common,'status':'unique' if len(matches)==1 else 'ambiguous' if matches else 'quote_in_other_block_wrong_source_id' if elsewhere else 'not_literal','matches':matches,'other_matching_block_ids':elsewhere,'mode':'short_exact_quote'}
def resolve_all(text,references,jd_text='',personal=True):return [locate(text,r,jd_text,personal) for r in references]
