"""Minimal public factual sources, brief score/comment views and read-only checks.

Derivatives are new artifacts, not replacements for frozen inputs. The public dataset carries no original-input hash or process inventory. Validation
checks only the partial public views, not private original replay or source freezes.

This intentionally non-replayable text view omits authoring categories, factual
provenance prose and uncertainty annotations as well as explicit answer labels.
Its structural allowlist is not a semantic privacy/answer-key detector. Prose can
encode design hints; a separate content review remains necessary. File checks do
not provide a sandbox or transactional protection against concurrent writers.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from .judge_view import CURATOR_KEYS

VERSION = 'development-public-v4'
CURATION_KEYS = CURATOR_KEYS | frozenset({
    'requirements_evidence', 'stressor_rationale', 'scenario_rationale',
    'expected_answer', 'expected_answers', 'expected_label', 'expected_result',
    'expected_results', 'expected_quality', 'design_notes', 'design_rationale',
    'scenario_notes', 'curation_only', 'untrusted_jd_notes',
})
PROFILE_FIELDS = frozenset({
    'case_id', 'identity_id', 'source_family', 'creation_batch', 'synthetic',
    'publication', 'license', 'facts',
})
JOB_FIELDS = frozenset({
    'case_id', 'synthetic', 'publication', 'license', 'title', 'vacancy_label',
    'requirements',
})
FACT_FIELDS = frozenset({'id', 'kind', 'en', 'zh'})
REQUIREMENT_FIELDS = frozenset({'id', 'en', 'zh'})
PROFILE_METADATA = PROFILE_FIELDS - {'facts', 'synthetic'}
JOB_METADATA = JOB_FIELDS - {'title', 'requirements', 'synthetic'}
HASH = re.compile(r'^[0-9a-f]{64}$')
CASE = re.compile(r'^case-[0-9]{3}$')
BATCH = re.compile(r'^batch-[0-9]{3}$')
MAX_FILE_BYTES = 16 * 1024 * 1024


class PublicSourceError(ValueError):
    """A public derivative or its manifest violates the declared contract."""


def _check(condition, message):
    if not condition:
        raise PublicSourceError(message)


def _no_curation(value, where='data'):
    if isinstance(value, dict):
        for key, child in value.items():
            _check(key not in CURATION_KEYS, where + ': excluded design field')
            _no_curation(child, where)
    elif isinstance(value, list):
        for child in value:
            _no_curation(child, where)


def _entries(value, allowed, where):
    _check(type(value) is list, where + ': array required')
    ids = set()
    for item in value:
        _check(type(item) is dict, where + ': object entries required')
        _check(set(item) == allowed, where + ': entry fields must match the public allowlist')
        _check(isinstance(item.get('id'), str) and bool(item['id']),
               where + ': nonempty entry id required')
        _check(item['id'] not in ids, where + ': duplicate entry id')
        ids.add(item['id'])
        for language in ('en', 'zh'):
            _check(isinstance(item.get(language), str) and bool(item[language]),
                   where + ': bilingual text required')
        if 'kind' in item:
            _check(isinstance(item['kind'], str) and bool(item['kind']),
                   where + ': nonempty factual kind required')
        _no_curation(item, where)


def _validate_pair(profile, job):
    _check(type(profile) is dict and type(job) is dict, 'source objects required')
    _check(set(profile) <= PROFILE_FIELDS, 'profile: unsupported root field')
    _check(set(job) <= JOB_FIELDS, 'job: unsupported root field')
    for role, source, metadata in (
            ('profile', profile, PROFILE_METADATA), ('job', job, JOB_METADATA)):
        _check(source.get('synthetic') is True, role + ': synthetic=true required')
        _check(isinstance(source.get('case_id'), str) and
               CASE.fullmatch(source['case_id']) is not None,
               role + ': three-digit case id required')
        for key in metadata & set(source):
            _check(isinstance(source[key], str) and bool(source[key]),
                   role + ': metadata must be nonempty strings')
        if 'publication' in source:
            _check(source['publication'] == 'public', role + ': publication is not public')
        if 'license' in source:
            _check(source['license'] == 'CC0-1.0', role + ': unsupported source license')
        _no_curation(source, role)
    _check(profile['case_id'] == job['case_id'], 'source case ids differ')
    _check(isinstance(profile.get('identity_id'), str) and bool(profile['identity_id']),
           'profile: identity_id required')
    _entries(profile.get('facts'), FACT_FIELDS, 'facts')
    _check(bool(profile['facts']), 'profile: facts cannot be empty')
    _entries(job.get('requirements'), REQUIREMENT_FIELDS, 'requirements')
    _check(bool(job['requirements']), 'job: requirements cannot be empty')
    title = job.get('title')
    _check(type(title) is dict and set(title) == {'en', 'zh'} and
           all(isinstance(title[x], str) and bool(title[x]) for x in ('en', 'zh')),
           'job: bilingual title required')


def derive_sources(profile, job):
    """Return isolated public factual-text derivatives, never replay inputs.

    Safe identity IDs, lineage, creation batch and explicit publication metadata are
    retained. Facts keep exactly id/kind/en/zh; requirements keep id/en/zh. Text is
    copied unchanged. Authoring categories, fact-provenance prose, uncertainty
    annotations/directives, design keys and authored untrusted-JD notes are omitted.
    These omissions make this a documented non-replayable view, not an equivalent
    substitute for the private originals. No removed values are returned. Inputs
    are never modified and missing license metadata is not fabricated.
    """
    _check(type(profile) is dict and type(job) is dict, 'source objects required')
    result = {'profile': {}, 'job': {}}
    for role, original, fields in (
            ('profile', profile, PROFILE_FIELDS - {'facts'}),
            ('job', job, JOB_FIELDS - {'requirements'})):
        for key in sorted(fields):
            if key in original:
                result[role][key] = copy.deepcopy(original[key])
    for role, original, name, allowed in (
            ('profile', profile, 'facts', FACT_FIELDS),
            ('job', job, 'requirements', REQUIREMENT_FIELDS)):
        _check(type(original.get(name)) is list, name + ': array required')
        entries = []
        for item in original[name]:
            _check(type(item) is dict, name + ': object entries required')
            _check(allowed <= set(item), name + ': required factual text absent')
            entries.append({key: copy.deepcopy(item[key]) for key in sorted(allowed)})
        result[role][name] = entries
    _validate_pair(result['profile'], result['job'])
    return result


def _relative_path(value):
    _check(isinstance(value, str) and bool(value), 'nonempty relative path required')
    _check('\\' not in value and '\0' not in value and not value.startswith('/'),
           'absolute, backslash or null path rejected')
    parts = value.split('/')
    _check(all(part not in ('', '.', '..', '__pycache__', '.git', '.pytest_cache')
               for part in parts), 'traversal, cache or empty path component rejected')
    _check(PurePosixPath(value).as_posix() == value, 'noncanonical relative path rejected')
    return parts


def _read_bytes(root, rel):
    """Open each relative path component without following symlinks (POSIX)."""
    parts = _relative_path(rel)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(root, directory_flags)
        try:
            for component in parts[:-1]:
                child = os.open(component, directory_flags, dir_fd=fd)
                os.close(fd)
                fd = child
            file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                              dir_fd=fd)
            try:
                info = os.fstat(file_fd)
                _check(stat.S_ISREG(info.st_mode), 'regular source file required')
                _check(info.st_size <= MAX_FILE_BYTES, 'source file exceeds size limit')
                data = bytearray()
                while True:
                    chunk = os.read(file_fd, min(65536, MAX_FILE_BYTES + 1 - len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
                    _check(len(data) <= MAX_FILE_BYTES, 'source file exceeds size limit')
                return bytes(data)
            finally:
                os.close(file_fd)
        finally:
            os.close(fd)
    except OSError as error:
        raise PublicSourceError('missing, symlinked or unreadable public path: ' + rel) from error


def _load_json(data):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            _check(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    def invalid_constant(_value):
        raise PublicSourceError('nonfinite JSON number rejected')

    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=unique_pairs,
                          parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PublicSourceError('invalid UTF-8 JSON') from error


REVIEW_FIELDS = frozenset({'case_id','factual_status','overall_score','dimension_ratings',
    'brief_feedback_zh','brief_feedback_en','review_limitations','disputed_label'})
DIMENSION_LABELS = {
    'jd_relevance': ('岗位相关性','Job relevance'),
    'clarity': ('表达清晰度','Clarity'),
    'supported_achievements': ('成果表述','Supported achievements'),
    'format_readability': ('实际排版可读性','Rendered-format readability'),
}
RATING_FIELDS = frozenset({'dimension','label_zh','label_en','rating','scale_min','scale_max'})
REVIEW_LIMITATIONS = ['Unvalidated native review; content only.', '未经校准的原生评审；仅评估文本内容。']
PUBLIC_FILES = frozenset({'profile.public.json','job.public.json','resume.en.md','resume.zh.md','evaluation.public.json'})
INTERNAL_TEXT = re.compile(r'\b[FCUR][0-9]{2,3}\b|claim_audit|requirement_coverage|source_fact|evidence_pointer|'
    r'ledger|predecessor|provenance|curation|expected_answer|sha256|\.json|/workspace/|/home/', re.I)


def derive_evaluation(raw, *, brief_feedback_zh, brief_feedback_en, disputed_label=False):
    """Copy only actual ratings/nulls and attach separately reviewed brief comments.

    Detailed raw findings, mappings, quotations and process fields are never copied.
    Comments must be concise human-reviewed summaries, not invented observations
    or raw source comparisons. This structural helper cannot certify prose.
    """
    _check(type(raw) is dict, 'review object required')
    _check(raw.get('overall_score') is None and 'overall_score' in raw,
           'this content-only view requires a recorded null overall score')
    dimensions=raw.get('dimensions')
    _check(type(dimensions) is dict and set(dimensions)==set(DIMENSION_LABELS),
           'four actual dimensions required')
    ratings=[]
    for key,(zh,en) in DIMENSION_LABELS.items():
        _check(type(dimensions[key]) is dict and 'rating' in dimensions[key],
               'actual dimension rating required')
        ratings.append({'dimension':key,'label_zh':zh,'label_en':en,
                        'rating':copy.deepcopy(dimensions[key]['rating']),
                        'scale_min':0,'scale_max':4})
    result={'case_id':raw.get('case_id'),'factual_status':raw.get('factual_fidelity'),
        'overall_score':None,'dimension_ratings':ratings,
        'brief_feedback_zh':brief_feedback_zh,'brief_feedback_en':brief_feedback_en,
        'review_limitations':list(REVIEW_LIMITATIONS),'disputed_label':disputed_label}
    _validate_review(result)
    return result


def _validate_review(value):
    _check(type(value) is dict and set(value)==REVIEW_FIELDS,'brief review fields must exactly match allowlist')
    _check(isinstance(value['case_id'],str) and CASE.fullmatch(value['case_id']),'review case id invalid')
    _check(value['factual_status'] in {'pass','needs_review','fail'},'factual status invalid')
    _check(value['overall_score'] is None,'overall score must remain null')
    _check(type(value['disputed_label']) is bool,'disputed label must be boolean')
    _check(not value['disputed_label'] or value['factual_status']=='needs_review','disputed label requires review status')
    _check(value['review_limitations']==REVIEW_LIMITATIONS,'fixed review limitations required')
    for key,limit in [('brief_feedback_zh',180),('brief_feedback_en',400)]:
        text=value[key]
        _check(isinstance(text,str) and bool(text.strip()) and len(text)<=limit,'brief comment length/type invalid')
        _check(INTERNAL_TEXT.search(text) is None,'internal references in brief comment')
        _check(not any(c in text for c in ('{','}','[',']','\n','\r')),'brief comment must be plain single-line prose')
    ratings=value['dimension_ratings'];_check(type(ratings) is list and len(ratings)==4,'four ratings required')
    _check([x.get('dimension') for x in ratings if type(x) is dict]==list(DIMENSION_LABELS),'dimension order/membership invalid')
    for item in ratings:
        _check(type(item) is dict and set(item)==RATING_FIELDS,'rating fields invalid')
        zh,en=DIMENSION_LABELS[item['dimension']]
        _check(item['label_zh']==zh and item['label_en']==en,'dimension labels invalid')
        _check(type(item['scale_min']) is int and item['scale_min']==0 and
               type(item['scale_max']) is int and item['scale_max']==4,'rating scale invalid')
        rating=item['rating'];_check(rating is None or (type(rating) in (int,float) and 0<=rating<=4),'rating invalid')


def validate_public_dataset(root,index_path='data/development-140/index.json'):
    """Validate five-file membership, public source schemas and brief score views.

    This never reads original reviews or confirms historical source validation.
    It is not semantic entailment, reviewer calibration or a privacy certification.
    """
    root=Path(root).absolute();_check(root.is_dir() and not root.is_symlink(),'plain repository root required')
    index=_load_json(_read_bytes(root,index_path))
    _check(type(index) is dict and index.get('schema_version')==VERSION,'dataset index schema invalid')
    cases=index.get('cases');_check(type(cases) is list and bool(cases),'case list required')
    _check(type(index.get('case_count')) is int and index['case_count']==len(cases),'case count mismatch')
    _check(set(index)<={'schema_version','case_count','cases','notice'},'index fields invalid')
    seen=set();identities=set();result={'cases':len(cases),'source_files':0,'resumes':0,'evaluations':0,
        'facts':0,'requirements':0,'gate_counts':{'pass':0,'needs_review':0,'fail':0},'errors':[]}
    for item in cases:
        _check(type(item) is dict and set(item)=={'case_id','path'},'case index fields invalid')
        cid=item['case_id'];_check(isinstance(cid,str) and CASE.fullmatch(cid),'case id invalid')
        _check(cid not in seen,'duplicate case');seen.add(cid)
        rel=item['path'];_relative_path(rel);_check(rel=='data/development-140/'+cid,'unexpected case path')
        directory=root/rel;_check(directory.is_dir() and not directory.is_symlink(),'plain case directory required')
        _check({p.name for p in directory.iterdir()}==PUBLIC_FILES,'case must contain exactly five public files')
        profile=_load_json(_read_bytes(root,rel+'/profile.public.json'))
        job=_load_json(_read_bytes(root,rel+'/job.public.json'));_validate_pair(profile,job)
        _check(profile['case_id']==cid,'source case mismatch')
        identity=profile['identity_id'];_check(identity not in identities,'duplicate identity');identities.add(identity)
        review=_load_json(_read_bytes(root,rel+'/evaluation.public.json'));_validate_review(review)
        _check(review['case_id']==cid,'review case mismatch')
        for name in ('resume.en.md','resume.zh.md'):
            raw=_read_bytes(root,rel+'/'+name)
            try:text=raw.decode('utf-8')
            except UnicodeError as error:raise PublicSourceError('resume is not UTF-8') from error
            _check(bool(text.strip()),'resume cannot be empty')
        result['source_files']+=2;result['resumes']+=2;result['evaluations']+=1
        result['facts']+=len(profile['facts']);result['requirements']+=len(job['requirements'])
        result['gate_counts'][review['factual_status']]+=1
    dataset=root/'data/development-140'
    _check({p.name for p in dataset.iterdir()}=={'index.json'}|{c['case_id'] for c in cases},'unlisted dataset entries')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',default='.')
    parser.add_argument('--index',default='data/development-140/index.json');args=parser.parse_args()
    try:result=validate_public_dataset(args.root,args.index)
    except (PublicSourceError,KeyError,TypeError) as error:
        print(json.dumps({'errors':[str(error)]},ensure_ascii=False));return 1
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
