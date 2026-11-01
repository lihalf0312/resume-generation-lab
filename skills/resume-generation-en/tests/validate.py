"""Offline invariant checks, not a resume quality or renderer certification."""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import onepage as w
import date_wrap_repair as repair
import scope_contract as scope
import review_rules as review
import runtime

class Invariants(unittest.TestCase):
    def test_synthetic_marker_and_target_intent(self):
        source={'name':'Example','target_role':'Analyst','sections':[]}
        rows=w.flatten(source)
        self.assertEqual(rows[1]['text'],'Target: Analyst')
        self.assertFalse(any(p['kind']=='marker' for p in rows))
        source['synthetic']=True
        self.assertEqual(sum(p['kind']=='marker' for p in w.flatten(source)),1)

    def test_award_precision_and_status(self):
        for award,expected in [('June','Sep 2020 – Jun 2023 (awarded)'),('July','Sep 2020 – Jun 2023; awarded Jul 2023')]:
            rows=[{'id':'e','kind':'entry','text':'BSc, Example College','date':'September 2020 – June 2023; awarded '+award+' 2023','section':0,'item':0}]
            out,changes=w.automatic_structure(rows)
            self.assertEqual(out[0]['date'],expected)
            self.assertIn('September',rows[0]['date'])
            self.assertTrue(all(x['class']=='automatic_structure' and x['semantic_quality_pass'] is None for x in changes))

    def test_label_fold_preserves_unique_information_and_capitals(self):
        rows=[{'id':'s0','kind':'section','text':'Tools','section':0},{'id':'e','kind':'entry','text':'Document Workflow','section':0,'item':0},{'id':'b','kind':'bullet','text':'Git and Markdown','section':0,'item':0}]
        out,_=w.automatic_structure(rows)
        self.assertEqual(out[-1]['label'],'Document Workflow:')
        self.assertEqual(out[-1]['text'],'Git and Markdown')
        self.assertFalse(any(p['kind']=='entry' for p in out))

    def test_semantic_patch_requires_exact_spans_and_current_text(self):
        rows=[{'id':'b','kind':'bullet','text':'Checked 12 guides.'}]
        src={'material_text':'Checked 12 workshop guides.','jd_text':'Check guides.'}
        op={'paragraph_id':'b','action':'replace','before':'Checked 12 guides.','after':'Checked 12 workshop guides.','reason':'Preserve source scope','source_fragments':[{'field':'material_text','start':0,'end':len(src['material_text']),'quote':src['material_text']}]}
        d={'editor':'Codex-assisted semantic editing','operations':[op]}
        out,changes=w.apply_semantic(rows,d,src)
        self.assertEqual(out[0]['text'],src['material_text']);self.assertEqual(rows[0]['text'],'Checked 12 guides.')
        op['source_fragments'][0]['quote']='Checked12workshopguides.'
        with self.assertRaises(ValueError):w.apply_semantic(rows,d,src)
        op['source_fragments'][0]['quote']=src['material_text'];op['source_fragments'][0]['end']=999
        with self.assertRaises(ValueError):w.apply_semantic(rows,d,src)
        op['source_fragments'][0]['end']=len(src['material_text']);op['before']='another version'
        with self.assertRaises(ValueError):w.apply_semantic(rows,d,src)

    def test_initial_source_interval_and_local_network_guard(self):
        source={'material_text':'Example','jd_text':'Example role'}
        analysis={'editor':'Codex-assisted semantic editing','facts':[{'id':'f1','statement':'Example','source_fragments':[{'field':'material_text','start':0,'end':7,'quote':'Example'}]}],'selection':[],'questions':[],'claim_map':[{'paragraph_id':'name','fact_ids':['f1']}]}
        runtime.citations(analysis,source)
        analysis['facts'][0]['source_fragments'][0]['end']=99
        with self.assertRaises(runtime.WorkflowError):runtime.citations(analysis,source)
        import socket
        sys.addaudithook(runtime.offline)
        before=runtime.GUARD_COUNTS['blocked_python_network_events']
        with self.assertRaises(runtime.WorkflowError):socket.socket()
        self.assertEqual(runtime.GUARD_COUNTS['blocked_python_network_events'],before+1)

    def analysis_fixture(self):
        import copy
        source={'material_text':'Example','jd_text':'Example role'}
        analysis={'editor':'Codex-assisted semantic editing','facts':[{'id':'f1','statement':'Example','source_fragments':[{'field':'material_text','start':0,'end':7,'quote':'Example'}]}],'selection':[{'fact_ids':['f1'],'decision':'adopt'}],'questions':[{'affected_fact_ids':['f1'],'necessary':True,'status':'awaiting_user','answer':None}],'claim_map':[{'paragraph_id':'name','fact_ids':['f1']}]}
        return copy.deepcopy(analysis),source

    def test_selection_reference_integrity(self):
        analysis,source=self.analysis_fixture();runtime.citations(analysis,source)
        for invalid in (None,[],['missing'],'f1',[1]):
            with self.subTest(invalid=invalid):
                analysis['selection'][0]['fact_ids']=invalid
                with self.assertRaises(runtime.WorkflowError):runtime.citations(analysis,source)
        analysis['selection'][0]={}
        with self.assertRaises(runtime.WorkflowError):runtime.citations(analysis,source)

    def test_question_reference_integrity_and_empty_new_information(self):
        analysis,source=self.analysis_fixture();runtime.citations(analysis,source)
        analysis['questions'][0]['affected_fact_ids']=[];runtime.citations(analysis,source)
        for invalid in (None,['missing'],'f1',[1]):
            with self.subTest(invalid=invalid):
                analysis['questions'][0]['affected_fact_ids']=invalid
                with self.assertRaises(runtime.WorkflowError):runtime.citations(analysis,source)
        for record in ({},{'affected_facts':['f1']},{'affected_fact_ids':['f1'],'affected_facts':[]}):
            analysis['questions']=[record]
            with self.assertRaises(runtime.WorkflowError):runtime.citations(analysis,source)

    def test_analysis_collections_and_fact_ids(self):
        for key in ('facts','selection','questions','claim_map'):
            analysis,source=self.analysis_fixture();analysis[key]={}
            with self.subTest(key=key):
                with self.assertRaises(runtime.WorkflowError):runtime.citations(analysis,source)
        analysis,source=self.analysis_fixture();analysis['facts'][0]['id']=''
        with self.assertRaises(runtime.WorkflowError):runtime.citations(analysis,source)

    def test_review_states_are_independent_declarations(self):
        observation={'category':'pending_ambiguity','speech_act':'neutral_observation','defect_confirmed':None,'original_problem_detected':False,'human_judgment_required':True,'reason':'Pending independent source judgment'}
        result=review.validate_observation(observation)
        self.assertIsNone(result['semantic_verification_passed'])
        observation['original_problem_detected']=True
        self.assertTrue(review.validate_observation(observation)['independent_fields_not_inferred'])
        for field,value in (('defect_confirmed',1),('original_problem_detected','yes'),('human_judgment_required',None),('speech_act','automatic factual pass')):
            invalid=dict(observation);invalid[field]=value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):review.validate_observation(invalid)
        invalid=dict(observation);del invalid['original_problem_detected']
        with self.assertRaises(ValueError):review.validate_observation(invalid)

    def date_edit_fixture(self):
        source={'material_text':'Volunteer at Example Lab from January 2021 to June 2022.','jd_text':'Assist a documentation team.'}
        row={'id':'e','kind':'entry','text':'Volunteer, Example Lab','date':'Jan 2021 – Jun 2023'}
        op={'paragraph_id':'e','action':'replace','before':w.ptext(row),'after_date':'Jan 2021 – Jun 2022','reason':'Correct the entered end year to match the literal source period','source_fragments':[{'field':'material_text','start':0,'end':len(source['material_text']),'quote':source['material_text']}]}
        return [row],{'editor':'Codex-assisted semantic editing','operations':[op]},source

    def test_source_linked_entry_date_correction_and_logs(self):
        rows,decision,source=self.date_edit_fixture()
        out,changes=w.apply_semantic(rows,decision,source)
        self.assertEqual(out[0]['date'],'Jan 2021 – Jun 2022')
        self.assertEqual(out[0]['text'],rows[0]['text'])
        self.assertEqual(rows[0]['date'],'Jan 2021 – Jun 2023')
        self.assertEqual(changes[0]['before_row']['date'],rows[0]['date'])
        self.assertEqual(changes[0]['after_row']['date'],out[0]['date'])
        self.assertEqual(changes[0]['before'],w.ptext(rows[0]))
        decision['operations'][0]['after']='Volunteer at Example Lab'
        combined,_=w.apply_semantic(rows,decision,source)
        self.assertEqual(combined[0]['text'],'Volunteer at Example Lab')
        self.assertEqual(combined[0]['date'],'Jan 2021 – Jun 2022')
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'corrected';w.build(folder,out)
            self.assertEqual(w.Document(folder/'resume.docx').paragraphs[0].text,'Volunteer, Example Lab\tJan 2021 – Jun 2022')

    def test_date_edit_rejects_row_action_and_types(self):
        for value in (None,2022,['Jun 2022'],True):
            rows,decision,source=self.date_edit_fixture();decision['operations'][0]['after_date']=value
            with self.subTest(value=value):
                with self.assertRaises(ValueError):w.apply_semantic(rows,decision,source)
        for kind in ('bullet','section','contact','name'):
            rows,decision,source=self.date_edit_fixture();rows[0]['kind']=kind
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):w.apply_semantic(rows,decision,source)
        rows,decision,source=self.date_edit_fixture();decision['operations'][0]['action']='remove'
        with self.assertRaises(ValueError):w.apply_semantic(rows,decision,source)
        rows,decision,source=self.date_edit_fixture();decision['operations'][0]['after']=None
        with self.assertRaises(ValueError):w.apply_semantic(rows,decision,source)

    def test_date_edit_requires_current_before_and_literal_material(self):
        rows,decision,source=self.date_edit_fixture();decision['operations'][0]['before']=rows[0]['text']
        with self.assertRaises(ValueError):w.apply_semantic(rows,decision,source)
        rows,decision,source=self.date_edit_fixture();decision['operations'][0]['source_fragments']=[{'field':'jd_text','start':0,'end':len(source['jd_text']),'quote':source['jd_text']}]
        with self.assertRaises(ValueError):w.apply_semantic(rows,decision,source)
        rows,decision,source=self.date_edit_fixture();decision['operations'][0]['source_fragments'][0]['quote']=source['material_text'].replace('2022','2023')
        with self.assertRaises(ValueError):w.apply_semantic(rows,decision,source)
        rows,decision,source=self.date_edit_fixture();decision['operations'][0]['source_fragments'][0]['end']+=1
        with self.assertRaises(ValueError):w.apply_semantic(rows,decision,source)

    def test_delivery_marker_and_target_positive(self):
        for synthetic in (True,False):
            source={'synthetic':synthetic,'target_role':'Analyst'}
            rows=w.flatten({'name':'Example','synthetic':synthetic,'target_role':'Analyst','sections':[]})
            result=review.delivery_invariants(rows,source)
            self.assertTrue(result['synthetic_marker_delivery_check'])
            self.assertTrue(result['target_intent_delivery_check'])
            self.assertIsNone(result['source_truth_verified'])

    def test_delivery_marker_removal_mutation_duplicate_and_real_injection(self):
        import copy
        source={'synthetic':True,'target_role':'Analyst'}
        rows=w.flatten({'name':'Example','synthetic':True,'target_role':'Analyst','sections':[]})
        marker=next(r for r in rows if r['id']=='synthetic-marker')
        variants=[[r for r in rows if r['id']!='synthetic-marker']]
        mutated=copy.deepcopy(rows);next(r for r in mutated if r['id']=='synthetic-marker')['text']='Sample';variants.append(mutated)
        variants.append(rows+[dict(marker,id='extra-marker')])
        for variant in variants:
            with self.assertRaises(ValueError):review.delivery_invariants(variant,source)
        with self.assertRaises(ValueError):review.delivery_invariants(rows,dict(source,synthetic=False))

    def test_delivery_target_removal_mutation_wrong_kind_and_duplicate(self):
        import copy
        source={'synthetic':False,'target_role':'Analyst'}
        rows=w.flatten({'name':'Example','synthetic':False,'target_role':'Analyst','sections':[]})
        target=next(r for r in rows if r['id']=='target')
        variants=[[r for r in rows if r['id']!='target']]
        for field,value in (('text','Analyst'),('text','Target: Different role'),('kind','entry')):
            variant=copy.deepcopy(rows);next(r for r in variant if r['id']=='target')[field]=value;variants.append(variant)
        variants.append(rows+[dict(target,id='another-target')])
        for variant in variants:
            with self.assertRaises(ValueError):review.delivery_invariants(variant,source)

    def test_style_invariants_and_real_marker_absence(self):
        rows=w.flatten({'name':'Example','target_role':'Assistant','sections':[{'heading':'Experience','items':[{'heading':'Volunteer, Example Lab','date':'Jan 2024 – Jun 2024','bullets':['Checked workshop guides']}]}]})
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'v00';w.build(folder,rows)
            self.assertEqual(w.core(folder/'resume.docx'),w.core(Path(w.__file__).resolve().parent.parent/'assets/blank-english-template.docx'))
            self.assertNotIn('SYNTHETIC SAMPLE',(folder/'resume.txt').read_text())
            with self.assertRaises(FileExistsError):w.build(folder,rows)

    def test_scope_and_tail_are_not_semantic_proofs(self):
        result=scope.compare_scope({'actor':'team','phase':'pilot'},{'actor':'individual','phase':'production'})
        self.assertEqual(len(result['declared_scope_differences']),2)
        self.assertIsNone(result['semantic_verification_passed'])
        self.assertFalse(review.tail_review(mapping_ok=True,kind='bullet',lines=2,width_ratio=.1)['defect_confirmed'])
        self.assertTrue(review.clarification_review(answer_changes_truth=True,used_disputed_claim=True,safe_omission=False)['blocks_delivery'])
        self.assertFalse(review.clarification_review(answer_changes_truth=True,used_disputed_claim=False,safe_omission=True)['blocks_delivery'])

if __name__=='__main__':unittest.main(verbosity=2)
