"""Small opt-in overlay over the existing local v2 candidate."""
from pathlib import Path
import hashlib
import json
BASELINE = Path(__file__).resolve().parents[3] / 'onepage-layout-review-local-20261109-v2'
_manifest = Path(__file__).resolve().parents[2] / 'DEPENDENCIES.json'
if _manifest.exists():
    for _relative, _expected in json.loads(_manifest.read_text(encoding='utf-8'))['files'].items():
        _path = BASELINE.parent / _relative
        if hashlib.sha256(_path.read_bytes()).hexdigest() != _expected:
            raise ValueError('label_candidate_dependency_changed:' + _relative)
__path__.append(str(BASELINE / 'code/resume_controls'))
