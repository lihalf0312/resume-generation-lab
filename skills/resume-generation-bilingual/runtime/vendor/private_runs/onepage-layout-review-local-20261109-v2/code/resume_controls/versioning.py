"""Frozen local implementation binding, not an API execution approval."""
from pathlib import Path
from .common import read,file_hash,digest
BASE=Path(__file__).resolve().parents[2]
def bindings(base=BASE):
 manifest=Path(base)/'FROZEN_VERSION.json'
 if not manifest.exists():return {'status':'development_unfrozen','paid_execution_authorized':False}
 value=read(manifest)
 for rel,sha in value['files'].items():
  p=Path(base)/rel
  if not p.is_file() or p.is_symlink() or file_hash(p)!=sha:raise ValueError('frozen_implementation_changed:'+rel)
 for rel,sha in value.get('existing_dependency_files',{}).items():
  if file_hash(BASE.parents[1]/rel)!=sha:raise ValueError('existing_adapter_dependency_changed:'+rel)
 return {'status':'frozen_live_scope_implementation'if value.get('live_scope_implementation')else'frozen_offline_candidate','manifest_sha256':file_hash(manifest),'content_sha256':digest(value['files']),'paid_execution_authorized':False}
