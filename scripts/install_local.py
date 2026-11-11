"""Verify and copy one local skill ZIP. No network, dependency install or code execution."""
from __future__ import annotations
import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import zipfile

MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 5000
RESERVED = {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}
class InstallError(ValueError): pass

def reject_reparse(path):
    for entry in [path, *path.parents]:
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise InstallError(f'Symlink destination is not permitted: {entry}')
        attrs = getattr(info, 'st_file_attributes', 0)
        if attrs & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024):
            raise InstallError(f'Reparse destination is not permitted: {entry}')

def verified_snapshot(path, expected):
    if not re.fullmatch(r'[0-9a-fA-F]{64}', expected):
        raise InstallError('Expected SHA-256 must contain exactly 64 hex digits')
    with path.open('rb') as source:
        data = source.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise InstallError('Archive exceeds 64 MiB compressed size limit')
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected.lower():
        raise InstallError('SHA-256 mismatch; nothing was installed')
    return data, actual

def inspect_archive(z, actual):
    entries=z.infolist()
    if len(entries)>MAX_FILES or sum(e.file_size for e in entries)>MAX_BYTES:
        raise InstallError('Archive exceeds file-count or expanded-size limit')
    seen=set(); roots=set(); files=[]
    namespace = {}
    for e in entries:
        name=e.orig_filename
        p=PurePosixPath(name)
        if chr(92) in name or p.is_absolute() or not p.parts:
            raise InstallError('Unsafe archive path')
        for part in name.rstrip('/').split('/'):
            if not part or part in ('.','..') or any(ord(c)<32 for c in part) or ':' in part or part.endswith((' ','.')) or part.split('.')[0].upper() in RESERVED:
                raise InstallError('Unsafe archive path')
        if e.flag_bits & 1:
            raise InstallError('Encrypted archive members are not supported')
        mode=e.external_attr >> 16
        if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR)):
            raise InstallError('Archive links/special files are not permitted')
        normalized='/'.join(p.parts).casefold()
        if normalized in seen: raise InstallError('Duplicate/case-colliding archive path')
        seen.add(normalized); roots.add(p.parts[0])
        # Validate implicit directories as well as explicit ZIP members.
        # Windows cannot preserve two spellings or kinds at the same path.
        current = namespace
        for index, part in enumerate(p.parts):
            directory = index < len(p.parts) - 1 or e.is_dir()
            key = part.casefold()
            existing = current.get(key)
            if existing is None:
                existing = current[key] = (part, directory, {})
            if existing[:2] != (part, directory):
                raise InstallError('Case-colliding archive path or file/directory conflict')
            current = existing[2]
        if not e.is_dir(): files.append(e)
    if len(roots)!=1: raise InstallError('Archive must contain exactly one skill folder')
    skill=next(iter(roots))
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',skill) or len(skill)>64:
        raise InstallError('Invalid skill folder name')
    entry=skill+'/SKILL.md'
    if entry not in z.namelist(): raise InstallError('SKILL.md is missing')
    text=z.read(entry).decode('utf-8-sig')
    m=re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)',text,re.S)
    if not m: raise InstallError('SKILL.md frontmatter is missing')
    header=m.group(1)
    n=re.search(r'^name:\s*([a-z0-9-]+)\s*$',header,re.M)
    d=re.search(r'^description:\s*\S.+$',header,re.M)
    if not n or n.group(1)!=skill or not d:
        raise InstallError('SKILL.md name/description do not match the folder')
    hashes={e.filename[len(skill)+1:]:hashlib.sha256(z.read(e)).hexdigest() for e in files}
    return {'skill_name':skill,'sha256':actual,'file_count':len(files),'file_hashes':hashes}

def install(archive, expected, skills_dir, verify_only=False):
    archive=Path(archive)
    root=Path(skills_dir).expanduser()
    if not root.is_absolute(): raise InstallError('skills-dir must be an explicit absolute directory')
    reject_reparse(root)
    root=root.resolve()
    data, actual = verified_snapshot(archive, expected)
    with zipfile.ZipFile(BytesIO(data)) as verified:
        report = inspect_archive(verified, actual)
        return install_verified(verified, root, report, verify_only)

def install_verified(verified, root, report, verify_only):
    dest=root/report['skill_name']
    if dest.exists() or dest.is_symlink(): raise InstallError('Destination already exists; nothing was overwritten')
    if os.name == 'nt' and any(len(str(dest/rel)) >= 259 for rel in report['file_hashes']):
        raise InstallError('Destination path is too long for this Windows package. Use a shorter host-supported skill root; no system/security setting was changed.')
    if os.name == 'nt':
        # Reserve a conservative 32-character temporary-directory component,
        # then check the actual staging name again before extracting files.
        prospective_stage=root/('.resume-install-'+'x'*17)
        if len(str(prospective_stage)) >= 248 or any(len(str(prospective_stage/report['skill_name']/rel)) >= 259 for rel in report['file_hashes']):
            raise InstallError('Temporary extraction path budget is too long for this Windows package. Use a shorter supported skill root; no installation directory was created.')
    report['destination']=str(dest)
    report['host_discovery']='not_verified_by_file_copy'
    if verify_only:
        report['installed']=False
        return report
    root.mkdir(parents=True,exist_ok=True)
    reject_reparse(root)
    # Only this new bounded temp directory is ever cleaned up. Existing skills are untouched.
    with tempfile.TemporaryDirectory(prefix='.resume-install-',dir=root) as tmp:
        stage=Path(tmp)
        if stage.resolve().parent!=root: raise InstallError('Staging directory escaped skills root')
        if os.name == 'nt' and any(len(str(stage/report['skill_name']/rel)) >= 259 for rel in report['file_hashes']):
            raise InstallError('Temporary extraction path is too long for this Windows package. Use a shorter supported skill root; no installation directory was created.')
        for e in verified.infolist():
            target=stage.joinpath(*PurePosixPath(e.filename).parts)
            if not target.resolve().is_relative_to(stage.resolve()): raise InstallError('Archive path escaped staging')
            if e.is_dir(): target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with verified.open(e) as source, target.open('xb') as output:
                    shutil.copyfileobj(source,output)
        staged=stage/report['skill_name']
        staged_files = {path.relative_to(staged).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in staged.rglob('*') if path.is_file()}
        if staged_files != report['file_hashes']:
            raise InstallError('Staged files differ from verified archive')
        if dest.exists() or dest.is_symlink(): raise InstallError('Destination appeared during installation')
        if os.name == 'nt':
            # Same-volume Windows rename fails if the destination exists.
            # Publish the complete directory in one operation.
            staged.rename(dest)
        else:
            # POSIX rename could replace an existing empty destination.
            dest.mkdir(exist_ok=False)
            for child in staged.iterdir():
                child.rename(dest/child.name)
    report['installed']=True
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--sha256',required=True)
    p.add_argument('--skills-dir',type=Path,required=True)
    p.add_argument('--verify-only',action='store_true')
    a=p.parse_args()
    if sys.version_info < (3, 10):
        print('Python 3.10 or newer is required. Use an existing supported interpreter.', file=sys.stderr)
        return 2
    try:
        print(json.dumps(install(a.archive,a.sha256,a.skills_dir,a.verify_only),indent=2,ensure_ascii=False))
        return 0
    except (InstallError,OSError,zipfile.BadZipFile,UnicodeError,NotImplementedError) as exc:
        print(json.dumps({'installed':False,'error':str(exc),'note':'Existing installations are never overwritten. If a filesystem failure occurred during copy, inspect the destination before retrying.'},ensure_ascii=False))
        return 2
if __name__=='__main__': raise SystemExit(main())
