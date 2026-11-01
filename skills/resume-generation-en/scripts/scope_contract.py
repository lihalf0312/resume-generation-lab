"""Compare declared claim scope, never infer truth from keywords or annotations.
The caller must independently read source and candidate prose. Passing this
contract is NOT textual entailment, factual acceptance, or a writing-quality pass.
"""
FIELDS=('actor','object','metric_basis','population','location','dataset','phase')
def compare_scope(source_claim,candidate_claim):
 if not candidate_claim.get('asserted',True):return {'declared_scope_differences':[],'safe_omission_declared':True,'semantic_verification_passed':None,'independent_text_review_required':True}
 differences=[]
 for f in FIELDS:
  value=source_claim.get(f)
  if value is not None and candidate_claim.get(f)!=value:differences.append({'field':f,'source':value,'candidate':candidate_claim.get(f),'judgment':'scope changed or missing; review prose and source'})
 return {'declared_scope_differences':differences,'semantic_verification_passed':None,'independent_text_review_required':True,'annotation_fidelity_not_verified':True}
