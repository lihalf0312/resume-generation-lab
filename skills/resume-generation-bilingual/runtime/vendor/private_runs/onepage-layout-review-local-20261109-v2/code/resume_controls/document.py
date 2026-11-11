"""Stable content-unit IDs. Versions bind text, hierarchy and order, not case IDs."""
from copy import deepcopy
import re
from .common import digest,text_hash
from .schemas import ID as SCHEMA_ID
ID=re.compile(SCHEMA_ID['pattern'])
KINDS={'name','section','entry','date','sentence'}
PARENTS={'name':None,'section':None,'entry':'section','date':'entry','sentence':'entry'}
def validate(doc):
 if set(doc)-{'intent_context'}!={'document_id','revision','language','nodes','protected_ids'}:raise ValueError('document_fields')
 if 'intent_context'in doc:
  c=doc['intent_context']
  if not isinstance(c,dict)or set(c)!={'jd_sha256','employers','not_personal_evidence'}or c['not_personal_evidence']is not True or not re.fullmatch('[a-f0-9]{64}',c['jd_sha256']):raise ValueError('intent_context_fields')
  for e in c['employers']:
   if set(e)!={'text','start','end','source_type'}or not isinstance(e['text'],str)or not e['text'].strip()or e['source_type']!='job_requirement' or type(e['start'])is not int or type(e['end'])is not int or e['start']<0 or e['end']<=e['start']:raise ValueError('intent_employer_fields')
 if not isinstance(doc['document_id'],str) or not doc['document_id'] or type(doc['revision'])is not int or doc['revision']<0 or doc['language']not in ['en','zh']:raise ValueError('document_identity')
 nodes=doc['nodes']
 if not isinstance(nodes,list) or not nodes:raise ValueError('document_nodes')
 known={};names=0
 for node in nodes:
  if set(node)!={'id','kind','parent','text','purpose'} or not ID.fullmatch(node.get('id','')) or node['id']in known or node['kind']not in KINDS or not isinstance(node['text'],str):raise ValueError('node_schema_or_duplicate')
  if node['kind']not in ['date','entry'] and not node['text'].strip():raise ValueError('empty_content_unit')
  if node['purpose']not in ['identity','education','experience','projects','skills','summary','other']:raise ValueError('node_purpose')
  expected=PARENTS[node['kind']]
  if expected is None:
   if node['parent']is not None:raise ValueError('root_parent')
  elif node['parent']not in known or known[node['parent']]['kind']!=expected:raise ValueError('parent_missing_or_wrong_kind')
  known[node['id']]=node
  if node['kind']=='name':names+=1
 if names!=1 or nodes[0]['kind']!='name':raise ValueError('one_name_first_required')
 for entry in [n for n in nodes if n['kind']=='entry']:
  children=[n for n in nodes if n['parent']==entry['id']]
  if sum(n['kind']=='date' for n in children)!=1 or children[0]['kind']!='date':raise ValueError('one_date_before_sentences')
 if not any(n['kind']=='section' for n in nodes):raise ValueError('section_required')
 for section in [n for n in nodes if n['kind']=='section']:
  if not any(n['parent']==section['id'] for n in nodes):raise ValueError('empty_section_must_be_explicitly_removed')
 # Every subtree is contiguous; no body can silently drift under another entry.
 for n in nodes:
  indices=[i for i,x in enumerate(nodes) if x['id'] in descendants(doc,n['id'])]
  if indices and indices!=list(range(min(indices),max(indices)+1)):raise ValueError('noncontiguous_subtree')
 if not isinstance(doc['protected_ids'],list) or len(set(doc['protected_ids']))!=len(doc['protected_ids']) or any(i not in known for i in doc['protected_ids']):raise ValueError('protected_id_missing_or_duplicate')
 return doc

def descendants(doc,node_id):
 ids={node_id};changed=True
 while changed:
  before=len(ids);ids.update(n['id'] for n in doc['nodes'] if n['parent'] in ids);changed=len(ids)>before
 return ids

