"""Public skill preparation adapter: inert config, grounded content, no rendering."""
import hashlib
import json
from pathlib import Path
from .core import GroundedRenderer, digest, validate
from .format_contract import build_contract, assess_format_report
from .preferences import merge_preferences

REQUIRED_REFERENCES=('references/workspace.md','references/layout-and-qa.md','assets/resume-preferences.json')


class SanitizedSkillAdapter:
    version='public-skill-preferences-adapter-v2'

    def __init__(self, skill_path, confirmed_preferences=None, current_overrides=None, template_preferences=None):
        self.path=Path(skill_path)
        if not self.path.is_file() or self.path.is_symlink():raise FileNotFoundError('Regular public SKILL.md required')
        self.skill_text=self.path.read_text(encoding='utf-8')
        if not self.skill_text.strip():raise ValueError('Empty skill')
        self.skill_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.reference_hashes={}
        for rel in REQUIRED_REFERENCES:
            ref=self.path.parent/rel
            if not ref.is_file() or ref.is_symlink() or self.path.parent.resolve() not in ref.resolve().parents:
                raise FileNotFoundError('Missing or unsafe required skill reference: '+rel)
            if not ref.read_text(encoding='utf-8').strip():raise ValueError('Empty skill reference: '+rel)
            self.reference_hashes[rel]=hashlib.sha256(ref.read_bytes()).hexdigest()
        self.defaults=json.loads((self.path.parent/'assets/resume-preferences.json').read_text(encoding='utf-8'))
        self.preferences=merge_preferences(self.defaults,template_preferences,confirmed_preferences,current_overrides)
        self.layer_hashes={name:digest(value) for name,value in [('public_defaults',self.defaults),('template',template_preferences),('confirmed',confirmed_preferences),('current',current_overrides)]}

    def generate(self, profile, job, policy):
        validate(profile);validate(job)
        return GroundedRenderer().generate(profile,job,policy)

    def prepare(self, profile, job, policy, language=None):
        validate(profile);validate(job)
        if language is None:
            selected=self.preferences['output_languages']
            if selected is None or len(selected)!=1:raise ValueError('Explicit output language required; no implicit bilingual or English generation')
            language=selected[0]
        language='zh-CN' if language=='zh' else language
        contract=build_contract(self.preferences,language)
        p=dict(profile)
        if language=='zh-CN':
            facts=profile.get('facts_zh')
            if not isinstance(facts,list) or len(facts)!=len(profile['facts']) or not all(isinstance(x,str) and x for x in facts):raise ValueError('Aligned supplied Chinese facts required; no invented translation')
            p['facts']=facts
        return {'adapter_version':self.version,'skill_path':self.path.as_posix(),
                'skill_sha256':self.skill_sha256,'skill_reference_hashes':self.reference_hashes,
                'source_preferences':self.defaults,'resolved_preferences':self.preferences,
                'preference_layer_hashes':self.layer_hashes,
                'precedence':['public_defaults','measured_template','confirmed_user','current_request'],
                'language':language,'profile_hash':digest(profile),'job_hash':digest(job),
                'source_fact_ids':profile.get('fact_ids',['fact-%03d'%i for i in range(len(profile['facts']))]),
                'grounded_content_draft':GroundedRenderer().generate(p,job,policy),
                'content_notice':'Draft evidence inventory; baseline English headings are not a final localized document.',
                'format_contract':contract,'format_contract_hash':digest(contract),
                'format_status':assess_format_report({'language':language},contract),
                'missing_dependencies':['actual measured template if template mode requested','recorded available fonts/page parameters for generic fallback','compatible DOCX/PDF generation engine and actual rendered artifact inspection'],
                'final_artifact_generated':False,
                'handoff':'Use confirmed facts and resolved preferences. Generic fallback is a new design, not restoration of an absent template. No configured file is opened or executed.'}
