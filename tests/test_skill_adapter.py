import json
import tempfile
import unittest
from pathlib import Path
from resume_pipeline.core import OriginalSkillAdapter, load_records
from resume_pipeline.format_contract import assess_format_report

class SkillAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'SKILL.md'
        self.path.write_text('# Explicit synthetic skill fixture for unit testing\nA4 portrait; no rendering implemented.\n')
        self.adapter=OriginalSkillAdapter(self.path)
        records=load_records(Path(__file__).resolve().parents[1]/'fixtures/synthetic.jsonl')
        self.profile,self.job=records[0],records[-1]
    def tearDown(self):self.tmp.cleanup()
    def test_actual_sanitized_skill_linkage(self):
        root=Path(__file__).resolve().parents[1]
        adapter=OriginalSkillAdapter(root/'skills/resume-generation/SKILL.md')
        b=adapter.prepare(self.profile,self.job,{},'en')
        self.assertEqual(b['source_format_contract']['contract_kind'],'sanitized_source_requirements')
        self.assertIn('references/format-contract.json',b['skill_reference_hashes'])
        self.assertFalse(b['final_artifact_generated'])
    def test_grounded_handoff_no_compliance_claim(self):
        b=self.adapter.prepare(self.profile,self.job,{},'en')
        self.assertFalse(b['final_artifact_generated'])
        self.assertEqual(b['format_status']['status'],'not_assessed')
        self.assertFalse(b['format_status']['actual_style_verified'])
        self.assertEqual(b['format_contract']['pages_per_language'],1)
        self.assertEqual(len(b['skill_sha256']),64)
        for f in self.profile['facts']:self.assertIn(f,b['grounded_content_draft'])
    def test_chinese_requires_supplied_aligned_facts(self):
        with self.assertRaises(ValueError):self.adapter.prepare(self.profile,self.job,{},'zh')
        self.profile['facts_zh']=['虚构练习事实一。','虚构练习事实二。']
        b=self.adapter.prepare(self.profile,self.job,{},'zh')
        self.assertIn('虚构练习事实一。',b['grounded_content_draft'])
    def complete_report(self):
        return {'language':'zh','separate_language_documents':True,'page_count':1,
                'paper':'A4','orientation':'portrait','blank_padding_used':False,
                'font_shrink_used':False,'dates_bold':True,'autoSpaceDE':True,
                'autoSpaceDN':True,'doNotCompress_punctuation':True,
                'bullet_alignment_verified':True,'pdf_export_engine':'Microsoft Word',
                'pdf_selectable_text':True,'heading_lines':'double',
                'graduation_label_and_value_bold':True,'paragraph_last_line_ratios':[.7],
                'docx_sha256':'a'*64,'pdf_sha256':'b'*64,'render_evidence_sha256':'c'*64,
                'extractor_version':'test-fixture','word_version':'test-fixture'}
    def test_complete_report_still_not_verified(self):
        r=assess_format_report(self.complete_report())
        self.assertEqual(r['status'],'reported_pass')
        self.assertFalse(r['actual_style_verified'])
        self.assertFalse(r['export_ready'])
    def test_contract_rejects_short_line_or_wrong_export(self):
        for k,v in [('paragraph_last_line_ratios',[.5]),('pdf_export_engine','other'),('font_shrink_used',True),('page_count',True),('graduation_label_and_value_bold',False)]:
            r=self.complete_report();r[k]=v
            self.assertEqual(assess_format_report(r)['status'],'fail')
    def test_preferred_line_range_is_warning(self):
        r=self.complete_report();r['paragraph_last_line_ratios']=[.6]
        result=assess_format_report(r)
        self.assertEqual(result['status'],'reported_pass')
        self.assertTrue(result['warnings'])

if __name__=='__main__':unittest.main()