def version(doc):validate(doc);return digest(doc)
def units(doc):validate(doc);return {n['id']:n for n in doc['nodes']}
def ingest(resume,document_id,language,protected_paths=(),intent_context=None):
 if set(resume)!={'name','sections'} or not isinstance(resume['sections'],list):raise ValueError('resume_schema')
 nodes=[];paths={}
 def add(path,kind,parent,text,purpose):
  if not isinstance(text,str):raise ValueError('content_must_be_text')
  ident='u_'+digest({'document':document_id,'birth_path':path,'kind':kind})[:20];nodes.append({'id':ident,'kind':kind,'parent':parent,'text':text,'purpose':purpose});paths[path]=ident;return ident
 add('name','name',None,resume['name'],'identity')
 for si,s in enumerate(resume['sections']):
  if set(s)!={'heading','purpose','items'} or not isinstance(s['items'],list):raise ValueError('section_schema')
  sid=add(f's{si}','section',None,s['heading'],s['purpose'])
  for ei,e in enumerate(s['items']):
   if set(e)!={'heading','date','bullets'} or not isinstance(e['bullets'],list):raise ValueError('entry_schema')
   eid=add(f's{si}.e{ei}','entry',sid,e['heading'],s['purpose']);add(f's{si}.e{ei}.date','date',eid,e['date'],s['purpose'])
   for bi,b in enumerate(e['bullets']):add(f's{si}.e{ei}.b{bi}','sentence',eid,b,s['purpose'])
 doc={'document_id':document_id,'revision':0,'language':language,'nodes':nodes,'protected_ids':[paths[x] for x in protected_paths]}
 if intent_context is not None:doc['intent_context']=deepcopy(intent_context)
 validate(doc);return doc,paths

def to_resume(doc):
 validate(doc);result={'name':doc['nodes'][0]['text'],'sections':[]}
 for s in [n for n in doc['nodes'] if n['kind']=='section']:
  items=[]
  for e in [n for n in doc['nodes'] if n['parent']==s['id']]:
   children=[n for n in doc['nodes'] if n['parent']==e['id']];items.append({'heading':e['text'],'date':next(n['text'] for n in children if n['kind']=='date'),'bullets':[n['text'] for n in children if n['kind']=='sentence']})
  result['sections'].append({'heading':s['text'],'purpose':s['purpose'],'items':items})
 return result

# Exact category labels only. Unknown or embellished headings remain reviewable.
PURE_LABELS=frozenset({
 'profile','summary','professional summary','career summary','target','target role','application target',
 'experience','work experience','professional experience','employment history','education','education and training',
 'education & certifications','education and certifications','projects','selected projects','project experience',
 'skills','technical skills','tools','tools and communication','tools and procedures','languages','other information',
 'volunteering','volunteer experience','interests','education & career development','education and career development',
 '职业简介','个人简介','个人总结','求职意向','目标岗位','工作经历','任职经历','教育背景','教育经历',
 '项目经历','技能','专业技能','工具','工具与沟通','语言','其他信息','其他经历','志愿活动','兴趣爱好',
 'career target','career objective','objective','求职目标','职业目标',
 'additional information','professional development','professional profile','core skills','selected experience','certifications','licences',
 'laboratory experience','additional laboratory contributions','laboratory skills',
 'education & training','technical & communication skills','technical skills and outreach','skills and other',
 '技能与其他','技能与语言','技能与资质','技术技能','个人信息','教育与培训'
})
QUALIFIED_ROLE_NAMES=frozenset({'registered nurse','licensed practical nurse','certified nursing assistant'})
INTENT_LABELS=frozenset({'target','target role','application target','career target','career objective','objective','求职意向','目标岗位','求职目标','职业目标'})
def pure_label(text):
 value=' '.join(text.strip().casefold().split())
 if value.endswith((':','：')):value=value[:-1].rstrip()
 return value in PURE_LABELS

def label_value(text):return ' '.join(text.strip().casefold().rstrip(':：').split())

