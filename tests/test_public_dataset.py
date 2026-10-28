import copy
import json
from pathlib import Path
import tempfile
import unittest
from resume_pipeline.public_dataset import (derive_sources,derive_evaluation,validate_public_dataset,
    PublicSourceError,_validate_review,REVIEW_FIELDS)


def sources():
    return ({'case_id':'case-001','identity_id':'fictional-1','source_family':'toy-lineage',
      'creation_batch':'toy','synthetic':True,'publication':'public','license':'CC0-1.0',
      'sector':'toy category','uncertainties':[{'safe_handling':'toy note'}],
      'facts':[{'id':'F01','kind':'project','en':'Checked 2 records.','zh':'核对2条记录。','provenance':'toy note'}]},
      {'case_id':'case-001','synthetic':True,'title':{'en':'Toy role','zh':'练习岗位'},
       'requirements':[{'id':'R01','en':'Check records.','zh':'核对记录。','evidence_status':'toy','supporting_fact_ids':['F01']}]})


def raw_review():
    return {'case_id':'case-001','factual_fidelity':'needs_review','overall_score':None,
      'dimensions':{'jd_relevance':{'rating':3},'clarity':{'rating':2},
       'supported_achievements':{'rating':3},'format_readability':{'rating':None}},
      'claim_audit':'OMITTED_TEST_SENTINEL',
      'requirement_coverage':'OMITTED_TEST_SENTINEL',
      'hashes':{'private':'a'*64},'blinding':{'internal':True}}


def score_view(raw=None,**kw):
    return derive_evaluation(raw or raw_review(),brief_feedback_zh='表述范围需要澄清。',
      brief_feedback_en='Clarify the scope of the wording.',**kw)


class PublicDatasetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.case=self.root/'data/development-140/case-001';self.case.mkdir(parents=True)
        p,j=sources();s=derive_sources(p,j)
        self.write('profile.public.json',s['profile']);self.write('job.public.json',s['job'])
        self.write('evaluation.public.json',score_view())
        for n in ['resume.en.md','resume.zh.md']:(self.case/n).write_text('Fictional toy resume.\n')
        self.index=self.case.parent/'index.json';self.index.write_text(json.dumps({'schema_version':
          'development-public-v4','case_count':1,'cases':[{'case_id':'case-001','path':'data/development-140/case-001'}]}))
    def tearDown(self):self.tmp.cleanup()
    def write(self,n,v):(self.case/n).write_text(json.dumps(v,ensure_ascii=False))
    def check(self):return validate_public_dataset(self.root)
    def mutate(self,n,fn):
        p=self.case/n;j=json.loads(p.read_text());fn(j);self.write(n,j)
    def test_valid_five_file_dataset(self):
        r=self.check();self.assertEqual((r['cases'],r['source_files'],r['resumes'],r['evaluations']),(1,2,2,1))
    def test_source_text_preserved_annotations_omitted(self):
        p,j=sources();old=copy.deepcopy([p,j]);v=derive_sources(p,j);self.assertEqual([p,j],old)
        self.assertEqual(v['profile']['facts'][0]['en'],p['facts'][0]['en']);self.assertNotIn('sector',v['profile'])
        self.assertNotIn('evidence_status',v['job']['requirements'][0])
    def test_actual_ratings_and_null_preserved(self):
        v=score_view();self.assertIsNone(v['overall_score']);self.assertEqual([x['rating'] for x in v['dimension_ratings']],[3,2,3,None])
    def test_detailed_reviews_never_copied(self):
        raw=raw_review();before=copy.deepcopy(raw);v=score_view(raw);self.assertEqual(raw,before)
        self.assertEqual(set(v),REVIEW_FIELDS)
        text=json.dumps(v);self.assertNotIn('OMITTED_TEST_SENTINEL',text);self.assertNotIn('F01',text);self.assertNotIn('R01',text)
    def test_negative_status_and_brief_comment_preserved(self):
        v=score_view();self.assertEqual(v['factual_status'],'needs_review');self.assertEqual(v['brief_feedback_en'],'Clarify the scope of the wording.')
    def test_dispute_flag_not_rescore(self):
        v=score_view(disputed_label=True);self.assertTrue(v['disputed_label']);self.assertEqual(v['factual_status'],'needs_review')
    def test_nonnull_overall_score_rejected(self):
        raw=raw_review();raw['overall_score']=99
        with self.assertRaises(PublicSourceError):score_view(raw)
    def test_unknown_review_keys_rejected(self):
        for key in ['claim_audit','requirement_coverage','source_fact_ids','hashes','reason']:
            v=score_view();v[key]=[]
            with self.assertRaises(PublicSourceError):_validate_review(v)
    def test_nested_rating_metadata_rejected(self):
        v=score_view();v['dimension_ratings'][0]['evidence_ids']=['toy']
        with self.assertRaises(PublicSourceError):_validate_review(v)
    def test_internal_references_rejected_in_comments(self):
        for text in ['See F01 and R01.','claim_audit result','ledger detail','/workspace/private','file.json']:
            v=score_view();v['brief_feedback_en']=text
            with self.assertRaises(PublicSourceError):_validate_review(v)
    def test_brief_length_and_embedded_json_rejected(self):
        for text in ['x'*401,'{"private":"detail"}','line\nbreak']:
            v=score_view();v['brief_feedback_en']=text
            with self.assertRaises(PublicSourceError):_validate_review(v)
    def test_scores_labels_scales_strict(self):
        for field,bad in [('rating',5),('rating',True),('scale_max',100),('label_en','Different')]:
            v=score_view();v['dimension_ratings'][0][field]=bad
            with self.assertRaises(PublicSourceError):_validate_review(v)
    def test_extra_case_file_rejected(self):
        (self.case/'notes.json').write_text('{}')
        with self.assertRaises(PublicSourceError):self.check()
    def test_missing_or_empty_resume_rejected(self):
        p=self.case/'resume.en.md';p.write_text(' ')
        with self.assertRaises(PublicSourceError):self.check()
        p.unlink()
        with self.assertRaises(PublicSourceError):self.check()
    def test_symlink_source_rejected(self):
        p=self.case/'profile.public.json';data=p.read_bytes();p.unlink();q=self.root/'other';q.write_bytes(data);p.symlink_to(q)
        with self.assertRaises(PublicSourceError):self.check()
    def test_traversal_case_path_rejected(self):
        j=json.loads(self.index.read_text());j['cases'][0]['path']='data/../case-001';self.index.write_text(json.dumps(j))
        with self.assertRaises(PublicSourceError):self.check()
    def test_duplicate_or_unlisted_cases_rejected(self):
        (self.case.parent/'notes.json').write_text('{}')
        with self.assertRaises(PublicSourceError):self.check()
        (self.case.parent/'notes.json').unlink();j=json.loads(self.index.read_text());j['cases']*=2;j['case_count']=2;self.index.write_text(json.dumps(j))
        with self.assertRaises(PublicSourceError):self.check()
    def test_case_identity_mismatch_rejected(self):
        self.mutate('evaluation.public.json',lambda j:j.update(case_id='case-002'))
        with self.assertRaises(PublicSourceError):self.check()
    def test_source_design_key_rejected(self):
        self.mutate('profile.public.json',lambda j:j.update(fit_type='toy'))
        with self.assertRaises(PublicSourceError):self.check()
    def test_duplicate_json_and_limits_rejected(self):
        v=score_view();v['review_limitations'].append('Other internal note')
        with self.assertRaises(PublicSourceError):_validate_review(v)
        (self.case/'evaluation.public.json').write_text('{"case_id":"a","case_id":"b"}')
        with self.assertRaises(PublicSourceError):self.check()


if __name__=='__main__':unittest.main()
