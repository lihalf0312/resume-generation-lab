"""Regression: later generated JSON must not change frozen source membership."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/'experiments/development-001/validate_extension_004.py'
SOURCE_NAMES=('profile.json','job.json','curation-notes.json')

class Extension004ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        shutil.copyfile(VALIDATOR,self.root/'validate_extension_004.py')
        self.batch=self.root/'batch-004';self.case=self.batch/'case-031';self.case.mkdir(parents=True)
        facts=[{'id':f'F{i:02d}','en':f'Fictional activity {i}','zh':f'虚构练习{i}','kind':'project','provenance':'synthetic test'} for i in range(16)]
        profile={'case_id':'case-031','synthetic':True,'identity_id':'fictional-031','source_family':'fixture-031','facts':facts}
        job={'case_id':'case-031','synthetic':True,'requirements':[{'id':f'R{i}','en':f'Task {i}','zh':f'任务{i}'} for i in range(3)]}
        notes={'case_id':'case-031','requirement_evidence':[{'requirement_id':f'R{i}','evidence_status':'direct','supporting_fact_ids':['F00']} for i in range(3)]}
        for name,data in zip(SOURCE_NAMES,(profile,job,notes)):(self.case/name).write_text(json.dumps(data))
        self.manifest={'files':{f'case-031/{name}':hashlib.sha256((self.case/name).read_bytes()).hexdigest() for name in SOURCE_NAMES}}
        self.save_manifest()
    def tearDown(self):self.tmp.cleanup()
    def save_manifest(self):(self.batch/'source-manifest-v1.sha256.json').write_text(json.dumps(self.manifest))
    def execute(self):return subprocess.run([sys.executable,str(self.root/'validate_extension_004.py')],capture_output=True,text=True)
    def test_generated_json_does_not_expand_source_manifest(self):
        baseline=self.execute();self.assertEqual(baseline.returncode,0,baseline.stderr)
        for name in ('generation.json','evaluation.json','layout-report.json'):(self.case/name).write_text('{"artifact":true}')
        result=self.execute();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout);self.assertEqual(report['files'],3);self.assertEqual(report['errors'],[])
    def test_changed_source_hash_fails(self):
        path=self.case/'profile.json';path.write_text(path.read_text()+'\n')
        result=self.execute();self.assertNotEqual(result.returncode,0);self.assertIn('hash mismatch',result.stdout)
    def test_missing_actual_source_fails(self):
        (self.case/'job.json').unlink()
        self.assertNotEqual(self.execute().returncode,0)
    def test_missing_manifest_source_entry_fails(self):
        del self.manifest['files']['case-031/job.json'];self.save_manifest()
        result=self.execute();self.assertNotEqual(result.returncode,0);self.assertIn('manifest coverage',result.stdout)
    def test_extra_manifest_source_entry_fails(self):
        extra=self.case/'extra-source.json';extra.write_text('{}')
        self.manifest['files']['case-031/extra-source.json']=hashlib.sha256(extra.read_bytes()).hexdigest();self.save_manifest()
        result=self.execute();self.assertNotEqual(result.returncode,0);self.assertIn('manifest coverage',result.stdout)
    def test_extra_actual_source_case_fails(self):
        other=self.batch/'case-032';shutil.copytree(self.case,other)
        for name in SOURCE_NAMES:
            path=other/name;data=json.loads(path.read_text());data['case_id']='case-032'
            if name=='profile.json':data.update(identity_id='fictional-032',source_family='fixture-032')
            path.write_text(json.dumps(data))
        result=self.execute();self.assertNotEqual(result.returncode,0);self.assertIn('manifest coverage',result.stdout)

if __name__=='__main__':unittest.main()