# Positive whole-field grammar. No suffix is discarded and no list of banned
# personal verbs is used to certify intent. Unknown titles/metadata stay in the
# fact manifest, even when they may in reality be harmless goals.
INTENT_PREFIX=re.compile(r'^(?:(?:target(?:\s+role)?|application target|career (?:target|objective)|objective|求职意向|求职目标|目标岗位|职业目标|目标职位)\s*[:：]\s*|(?:(?:i\s+am\s+)?seeking|applying\s+for)\s+|(?:希望申请|申请目标)\s*)',re.I)
ROLE_NOUNS=tuple('analyst engineer writer chemist editor trainer teacher auditor architect librarian pharmacist therapist buyer planner lead scientist manager director specialist coordinator administrator assistant accountant developer designer researcher technician consultant officer recruiter nurse'.split())
# These tokens describe target occupations, not the candidate's abilities.
ROLE_MODIFIERS=frozenset('study senior junior principal staff associate assistant graduate software hardware mechanical electrical data business quality assurance QA QC test testing technical analytical chemical civil environmental laboratory lab research project product programme program operations finance financial sales marketing customer support service services human resources HR UX UI machine learning information security cybersecurity IT cloud platform systems system full-stack frontend backend web mobile application accounting accounts billing collections content medical clinical public health safety regulatory compliance procurement supply chain logistics manufacturing production process development field construction site design digital communications communication community education training teaching legal document documentation'.split())
ZH_ROLES=tuple('教师 经理 总监 工程师 分析师 专员 协调员 助理 研究员 技师 护士 设计师 顾问 会计 会计师 审计师 架构师 编辑 程序员 主管'.split())
ZH_AREAS=tuple('软件 软件测试 数据 业务 技术文档 解决方案 环境监测 财务 项目 产品 销售 市场 人力资源 测试 质量 机械 电气 现场 实验室 客户支持 运营 网络 安全 云 系统 研发 内容 供应链 采购 物流 生产 工艺'.split())
# A small explicit location vocabulary avoids treating arbitrary prose as a
# location. Unrecognised places are ambiguous, not fabricated or disallowed jobs.
PLACE_FORMS=(
 ('London','UK'),('London','United Kingdom'),('Manchester','UK'),
 ('Berlin','Germany'),('Munich','Germany'),('Paris','France'),
 ('Aveiro','Portugal'),('Lisbon','Portugal'),('Melbourne','Australia'),
 ('Sydney','Australia'),('Toronto','Canada'),('Vancouver','Canada'),
 ('New York','USA'),('San Francisco','USA'),('Boston','USA'),
 ('Shanghai','China'),('Beijing','China'),('Shenzhen','China'),
 ('Singapore',),('Hong Kong',),('Dublin','Ireland'),
 ('上海','中国'),('北京','中国'),('深圳','中国'),('广州','中国'),
 ('杭州','中国'),('香港',),('新加坡',),('伦敦','英国'),
 ('柏林','德国'),('阿威罗','葡萄牙'),('墨尔本','澳大利亚')
)
def _alternatives(values):return '(?:'+'|'.join(re.escape(v)for v in sorted(set(values),key=len,reverse=True))+')'
ROLE_MOD_SEQUENCE=_alternatives(ROLE_MODIFIERS)+r'(?:\s+(?:(?:&|and)\s+)?'+_alternatives(ROLE_MODIFIERS)+r')*'
EN_ROLE=_alternatives(QUALIFIED_ROLE_NAMES)+'|'+r'(?:'+ROLE_MOD_SEQUENCE+r'\s+)?'+_alternatives(ROLE_NOUNS)+r'(?:\s+(?:I{1,3}|IV|V))?'
ZH_ROLE=r'(?:(?:高级|资深|初级)\s*)?(?:'+_alternatives(ZH_AREAS)+r'\s*)?'+_alternatives(ZH_ROLES)
PURE_ROLE=r'(?:(?:a|an|the)\s+)?(?:'+EN_ROLE+'|'+ZH_ROLE+r')(?:\s+(?:role|position|opportunity)|岗位|职位)?'
_places=set()
for _parts in PLACE_FORMS:
 _places.update(_parts)
 if len(_parts)==2:
  _places.add(', '.join(_parts))
  if all(re.search(r'[\u3400-\u9fff]',v)for v in _parts):_places.add(''.join(reversed(_parts)))
