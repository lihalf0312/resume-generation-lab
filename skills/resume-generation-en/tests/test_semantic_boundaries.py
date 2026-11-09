"""Declaration boundary regressions; not automatic natural-language detection."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import review_rules as r
class SemanticBoundaries(unittest.TestCase):
 def test_synthetic_relation_matrix(self):
  data=json.loads(Path(__file__).with_name('semantic-boundary-fixtures.synthetic.json').read_text())
  self.assertTrue(data['synthetic']);self.assertEqual(len(data['cases']),20)
  for case in data['cases']:
   with self.subTest(case=case):
    got=r.semantic_boundary_review(**{k:v for k,v in case.items() if k!='expected_category'})
    self.assertEqual(got['declared_category'],case['expected_category'])
    self.assertIsNone(got['semantic_verification_passed']);self.assertTrue(got['human_judgment_required'])
 def test_invalid_annotations_fail_closed(self):
  for key in ['source_kind','claim_kind','support_state']:
   for value in [None,True,[],{},'unknown']:
    with self.subTest(key=key,value=value):
     args={'source_kind':'record_identifier','claim_kind':'scheduling_support','support_state':'absent'};args[key]=value
     with self.assertRaises(ValueError):r.semantic_boundary_review(**args)
 def test_checker_is_not_word_filter(self):
  got=r.semantic_boundary_review(source_kind='record_identifier',claim_kind='efficiency_outcome',support_state='explicit')
  self.assertIsNone(got['declared_category']);self.assertIsNone(got['semantic_verification_passed'])
 def test_literal_citation_does_not_establish_personal_actor(self):
  import runtime
  source={'material_text':'The project budget ceiling was 250 credits.'}
  analysis={'editor':'Codex-assisted semantic editing','facts':[{'id':'f1','statement':source['material_text'],'source_fragments':[{'field':'material_text','start':0,'end':len(source['material_text']),'quote':source['material_text']}]}],'selection':[],'questions':[],'claim_map':[{'paragraph_id':'s0.i0.b0','candidate_wording':'Maintained the project expense ledger.','fact_ids':['f1']}]}
  runtime.citations(analysis,source)  # Valid citation shape is deliberately not a semantic verdict.
  got=r.semantic_boundary_review(source_kind='budget_constraint',claim_kind='personal_recordkeeping',support_state='absent')
  self.assertEqual(got['declared_category'],'source_support_gap')
  self.assertIsNone(got['semantic_verification_passed'])
if __name__=='__main__':unittest.main(verbosity=2)
