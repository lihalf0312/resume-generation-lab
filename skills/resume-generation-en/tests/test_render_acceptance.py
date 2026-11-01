"""RC4 boundary regressions; actual renderer recovery is a separate integration run."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import runtime as r
import onepage as w

class WorkdirBoundary(unittest.TestCase):
    def test_equal_both_containments_and_no_side_effect(self):
        install=Path(r.__file__).resolve().parent.parent
        for root in (install,install/'forbidden-never-created',install.parent):
            with self.subTest(root=root):
                before=set(install.iterdir())
                with self.assertRaises(r.WorkflowError):r.preflight({'workdir':str(root)})
                self.assertEqual(before,set(install.iterdir()))
                with tempfile.TemporaryDirectory() as temp:
                    config=Path(temp)/'config.json'
                    config.write_text(json.dumps({'workdir':str(root),'renderer':'/unused','fontconfig_file':'/unused','fonts':{'regular':'/unused'}}))
                    with self.assertRaises(r.WorkflowError):r.configuration(config)
                self.assertFalse((install/'forbidden-never-created').exists())

    def test_rejected_init_does_not_copy_or_modify_input(self):
        install=Path(r.__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);source=base/'source.json';source.write_text('{"private_source_sentinel":true}')
            before=r.digest(source)
            config=base/'runtime.json';config.write_text(json.dumps({'workdir':str(install/'forbidden-init'),'renderer':'/unused','fontconfig_file':'/unused','fonts':{'regular':'/unused'}}))
            with patch.object(sys,'argv',['runtime.py','--config',str(config),'init',str(source)]):
                with self.assertRaises(r.WorkflowError):r.main()
            self.assertEqual(r.digest(source),before)
            self.assertFalse((install/'forbidden-init').exists())

    def test_symlink_resolution_and_unrelated_positive(self):
        install=Path(r.__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'alias').symlink_to(install,target_is_directory=True)
            for workdir in (base/'alias',base/'alias'/'never-created'):
                with self.assertRaises(r.WorkflowError):r.preflight({'workdir':str(workdir)})
            (base/'ancestor').symlink_to(install.parent,target_is_directory=True)
            with self.assertRaises(r.WorkflowError):r.preflight({'workdir':str(base/'ancestor')})
            self.assertEqual(r.validate_workdir({'workdir':str(base/'independent')}),base/'independent')
            self.assertFalse((base/'independent').exists())
            with patch.object(r,'__file__',str(base/'alias'/'scripts'/'runtime.py')):
                with self.assertRaises(r.WorkflowError):r.validate_workdir({'workdir':str(install/'never-created')})

class AcceptanceBoundary(unittest.TestCase):
    def fixture(self,base):
        root=Path(base)/'task';root.mkdir();latest=root/'versions'/'v00';latest.mkdir(parents=True)
        for name in ('resume.docx','content.json','resume.txt','style-check.json'):(latest/name).write_text('{}')
        renderer=Path(base)/'renderer';renderer.write_text('local executable')
        fc=Path(base)/'fonts.conf';fc.write_text('local fontconfig')
        return latest,{'workdir':str(root),'renderer':str(renderer),'fontconfig_file':str(fc)}, {'renderer':'local test renderer','resolved_fonts':{'regular':{'sha256':'test'}}}

    def fake_run(self,cmd,*args):
        import subprocess
        if '--outdir' in cmd:(Path(cmd[cmd.index('--outdir')+1])/'resume.pdf').write_bytes(b'explicit test pdf')
        return subprocess.CompletedProcess(cmd,0,'renderer test output','renderer test diagnostic')

    def fake_measure(self,folder):
        m={'pages':1,'all_content_words_preserved':True,'style_unchanged':True,'pages_detail':[{'outside_body_words':0}]}
        r.write(folder/'measurement.json',m);return m

    def fake_fonts(self,folder,evidence):
        fonts={'validation_passed':True,'pdf_base_fonts':['TimesNewRomanPSMT']}
        r.write(folder/'font-evidence.json',fonts);return fonts

    def test_legacy_measurement_does_not_authorize_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            latest,c,e=self.fixture(temp);r.write(latest/'measurement.json',{'pages':1})
            with self.assertRaises(r.WorkflowError):r.accepted_render(latest,c,e)
            self.assertFalse((latest/'accepted-render.json').exists())

    def test_post_measurement_failure_recovery_reuse_and_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            latest,c,e=self.fixture(temp)
            def fail(folder,evidence):
                r.write(folder/'font-evidence.json',{'validation_passed':False,'fault_injected':True})
                raise r.WorkflowError('explicit post-measurement font fault')
            with patch.object(r,'checked_run',side_effect=self.fake_run) as run,patch.object(w,'measure',side_effect=self.fake_measure),patch.object(r,'verify_embedded_fonts',side_effect=fail):
                with self.assertRaises(r.WorkflowError):r.render_version(latest,c,e)
                self.assertEqual(run.call_count,1)
            failed=latest/'render-attempt-01';hashes={p.name:r.digest(p) for p in failed.iterdir()}
            self.assertTrue((failed/'measurement.json').exists())
            self.assertEqual(r.load(failed/'result.json')['returncode'],0)
            with self.assertRaises(r.WorkflowError):r.accepted_render(latest,c,e)
            with patch.object(r,'checked_run',side_effect=self.fake_run) as run,patch.object(w,'measure',side_effect=self.fake_measure),patch.object(r,'verify_embedded_fonts',side_effect=self.fake_fonts):
                folder,reused=r.render_version(latest,c,e);self.assertFalse(reused)
                self.assertTrue(r.render_version(latest,c,e)[1]);self.assertEqual(run.call_count,1)
            self.assertEqual(hashes,{p.name:r.digest(p) for p in failed.iterdir()})
            self.assertEqual(folder.name,'render-attempt-02')
            with self.assertRaises(r.WorkflowError):r.accepted_render(latest,dict(c,private_configuration_changed=True),e)
            original=(latest/'resume.docx').read_bytes();(latest/'resume.docx').write_bytes(b'changed original DOCX')
            with self.assertRaises(r.WorkflowError):r.accepted_render(latest,c,e)
            (latest/'resume.docx').write_bytes(original)
            (folder/'resume.pdf').write_bytes(b'changed')
            with self.assertRaises(r.WorkflowError):r.accepted_render(latest,c,e)
            with self.assertRaises(r.WorkflowError):r.render_version(latest,c,e)

    def test_three_failed_attempts_exhaust_and_retain_exit_errors(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            latest,c,e=self.fixture(temp)
            with patch.object(r,'checked_run',return_value=subprocess.CompletedProcess([],23,'output','actual stderr')) as run:
                for attempt in range(1,4):
                    with self.assertRaises(r.WorkflowError):r.render_version(latest,c,e)
                    result=r.load(latest/('render-attempt-%02d'%attempt)/'result.json')
                    self.assertEqual(result['returncode'],23);self.assertEqual(result['stderr'],'actual stderr')
                with self.assertRaises(r.WorkflowError):r.render_version(latest,c,e)
                self.assertEqual(run.call_count,3)
            self.assertFalse((latest/'render-attempt-04').exists())

    def test_actual_font_validator_rejects_nonembedded_and_unexpected_fonts(self):
        for name,data,allowed in [('TimesNewRomanPSMT',b'',False),('UnexpectedSubstitute',b'font-program',False),('TimesNewRomanPSMT',b'font-program',True)]:
            with self.subTest(font=name,embedded=bool(data)),tempfile.TemporaryDirectory() as temp:
                pdf=MagicMock();pdf.__enter__.return_value=pdf
                page=MagicMock();page.get_fonts.return_value=[(7,)]
                pdf.__iter__.return_value=iter([page]);pdf.extract_font.return_value=(name,'ttf','TrueType',data)
                with patch.object(w.fitz,'open',return_value=pdf):
                    if allowed:self.assertTrue(r.verify_embedded_fonts(Path(temp),{'resolved_fonts':{}})['validation_passed'])
                    else:
                        with self.assertRaises(r.WorkflowError):r.verify_embedded_fonts(Path(temp),{'resolved_fonts':{}})
                        self.assertFalse(r.load(Path(temp)/'font-evidence.json')['validation_passed'])

    def test_direct_render_rejects_install_and_escaped_version(self):
        install=Path(r.__file__).resolve().parent.parent
        with self.assertRaises(r.WorkflowError):r.render_version(install,{'workdir':str(install/'never-created')},{})
        with tempfile.TemporaryDirectory() as temp:
            latest,c,e=self.fixture(temp);outside=Path(temp)/'outside';outside.mkdir()
            (latest/'escape').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(r.WorkflowError):r.render_version(latest/'escape',c,e)
            self.assertEqual(list(outside.iterdir()),[])

if __name__=='__main__':unittest.main(verbosity=2)
