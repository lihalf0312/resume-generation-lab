"""Stage responsibility, not a factual/natural-language quality judge."""
ALLOWED_EDITORS={'automatic_structure','Codex-assisted semantic editing','human_pending'}
def synthetic_mark_review(*,synthetic,stage,has_mark):
 if not synthetic:return {'applicable':False,'factual_error':False,'delivery_issue':False,'reason':'real users do not receive a synthetic marker by default'}
 if stage=='generation':return {'applicable':False,'factual_error':False,'delivery_issue':False,'reason':'marker is added by delivery, not required in frozen model draft'}
 if stage!='delivery':raise ValueError('explicit stage required')
 return {'applicable':True,'factual_error':False,'delivery_issue':not has_mark,'reason':'delivery-layer responsibility'}
def clarification_review(*,answer_changes_truth,used_disputed_claim,safe_omission,answered=False):
 if answered:return {'status':'answered','blocks_delivery':False,'class':'resolved'}
 necessary=bool(answer_changes_truth)
 return {'status':'awaiting_user' if necessary else 'optional','class':'necessary' if necessary else 'optional_enhancement','blocks_delivery':bool(necessary and used_disputed_claim and not safe_omission),'safe_draft_allowed':bool(not used_disputed_claim or safe_omission)}
def tail_review(*,mapping_ok,kind,lines,width_ratio):
 if not mapping_ok:return {'kind':'mapping_failure','defect_confirmed':False,'review':'repair measurement before judging typography'}
 if kind!='bullet' or lines<2:return {'kind':'not_multiline_prose','defect_confirmed':False}
 if width_ratio<.15:return {'kind':'very_short_prose_tail','defect_confirmed':False,'review':'visual/editorial review, never filler or smaller type'}
 return {'kind':'short_tail_advisory' if width_ratio<.5 else 'normal','defect_confirmed':False}

REVIEW_CATEGORIES={'source_support_gap','factual_contradiction','responsibility_expansion','reasonable_paraphrase','pending_ambiguity','reasonable_omission','important_evidence_omission','expression','test_protocol','citation_integrity','job_fit_gap','positive_observation','duplicate'}
SPEECH_ACTS={'error_allegation','neutral_observation','positive_observation','expression_suggestion'}

def validate_observation(record):
 """Validate declared review record shape; never infer truth or other states."""
 if not isinstance(record,dict):raise ValueError('review observation must be an object')
 if not isinstance(record.get('category'),str) or record['category'] not in REVIEW_CATEGORIES:raise ValueError('unsupported review category')
 if not isinstance(record.get('speech_act'),str) or record['speech_act'] not in SPEECH_ACTS:raise ValueError('unsupported review speech_act')
 for field in ('defect_confirmed','original_problem_detected'):
  if field not in record or record[field] is not None and type(record[field]) is not bool:raise ValueError(field+' must be true, false or null')
 if type(record.get('human_judgment_required')) is not bool:raise ValueError('human_judgment_required must be explicitly true or false')
 if not isinstance(record.get('reason'),str) or not record['reason'].strip():raise ValueError('review observation requires a reason')
 return {'declared_record_shape_valid':True,'semantic_verification_passed':None,'independent_fields_not_inferred':True}

SYNTHETIC_MARKER='SYNTHETIC SAMPLE | NOT A REAL CANDIDATE'

def delivery_invariants(rows,source):
 """Check declared delivery presentation, never source truth or job fit."""
 if type(source.get('synthetic')) is not bool:raise ValueError('delivery requires explicit synthetic true or false')
 role=source.get('target_role')
 if not isinstance(role,str) or not role.strip():raise ValueError('delivery requires a target role')
 def display(row):
  return (row.get('label','')+' ' if row.get('label') else '')+row['text']+(' | '+row['date'] if row.get('date') else '')
 markers=[r for r in rows if r.get('id')=='synthetic-marker' or r.get('kind')=='marker' or r.get('text')==SYNTHETIC_MARKER]
 if source['synthetic']:
  if len(markers)!=1 or markers[0].get('id')!='synthetic-marker' or markers[0].get('kind')!='marker' or display(markers[0])!=SYNTHETIC_MARKER:raise ValueError('synthetic delivery requires exactly the unchanged synthetic marker')
 elif markers:raise ValueError('real delivery must not contain an automatic synthetic marker')
 targets=[r for r in rows if r.get('id')=='target' or r.get('text','').startswith('Target:')]
 if len(targets)!=1 or targets[0].get('id')!='target' or targets[0].get('kind')!='contact' or display(targets[0])!='Target: '+role:raise ValueError('delivery Target line must exactly match intended role and prefix')
 return {'synthetic_marker_delivery_check':True,'target_intent_delivery_check':True,'source_truth_verified':None}
