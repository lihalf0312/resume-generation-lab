"""Fail-closed publication inventory. No network or git push operations."""
import hashlib
import re
from pathlib import Path
from .core import SECRET_PATTERNS, load_records, public_gate, write_json

# Only these code/docs directories may be proposed. Research is manually reviewed
# separately; raw downloads, private runs, arbitrary files are never swept in.
REVIEWABLE_FILES = {
    "README.md", "STATUS.md", ".gitignore", "docs/SCHEMA.md",
    "resume_pipeline/__init__.py", "resume_pipeline/__main__.py",
    "resume_pipeline/core.py", "resume_pipeline/evaluator.py", "resume_pipeline/release.py",
    "tests/test_pipeline.py", "fixtures/synthetic.jsonl",
    "resume_pipeline/skill_adapter.py", "resume_pipeline/format_contract.py", "tests/test_skill_adapter.py",
}


def audit_release(root, paths, destination):
    root = Path(root).resolve()
    entries = []
    for relative in paths:
        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("unsafe publication path")
        path = root / rel
        if path.is_symlink() or root not in path.resolve().parents or not path.is_file():
            raise ValueError("not a regular in-root file")
        if str(rel) not in REVIEWABLE_FILES:
            raise ValueError("file not in public asset whitelist: " + str(rel))
        content = path.read_text(encoding="utf-8")
        if any(re.search(p, content) for p in SECRET_PATTERNS):
            raise ValueError("possible secret: " + str(rel))
        if str(rel) == "fixtures/synthetic.jsonl":
            public_gate(load_records(path))
        entries.append({"path": str(rel), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    result = {"files": entries, "published": False, "automated_checks": "whitelist, synthetic data provenance, common secret patterns", "human_review_required": "Check copyright, personal identifiers, unknown secret formats and all documentation before publishing; this scanner is not a privacy guarantee."}
    write_json(destination, result)
    return result