LOCATION=_alternatives(_places)
# Full metadata must be either known geography, work arrangement, or a standard
# gender marker. 'Location: I speak German' cannot match a free text wildcard.
META=r'(?:(?:(?:location|based in|工作地点|地点)\s*[:：]\s*)?'+LOCATION+r'|remote|hybrid|on-site|onsite|远程|混合办公|现场办公|f/m/div\.?|m/f/d|f/m/d|m/w/d|all genders)'
METADATA=r'(?:\s*(?:[—–|:：]| - )\s*'+META+r'|\s*\('+META+r'\)|\s*（'+META+r'）)'
WHOLE_INTENT=re.compile(r'(?:'+PURE_ROLE+r')(?:'+METADATA+r')*',re.I)

def organization_entity(text):
 # Literal JD metadata is not enough to turn an arbitrary first-person clause
 # into an employer. Positive name syntax; unknown names remain ambiguous.
 # This is entity TYPING, never evidence of employment or qualification.
 if re.fullmatch(r'(?:[A-Z][a-zA-Z0-9&-]{1,}|[A-Z]{2,})',text):return True
 token=r"[A-Z][A-Za-z0-9&'’-]*"
 suffix=r'(?:Ltd\.?|Limited|Inc\.?|Corp\.?|Corporation|Company|Group|Trust|University|College|Hospital|Centre|Center|Laboratory|Laboratories|Services|Systems|Software|Instruments|Technologies|Solutions|Cooperative|Housing|Foods|Press|Studio)'
 if re.fullmatch(token+r'(?:\s+(?:'+token+r'|and|of|the|for|&))*\s+'+suffix,text):return True
 return bool(re.fullmatch(r'[\u3400-\u9fffA-Za-z0-9·（）()& ]{1,80}(?:公司|集团|医院|大学|学院|研究院|中心|科技|事务所|工作室|银行)',text))

def goal_context(jd_text):
 """Literal JD header metadata, used ONLY to type intended employer names.
 No lookup or inferred personal fact. Unknown formats supply no entity exemption.
 """
 lines=[m for m in re.finditer(r'[^\r\n]+',jd_text)if m.group().strip()]
 employers=[]
 for m in lines:
  labeled=re.fullmatch(r'\s*(?:Company|Employer|公司|雇主)\s*[:：]\s*(.+?)\s*',m.group(),re.I)
  if labeled and organization_entity(labeled.group(1)):
   text=labeled.group(1);start=m.start()+labeled.start(1);employers.append({'text':text,'start':start,'end':start+len(text),'source_type':'job_requirement'});break
 # Existing authorized JD captures use title, blank line, company, blank line,
 # location. Only that explicit header layout is recognised; no body mining.
 if not employers and len(lines)>=3:
  a,b,c=lines[:3]
  if not jd_text[:a.start()].strip()and'\n\n'in jd_text[a.end():b.start()]and'\n\n'in jd_text[b.end():c.start()]:
   text=b.group().strip();start=b.start()+b.group().index(text)
   if len(text)<=150 and organization_entity(text):employers.append({'text':text,'start':start,'end':start+len(text),'source_type':'job_requirement'})
 return {'jd_sha256':__import__('hashlib').sha256(jd_text.encode()).hexdigest(),'employers':employers,'not_personal_evidence':True}

def validate_intent_context(doc,jd_text):
 if 'intent_context'in doc and doc['intent_context']!=goal_context(jd_text):raise ValueError('intent_employer_context_not_bound_to_original_JD')

def goal_components(doc,value):
 # A bounded positive grammar consumes the ENTIRE original field. Employers
 # are exact, source-bound entities, never arbitrary suffix prose or abilities.
 role=PURE_ROLE
 # Occupational domain after a comma is still part of the desired role.
 role=r'(?:'+role+r')(?:\s*,\s*'+ROLE_MOD_SEQUENCE+r')?'
 employers=[e['text']for e in doc.get('intent_context',{}).get('employers',[])]
 if employers:
  employer=_alternatives(employers)
  only=re.fullmatch(r'(?:target employer|target company|目标雇主|目标公司)\s*[:：]\s*('+employer+r')',value,re.I)
  if only:return {'target_role':None,'target_employer':only.group(1)}
  pattern=r'(?P<role>'+role+r')\s*(?:[—–|]| - |\s+at\s+|\s+for\s+)\s*(?P<employer>'+employer+r')(?P<meta>(?:'+METADATA+r')*)'
  pair=re.fullmatch(pattern,value,re.I)
  if pair:return {'target_role':pair.group('role'),'target_employer':pair.group('employer')}
 if re.fullmatch(role+r'(?:'+METADATA+r')*',value,re.I):return {'target_role':value,'target_employer':None}
 return None

