"""Explicit schemas on every stage. No provider client, keys, or live entry point."""
from pathlib import Path
from .schemas import SCHEMAS,VERSION,MAX_REVIEW_FACTS,MAX_BILINGUAL_FACTS,NOTE_MAX,QUOTE_MAX,protocol_hash
from .common import digest
from .citations import catalogue,wire_blocks
from . import document as d
from .versioning import bindings
from .bilingual_semantics import GUIDANCE,validate_request_language
RULES='''Program-classified pure labels, target roles and target employers are NOT personal facts. A target-employer entity from JD metadata proves only the desired application destination, never past employment or qualifications. Preserve mixed factual clauses and ambiguous suffixes in fact_manifest; never add supported judgments to repair missing evidence. Do not return personal check verdicts for program_intents or program_decorations. The delivery header already states the application target; avoid repeating it as a resume section. For typing_ambiguities, never invent personal evidence or return supported with empty evidence: explain the type ambiguity and retain unresolved status; a pure desired job does not require proof that the candidate already held it. Desired jobs may refer to JD without claiming qualifications or past employment. Mixed or ambiguous units remain in fact_manifest: check every factual assertion, including qualifications, tenure and actual roles. Never exempt a whole paragraph because of a Target/求职意向 prefix.
Types guide coverage, not semantic truth. If a supposedly nonpersonal unit hides factual claims, report incomplete coverage and node-ID advice; do not silently certify it.
Personal patch changes require M: references. A change remaining purely intent/label before AND after may use JD: references or none. Moving or changing it into personal assertions requires M: references.
Original material alone supports personal facts. JD is requirements, not experience.
Do not infer actions from a title, third-party work or existence of records. Preserve ability levels,
media, needed/planned/completed status, actor, number/unit, tenure, result scope and qualifications.
Use professional paraphrases when supported; do not add negative audit prose. Ask only material
truth/selection questions. Unanswered conflicts remain awaiting_user; omit disputed claims safely.
Reviews check every factual_manifest ID and all seven facets, not only old issues. Program-classified decorations need no output verdict. Use compact IDs, judgment,
short literal separate evidence fragments; no repeated whole CV. Quote location is not semantic proof.
Repeated quotes stay ambiguous unless literal source ID disambiguates. Never invent offsets.
Patch ONLY replace/delete/move by stable ID, with original hash, reason and source citations.
Submit only operations that actually change text/attribution/order. The program computes affected subtree IDs; do not submit redundant changed-ID declarations. No JSON paths or unrelated changes.
Capacity numbers are actual observations, not guaranteed cuts. Prioritize JD evidence; remove low-value
whole items and redundant skills before wording. Preserve core education, achievements and scope,
including tail-page education. Sparse drafts need selection review, never padding. No font/geometry changes.
Final review covers the whole actual candidate and changed claims; incomplete coverage remains incomplete.
Write only the requested language. Prefer concise, substantial one-page selection, never all source facts.
Review evidence must be compact: usually one short literal fragment per personal claim, notes only for
necessary explanations. Do not output checked_ids/pending_ids/facets lists: program computes coverage. An ambiguous judgment is CHECKED, not pending. Missing judgments remain unchecked, never inferred supported.
Bilingual review is ONE object with language-tagged checks, candidate versions and bounded arrays; no duplicate per-language coverage trees. If capacity is insufficient set complete=false with incomplete_reason; never drop required facts silently. Select M: source IDs for personal evidence; JD: IDs only for job_fit_gaps. Full original blocks are beside IDs. Optional short quotes must match that exact block literally; the program retrieves evidence, not the model. Citation identity is not entailment.
'''

