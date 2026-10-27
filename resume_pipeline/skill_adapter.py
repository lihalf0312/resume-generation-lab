"""Grounded preparation adapter for the sanitized user-supplied skill.

Does not execute skill instructions, recover missing dependencies, translate facts,
render Word documents, or assert PDF/style compliance.
"""
import hashlib
import json
from pathlib import Path
from .core import GroundedRenderer, digest, validate
from .format_contract import CONTRACT, assess_format_report


class SanitizedSkillAdapter:
    version = 'sanitized-skill-content-adapter-v1'

    def __init__(self, skill_path):
        self.path = Path(skill_path)
        if not self.path.is_file():
            raise FileNotFoundError('Sanitized original SKILL.md required: ' + str(self.path))
        self.skill_text = self.path.read_text(encoding='utf-8')
        if not self.skill_text.strip():
            raise ValueError('Empty sanitized skill')
        self.skill_sha256 = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.reference_hashes = {}
        for relative in ('references/formatting.md', 'references/dependencies.md', 'references/project.md', 'references/format-contract.json'):
            reference = self.path.parent / relative
            if reference.is_file():
                self.reference_hashes[relative] = hashlib.sha256(reference.read_bytes()).hexdigest()
        source_contract = self.path.parent / 'references' / 'format-contract.json'
        self.source_contract = json.loads(source_contract.read_text(encoding='utf-8')) if source_contract.is_file() else None

    def generate(self, profile, job, policy):
        """Compatibility interface: grounded content only, never a final resume artifact."""
        validate(profile); validate(job)
        return GroundedRenderer().generate(profile, job, policy)

    def prepare(self, profile, job, policy, language='en'):
        validate(profile); validate(job)
        if language not in CONTRACT['languages']:
            raise ValueError('language must be zh or en')
        p = dict(profile)
        if language == 'zh':
            translated = profile.get('facts_zh')
            if not isinstance(translated, list) or len(translated) != len(profile['facts']) or not all(isinstance(x, str) and x for x in translated):
                raise ValueError('Aligned supplied Chinese facts required; this adapter does not invent translations')
            p['facts'] = translated
        return {
            'adapter_version': self.version,
            'skill_path': self.path.as_posix(), 'skill_sha256': self.skill_sha256,
            'skill_reference_hashes': self.reference_hashes, 'source_format_contract': self.source_contract,
            'contract_scope': 'Machine checks cover a subset; complete sanitized skill/reference instructions remain authoritative.',
            'language': language, 'profile_hash': digest(profile), 'job_hash': digest(job),
            'source_fact_ids': profile.get('fact_ids', ['fact-%03d' % i for i in range(len(profile['facts']))]),
            'grounded_content_draft': GroundedRenderer().generate(p, job, policy),
            'content_notice': 'Draft fact inventory, not localized final document; heading labels remain baseline English.',
            'format_contract': CONTRACT, 'format_contract_hash': digest(CONTRACT),
            'format_status': assess_format_report({'language': language}),
            'missing_dependencies': ['original templates', 'authorized photo assets if required', 'private fact database', 'original render scripts', 'Microsoft Word export and actual artifact verification'],
            'final_artifact_generated': False,
            'handoff': 'Native generator may use supplied skill and facts; independently render and inspect both language artifacts before any compliance claim.',
        }