def intent_type(doc,node):
 if node['kind']in ['name','date']:return None
 ns={n['id']:n for n in doc['nodes']};text=node['text'].strip();m=INTENT_PREFIX.match(text)
 parent=ns.get(node['parent']);section=parent if parent and parent['kind']=='section' else ns.get(parent['parent']) if parent else None
 in_target=bool(section and label_value(section['text'])in INTENT_LABELS)
 explicit_employer=bool(re.match(r'^(?:target employer|target company|目标雇主|目标公司)\s*[:：]',text,re.I))
 if not(m or in_target or explicit_employer):return None
 # Dates belong to entries, including the containing entry of a sentence. A
 # role-looking child cannot escape personal review inside a dated appointment.
 entry=node if node['kind']=='entry' else parent if parent and parent['kind']=='entry' else None
 if entry and any(c['parent']==entry['id'] and c['kind']=='date' and c['text'].strip() for c in doc['nodes']):return 'dated_experience_context'
 if node['kind']=='sentence':
  # Do not infer an undated target context merely from an ancestor's section
  # label. Its containing entry must itself be a clear goal or goal container.
  explicit_container=bool(entry and section and label_value(section['text'])in INTENT_LABELS and (not entry['text'].strip() or label_value(entry['text'])in INTENT_LABELS))
  clear_parent_goal=bool(entry and intent_type(doc,entry)=='pure_job_intent')
  if not(explicit_container or clear_parent_goal):return 'intent_typing_ambiguous'
 value=text[m.end():]if m else text
 # No split/truncate, no dropping parentheses or tails. Whitespace normalising
 # quotes is deliberately absent; original text/hash remains untouched.
 if '\n'in value or '\r'in value or not goal_components(doc,value):return 'intent_typing_ambiguous'
 return 'pure_job_intent'

def classification(doc):
 validate(doc);out={'facts':[],'decorations':[],'intents':[],'typing_ambiguities':[]}
 for n in doc['nodes']:
  reason=None
  if n['kind']in ['entry','date'] and not n['text'].strip():reason='empty_date_or_container'
  elif n['kind']=='section' and pure_label(n['text']):reason='exact_pure_label'
  elif n['kind']=='entry' and pure_label(n['text']) and all(not c['text'].strip() for c in doc['nodes'] if c['parent']==n['id'] and c['kind']=='date'):reason='exact_pure_label'
  if reason:out['decorations'].append({'id':n['id'],'kind':n['kind'],'text':n['text'],'reason':reason});continue
  typing=intent_type(doc,n)
  if typing=='pure_job_intent':
   m=INTENT_PREFIX.match(n['text'].strip());value=n['text'].strip()[m.end():]if m else n['text'].strip()
   out['intents'].append({'id':n['id'],'kind':n['kind'],'text':n['text'],'text_sha256':text_hash(n['text']),'reason':typing,'components':goal_components(doc,value),'personal_qualification_certified':False,'employer_is_personal_experience':False});continue
  if typing=='intent_typing_ambiguous':out['typing_ambiguities'].append({'id':n['id'],'text':n['text'],'reason':typing,'kept_in_review':True})
  context=[];parent=n['parent']
  while parent:
   a=next(x for x in doc['nodes'] if x['id']==parent);context.append({'id':a['id'],'kind':a['kind'],'text':a['text'],'purpose':a['purpose']})
   if a['kind']=='entry':context.extend({'id':c['id'],'kind':'date','text':c['text']} for c in doc['nodes'] if c['parent']==a['id'] and c['kind']=='date')
   parent=a['parent']
  out['facts'].append({'id':n['id'],'kind':n['kind'],'original_sentence':n['text'],'text_sha256':text_hash(n['text']),'parent':n['parent'],'role_context':context,'typing_reason':typing or 'personal_or_unclassified_assertion','all_assertions_in_unit_require_review':True})
 return out

def claim_manifest(doc):return classification(doc)['facts']