def build(stage,*,skill,material_text,jd_text,candidate=None,capacity=None,issues=None):
 if stage not in SCHEMAS:raise ValueError('unknown_stage')
 if not skill or any(not isinstance(v,str) or not v.strip() for v in skill.values()):raise ValueError('complete_skill_required')
 if stage!='generate' and candidate is None:raise ValueError('current_candidate_required')
 if stage=='patch' and capacity is None:raise ValueError('measured_capacity_required_unknown_fields_allowed')
 context={'skill_files':skill,'source_blocks':wire_blocks(material_text,jd_text),'source_map_sha256':digest(catalogue(material_text,jd_text)),'source_blocks_sha256':digest(wire_blocks(material_text,jd_text)),'protocol_version':VERSION,'protocol_sha256':protocol_hash(),'rules':RULES+GUIDANCE+f'\nAuthoritative limits: explanation notes <= {NOTE_MAX} characters; literal evidence quote <= {QUOTE_MAX}. Prefer short quotes (roughly240) or source_id alone; never truncate evidence or omit fact coverage to fit. Return only schema fields. Extra narrative cannot replace judgments.','output_schema':SCHEMAS[stage],'schema_stage':stage,'version_bindings':bindings(),'template_parameters':{'en':{'body_pt':10.5,'section_pt':12,'name_pt':18,'margin_top_bottom_pt':48.2,'margin_left_right_pt':56.7},'zh':{'body_pt':12,'section_pt':14,'name_pt':18,'margins_pt':28.35,'separators':'confirmed paired independent line objects; unchanged'},'line_spacing':'frozen template; no fit-induced changes','synthetic_marker':'delivery layer only'}}
 if candidate is not None:
  d.validate(candidate);d.validate_intent_context(candidate,jd_text);context.update(candidate=candidate,candidate_version=d.version(candidate),fact_manifest=d.claim_manifest(candidate),program_decorations=d.classification(candidate)['decorations'],program_intents=d.classification(candidate)['intents'],typing_ambiguities=d.classification(candidate)['typing_ambiguities'],classification_sha256=digest(d.classification(candidate)))
  if stage in ['review','final_review'] and len(context['fact_manifest'])>MAX_REVIEW_FACTS:raise ValueError('review_capacity_exceeded_no_partial_request')
 if stage=='patch':context.update(capacity_feedback=capacity,revision_reasons=issues or [])
 # Review never receives generator identity, generation analysis, author oracle or prior verdicts.
 request={'stage':stage,'context':context};preflight(request);return {**request,'input_sha256':digest(request)}

def preflight(request):
 if set(request)!= {'stage','context'}:raise ValueError('undeclared_request_fields')
 c=request['context'];stage=request['stage']
 validate_request_language(c,stage)
 if c.get('output_schema')!=SCHEMAS.get(stage):raise ValueError('schema_drift')
 if any(k in c for k in ['verification','author_ledger','expected_answers','generator_identity','other_jd']):raise ValueError('answer_leakage')
 if c.get('protocol_version')!=VERSION or c.get('protocol_sha256')!=protocol_hash():raise ValueError('protocol_version_or_hash_drift')
 if digest(c.get('source_blocks',[]))!=c.get('source_blocks_sha256'):raise ValueError('source_blocks_changed')
 for b in c['source_blocks']:
  if b['text_sha256']!=__import__('hashlib').sha256(b['text'].encode()).hexdigest() or b['source_type']!=('personal_material' if b['id'].startswith('M:') else 'job_requirement' if b['id'].startswith('JD:') else None):raise ValueError('source_block_type_or_hash_invalid')
 if stage=='bilingual_review':
  if c['candidate_versions']!={k:d.version(v) for k,v in c['candidates'].items()} or c['fact_manifest']!={k:d.claim_manifest(v) for k,v in c['candidates'].items()} or c.get('program_intents')!={k:d.classification(v)['intents'] for k,v in c['candidates'].items()} or c.get('classification_sha256')!={k:digest(d.classification(v)) for k,v in c['candidates'].items()} or c.get('program_decorations')!={k:d.classification(v)['decorations'] for k,v in c['candidates'].items()} or c.get('typing_ambiguities')!={k:d.classification(v)['typing_ambiguities'] for k,v in c['candidates'].items()}:raise ValueError('stale_bilingual_fact_manifest')
 elif stage!='generate':
  if c.get('candidate_version')!=d.version(c['candidate']) or c.get('fact_manifest')!=d.claim_manifest(c['candidate']) or c.get('program_intents')!=d.classification(c['candidate'])['intents'] or c.get('classification_sha256')!=digest(d.classification(c['candidate'])) or c.get('program_decorations')!=d.classification(c['candidate'])['decorations'] or c.get('typing_ambiguities')!=d.classification(c['candidate'])['typing_ambiguities']:raise ValueError('stale_candidate_or_fact_manifest')
 return True

def load_skill(root):
 root=Path(root);return {str(p.relative_to(root)):p.read_text() for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in ['.md','.yaml','.yml','.json','.txt']}
