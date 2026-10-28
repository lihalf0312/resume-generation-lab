import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from resume_pipeline.core import OriginalSkillAdapter, load_records
from resume_pipeline.format_contract import assess_format_report
from resume_pipeline.preferences import merge_preferences

ROOT=Path(__file__).resolve().parents[1]
class SkillAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'skills/resume-generation',self.root/'skill')
        self.path=self.root/'skill/SKILL.md';self.adapter=OriginalSkillAdapter(self.path)
        records=load_records(ROOT/'fixtures/synthetic.jsonl');self.profile,self.job=records[0],records[-1]
        self.defaults=json.loads((self.root/'skill/assets/resume-preferences.json').read_text())
    def tearDown(self):self.tmp.cleanup()
    def bundle(self,adapter=None):return (adapter or self.adapter).prepare(self.profile,self.job,{},'en')
    def test_actual_public_skill_and_reference_hashes(self):
        b=self.bundle()
        self.assertEqual(b['skill_sha256'],hashlib.sha256(self.path.read_bytes()).hexdigest())
        for name,h in b['skill_reference_hashes'].items():self.assertEqual(h,hashlib.sha256((self.path.parent/name).read_bytes()).hexdigest())
        self.assertIn('assets/resume-preferences.json',b['skill_reference_hashes'])
        self.assertEqual(b['source_preferences'],self.defaults)
    def test_precedence_default_template_confirmed_current(self):
        adapter=OriginalSkillAdapter(self.path,template_preferences={'layout':{'target_pages':2,'dates_bold':False}},confirmed_preferences={'layout':{'target_pages':3}},current_overrides={'layout':{'target_pages':4,'page_size':'Letter'}})
        b=self.bundle(adapter);l=b['resolved_preferences']['layout']
        self.assertEqual(l['target_pages'],4);self.assertEqual(l['page_size'],'Letter');self.assertFalse(l['dates_bold'])
        self.assertEqual(self.defaults['layout']['target_pages'],1)
    def test_no_language_inference_and_chinese_alias(self):
        with self.assertRaises(ValueError):self.adapter.prepare(self.profile,self.job,{})
        with self.assertRaises(ValueError):self.adapter.prepare(self.profile,self.job,{},'zh')
        self.profile['facts_zh']=['虚构练习一。','虚构练习二。']
        self.assertEqual(self.adapter.prepare(self.profile,self.job,{},'zh')['language'],'zh-CN')
        a=OriginalSkillAdapter(self.path,current_overrides={'output_languages':['en']})
        self.assertEqual(a.prepare(self.profile,self.job,{})['language'],'en')
        with self.assertRaises(ValueError):a.prepare(self.profile,self.job,{},'zh-CN')
    def test_missing_config_or_required_ref_fails(self):
        for name in ('assets/resume-preferences.json','references/workspace.md','references/layout-and-qa.md'):
            p=self.path.parent/name;data=p.read_bytes();p.unlink()
            with self.assertRaises(FileNotFoundError):self.bundle()
            p.write_bytes(data)
    def test_malformed_config_unknown_keys_and_executable_paths_fail(self):
        p=self.path.parent/'assets/resume-preferences.json';p.write_text('{broken')
        with self.assertRaises(ValueError):self.bundle()
        p.write_text(json.dumps(self.defaults))
        for patch in ({'execute':'shell command'},{'template_paths':{'en':'script.py'}},{'template_paths':{'en':'../private.docx'}},{'layout':{'target_pages':True}},{'versioning':{'overwrite_delivered_versions':True}}):
            with self.assertRaises(ValueError):self.bundle(OriginalSkillAdapter(self.path,current_overrides=patch))
    def test_generic_fallback_not_template_fidelity(self):
        b=self.bundle();c=b['format_contract']
        self.assertEqual(c['layout_mode'],'generic_single_column_unrendered')
        self.assertFalse(c['template_fidelity_verified']);self.assertFalse(b['final_artifact_generated'])
        self.assertEqual(b['format_status']['status'],'not_assessed')
        for f in self.profile['facts']:self.assertIn(f,b['grounded_content_draft'])
    def report(self):
        return {'language':'en','page_count':1,'paper':'A4','blank_padding_used':False,
                'unauthorized_font_shrink_used':False,'dates_bold':True,'graduation_label_and_value_bold':True,
                'bullet_alignment_verified':True,'same_final_docx_content':True,'body_area_checked':True,
                'clipping_or_hidden_content':False,'heading_lines':'bottom_only',
                'generic_spacing_parameters_recorded':True,'punctuation_compression_issue_detected':False,
                'pdf_selectable_text':True,'docx_to_pdf_compatible':True,'all_final_pages_rendered':True,
                'pdf_export_engine':'LibreOffice','paragraph_last_line_ratios':[.7],
                'docx_sha256':'a'*64,'pdf_sha256':'b'*64,'render_evidence_sha256':'c'*64,
                'renderer_version':'synthetic-report','extractor_version':'synthetic-report'}
    def test_equivalent_renderer_report_not_actual_proof(self):
        r=assess_format_report(self.report(),self.bundle()['format_contract'])
        self.assertEqual(r['status'],'reported_pass');self.assertFalse(r['actual_style_verified'])
        self.assertFalse(r['word_specific_properties_verified']);self.assertFalse(r['export_ready'])
    def test_docx_only_still_requires_all_pages_rendered(self):
        a=OriginalSkillAdapter(self.path,current_overrides={'formats':['docx']})
        c=self.bundle(a)['format_contract'];r=self.report();r['all_final_pages_rendered']=False
        self.assertEqual(assess_format_report(r,c)['status'],'fail')
        del r['all_final_pages_rendered']
        self.assertEqual(assess_format_report(r,c)['status'],'not_assessed')
    def test_strict_half_line_default_and_explicit_override(self):
        report=self.report();report['paragraph_last_line_ratios']=[.5]
        self.assertEqual(assess_format_report(report,self.bundle()['format_contract'])['status'],'fail')
        a=OriginalSkillAdapter(self.path,current_overrides={'layout':{'body_last_line_min_exclusive':False}})
        self.assertEqual(assess_format_report(report,self.bundle(a)['format_contract'])['status'],'reported_pass')
    def test_template_spacing_and_conditional_compression(self):
        a=OriginalSkillAdapter(self.path,current_overrides={'template_paths':{'en':'templates/authorized.docx'}})
        c=self.bundle(a)['format_contract'];r=self.report();r['template_spacing_preserved']=True
        r['autoSpaceDE']=False;r['autoSpaceDN']=False
        self.assertEqual(assess_format_report(r,c)['status'],'reported_pass')
        r['punctuation_compression_issue_detected']=True
        self.assertEqual(assess_format_report(r,c)['status'],'not_assessed')
        r['doNotCompress_punctuation']=True
        self.assertEqual(assess_format_report(r,c)['status'],'reported_pass')

if __name__=='__main__':unittest.main()
