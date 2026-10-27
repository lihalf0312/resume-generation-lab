"""Stdlib-only, single-writer research pipeline; all scores are diagnostic."""
import hashlib
import json
import os
import re
from pathlib import Path

VERSION = "0.2.0"
RUBRIC = {"version": "diagnostic-v1", "description": "Skill coverage only, not HR judgment"}
PROMPT = "Verbatim profile facts only; order supported skills by job relevance."


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def validate(record):
    required = {"id", "kind", "source_family", "synthetic", "publication", "provenance", "skills"}
    if not isinstance(record, dict) or not required <= record.keys():
        raise ValueError("missing record fields")
    if record["kind"] not in ("profile", "job"):
        raise ValueError("kind must be profile or job")
    for name in ("id", "source_family"):
        if not isinstance(record[name], str) or not record[name].strip():
            raise ValueError("invalid " + name)
    if type(record["synthetic"]) is not bool:
        raise ValueError("synthetic must be explicit boolean")
    p = record["provenance"]
    if not isinstance(p, dict) or not all(isinstance(p.get(k), str) and p[k] for k in ("source", "retrieved_at", "license", "method")):
        raise ValueError("source, retrieval date, license and method required")
    if record["publication"] not in ("public", "private", "review_required"):
        raise ValueError("invalid publication decision")
    if not isinstance(record["skills"], list) or not all(isinstance(x, str) and x.strip() for x in record["skills"]):
        raise ValueError("skills must be strings")
    fields = ("name", "facts", "profile_group") if record["kind"] == "profile" else ("title",)
    if not all(k in record for k in fields):
        raise ValueError("missing kind-specific fields")
    if record["kind"] == "profile":
        if not isinstance(record["facts"], list) or not all(isinstance(f, str) and f.strip() for f in record["facts"]):
            raise ValueError("facts must be nonempty strings")
        if "fact_ids" in record and (not isinstance(record["fact_ids"], list) or len(record["fact_ids"]) != len(record["facts"]) or not all(isinstance(x, str) and x for x in record["fact_ids"]) or len(set(record["fact_ids"])) != len(record["fact_ids"])):
            raise ValueError("fact_ids must uniquely align with facts")
        if not isinstance(record["profile_group"], str) or not record["profile_group"]:
            raise ValueError("profile_group required for identity leakage prevention")
    if not isinstance(record[fields[0]], str) or not record[fields[0]].strip():
        raise ValueError("name/title must be nonempty text")
    return record


def load_records(path):
    records = [validate(json.loads(line)) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("duplicate record id")
    return records


def split_for(group, seed):
    bucket = int(digest([seed, group])[:8], 16) % 10
    return "train" if bucket < 6 else "dev" if bucket < 8 else "test"


def freeze_splits(records, path, seed="resume-research-v1"):
    """Identity groups and JD source families never cross split boundaries.

    Only same-split pairs are eligible. Connected profile families are grouped
    together as well, preventing near-duplicate source-template leakage.
    """
    groups = {}
    # Union profile identities AND source families; variants cannot bridge splits.
    parent = {}
    def root(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = root(parent[x])
        return parent[x]
    def normalized(values):
        return sorted(" ".join(v.casefold().split()) for v in values)
    for r in records:
        if r["kind"] == "profile":
            a, b = root("identity:" + r["profile_group"]), root("profile-source:" + r["source_family"])
            parent[max(a, b)] = min(a, b)
            a = root(a)
            b = root("profile-content:" + digest([normalized(r["facts"]), normalized(r["skills"])]))
            parent[max(a, b)] = min(a, b)
        else:
            a = root("job-source:" + r["source_family"])
            b = root("job-content:" + digest([" ".join(r["title"].casefold().split()), normalized(r["skills"])]))
            parent[max(a, b)] = min(a, b)
    for r in records:
        groups[r["id"]] = root("identity:" + r["profile_group"]) if r["kind"] == "profile" else root("job-source:" + r["source_family"])
    manifest = {"version": 1, "seed": seed, "corpus_hash": digest(sorted(records, key=lambda r: r["id"])),
                "groups": groups, "splits": {k: split_for(v, seed) for k, v in groups.items()}}
    path = Path(path)
    if path.exists():
        old = read_json(path)
        if old != manifest:
            raise ValueError("frozen split/corpus changed; create a NEW versioned experiment")
        return old
    write_json(path, manifest)
    return manifest


def pair_stream(records, manifest, split="train"):
    profiles = sorted((r for r in records if r["kind"] == "profile"), key=lambda r: r["id"])
    jobs = sorted((r for r in records if r["kind"] == "job"), key=lambda r: r["id"])
    for p in profiles:
        for j in jobs:
            if manifest["splits"][p["id"]] == manifest["splits"][j["id"]] == split:
                yield p, j


class OriginalSkillAdapter:
    """Link to sanitized original skill; grounded content, NOT original rendering."""
    version = "public-skill-preferences-adapter-v2"
    def __init__(self, skill_path=None, confirmed_preferences=None, current_overrides=None, template_preferences=None):
        self.preference_layers = dict(confirmed_preferences=confirmed_preferences, current_overrides=current_overrides, template_preferences=template_preferences)
        self.skill_path = Path(skill_path) if skill_path else Path(__file__).resolve().parents[1] / "skills" / "resume-generation" / "SKILL.md"

    def _adapter(self):
        from .skill_adapter import SanitizedSkillAdapter
        return SanitizedSkillAdapter(self.skill_path, **self.preference_layers)

    def generate(self, profile, job, policy):
        return self._adapter().generate(profile, job, policy)

    def prepare(self, profile, job, policy, language=None):
        return self._adapter().prepare(profile, job, policy, language)


class GroundedRenderer:
    version = "deterministic-grounded-v1"
    def generate(self, profile, job, policy):
        # No inferred achievements, employers, credentials or numerical claims.
        skills = list(profile["skills"])
        if policy.get("relevance_first"):
            targets = {s.casefold() for s in job["skills"]}
            skills.sort(key=lambda s: (s.casefold() not in targets, s.casefold()))
        return "\n".join(["# " + profile["name"], "", "## Skills", ", ".join(skills), "", "## Evidence"] + ["- " + f for f in profile["facts"]]) + "\n"


def evaluate(profile, job, resume):
    expected = {s.casefold() for s in job["skills"]}
    supplied = {s.casefold() for s in profile["skills"]}
    coverage = len(expected & supplied) / max(1, len(expected))
    fidelity = "pass" if resume in {GroundedRenderer().generate(profile, job, {"relevance_first": flag}) for flag in (True, False)} else "fail"
    return {"skill_coverage": coverage, "label_origin": "heuristic", "hr_validated": False,
            "factual_fidelity": fidelity,
            "claim_checks": [{"claim_id": "fact-%03d" % i, "text": fact, "source_fact_ids": [profile.get("fact_ids", ["fact-%03d" % n for n in range(len(profile["facts"]))])[i]], "status": "supported_verbatim" if fact in resume else "not_shown"} for i, fact in enumerate(profile["facts"])],
            "fidelity_method": "Exact allowlisted deterministic rendering only; any deviation fails, not semantic entailment verification.",
            "overall_score": None, "export_ready": False,
            "dimensions": {k: "not_assessed" for k in ("jd_relevance", "clarity", "supported_achievements", "format_readability")},
            "notice": "Coverage is exact-string inventory only; no anchored rubric ratings or rendered artifact checks performed.",
            "feedback": ["prioritize_supported_skills"] if expected & supplied else []}


def next_policy(current, feedback):
    # Feedback affects the next distinct pair, never rewrites/retries this pair.
    return {"version": current["version"] + 1,
            "relevance_first": current.get("relevance_first", False) or "prioritize_supported_skills" in feedback}


def ledger_rows(path):
    if not Path(path).exists():
        return []
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line]
    previous = "0" * 64
    pairs = set()
    for i, row in enumerate(rows):
        body = {k: v for k, v in row.items() if k != "event_hash"}
        if row["event_hash"] != digest(body) or row["previous_hash"] != previous or row["sequence"] != i + 1:
            raise ValueError("run ledger integrity failure")
        if row["pair_id"] in pairs:
            raise ValueError("duplicate pair in ledger")
        pairs.add(row["pair_id"])
        previous = row["event_hash"]
    return rows


def run(records, out, limit=10, milestone=False, renderer=None):
    """Single writer lock, durable append and recovery from ledger (not checkpoint)."""
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lock = out / ".writer.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as e:
        raise RuntimeError("writer lock exists; investigate before removing stale lock") from e
    os.close(fd)
    try:
        manifest = freeze_splits(records, out / "splits.json")
        rows = ledger_rows(out / "runs.jsonl")
        checkpoint_path = out / "checkpoint.json"
        if checkpoint_path.exists():
            checkpoint = read_json(checkpoint_path)
            anchored = checkpoint.get("processed_examples", checkpoint.get("validated_examples", 0))
            if anchored > len(rows) or (anchored and rows[anchored - 1]["event_hash"] != checkpoint["last_hash"]):
                raise ValueError("checkpoint anchor mismatch: possible ledger truncation")
        renderer = renderer or GroundedRenderer()
        if rows and (rows[0]["generator_version"] != renderer.version or rows[0]["pipeline_version"] != VERSION):
            raise ValueError("generator changed; use new experiment directory")
        seen = {r["pair_id"] for r in rows}
        policy = rows[-1]["next_policy"] if rows else {"version": 0, "relevance_first": False}
        count = 0
        for p, j in pair_stream(records, manifest):
            pair_id = digest([p["id"], j["id"]])
            if pair_id in seen:
                continue
            if count >= limit:
                break
            resume = renderer.generate(p, j, policy)
            scores = evaluate(p, j, resume)
            nxt = next_policy(policy, scores["feedback"])
            row = {"sequence": len(rows) + 1, "pair_id": pair_id, "profile_id": p["id"], "job_id": j["id"],
                   "split": "train", "synthetic": p["synthetic"] and j["synthetic"],
                   "profile_hash": digest(p), "job_hash": digest(j), "provenance": [p["provenance"], j["provenance"]],
                   "pipeline_version": VERSION, "generator_version": renderer.version, "model_version": "none",
                   "prompt_version": "grounding-v1", "prompt_hash": digest(PROMPT), "rubric": RUBRIC,
                   "rubric_hash": digest(RUBRIC), "policy": policy, "policy_hash": digest(policy),
                   "next_policy": nxt, "resume": resume, "resume_hash": digest(resume), "scores": scores,
                   "previous_hash": rows[-1]["event_hash"] if rows else "0" * 64}
            row["event_hash"] = digest(row)
            with (out / "runs.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
            rows.append(row)
            seen.add(pair_id)
            policy = nxt
            count += 1
            if len(rows) % 10 == 0:
                write_json(out / "checkpoint.json", {"processed_examples": len(rows), "fidelity_passed": sum(r["scores"].get("factual_fidelity") == "pass" for r in rows), "expert_validated": 0, "last_hash": row["event_hash"], "next_policy": policy, "split_hash": digest(manifest)})
            if len(rows) % 100 == 0:
                publish_manifest(out, rows, "100-example checkpoint")
        if milestone:
            publish_manifest(out, rows, "explicit milestone")
        return {"added": count, "total": len(rows), "available_train_pairs": sum(1 for _ in pair_stream(records, manifest))}
    finally:
        lock.unlink()


def publish_manifest(out, rows, reason):
    # LOCAL candidate manifest, never a network publish or an authorization.
    write_json(Path(out) / ("publish-candidate-%06d.json" % len(rows)), {
        "processed_examples": len(rows), "fidelity_passed": sum(r["scores"].get("factual_fidelity") == "pass" for r in rows), "expert_validated": 0, "last_hash": rows[-1]["event_hash"] if rows else None,
        "reason": reason, "published": False, "requires": "privacy gate plus explicit release workflow",
        "quality_claim": "infrastructure only; heuristic diagnostics are not HR validation"})


SECRET_PATTERNS = [r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----", r"gh[pousr]_[A-Za-z0-9]{20,}", r"sk-[A-Za-z0-9_-]{20,}", r"AKIA[0-9A-Z]{16}", r"(?i)(?:password|api_key|secret)\s*[:=]\s*[\"']?[^\s\"']{8,}"]


def public_gate(records):
    for r in records:
        validate(r)
        if not r["synthetic"] or r["publication"] != "public" or r["provenance"]["license"] not in ("CC0-1.0", "MIT", "CC-BY-4.0"):
            raise ValueError("only explicitly public synthetic, clearly licensed records may be published")
        if r["provenance"]["license"] == "CC-BY-4.0" and not r["provenance"].get("attribution"):
            raise ValueError("CC-BY attribution required")
        text = json.dumps(r)
        if any(re.search(pattern, text) for pattern in SECRET_PATTERNS):
            raise ValueError("possible secret in public records")
        if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
            raise ValueError("email-like identifier requires removal from synthetic public fixture")
    return True


def export_qualified_labels(examples, destination):
    """Future SFT/DPO export: accepts only consented, reviewed human labels.

    The caller owns identity/consent verification; this is a fail-closed schema gate,
    not proof that supplied attestations are genuine. No heuristic self-training.
    """
    output = []
    for e in examples:
        if not (e.get("label_origin") == "human" and e.get("reviewed") is True and e.get("training_consent") is True and e.get("split") == "train" and e.get("annotator_id") and e.get("rubric_version")):
            raise ValueError("qualified human train labels required")
        if e.get("format") == "sft" and all(isinstance(e.get(k), str) and e[k] for k in ("input", "output")):
            output.append(e)
        elif e.get("format") == "dpo" and all(isinstance(e.get(k), str) and e[k] for k in ("input", "chosen", "rejected")) and e["chosen"] != e["rejected"]:
            output.append(e)
        else:
            raise ValueError("invalid SFT/DPO example")
    Path(destination).write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in output), encoding="utf-8")


def evaluate_holdout(records, split_manifest, split, destination, limit=10):
    """One-shot non-adaptive baseline smoke on frozen dev/test; never policy fitting.

    This is structural smoke, not an expert evaluation or final test score.
    Never inspect final test feedback to select a policy without retiring that test.
    """
    if split not in ('dev', 'test') or limit < 0:
        raise ValueError('held-out split and nonnegative limit required')
    if split_manifest['corpus_hash'] != digest(sorted(records, key=lambda r:r['id'])):
        raise ValueError('corpus differs from frozen manifest')
    policy = {'version': 0, 'relevance_first': False}
    rows=[]
    for profile, job in pair_stream(records, split_manifest, split):
        if len(rows) >= limit:
            break
        resume=GroundedRenderer().generate(profile,job,policy)
        rows.append({'profile_id':profile['id'],'job_id':job['id'],'split':split,
                     'profile_hash':digest(profile),'job_hash':digest(job),
                     'policy':policy,'adaptive_updates':False,'resume':resume,
                     'scores':evaluate(profile,job,resume),'model_version':'none'})
    result={'purpose':'non-adaptive structural smoke only','pipeline_version':VERSION,
            'split_manifest_hash':digest(split_manifest),'processed_examples':len(rows),
            'fidelity_passed':sum(r['scores']['factual_fidelity']=='pass' for r in rows),
            'expert_validated':0,'rows':rows}
    with Path(destination).open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    return {'processed_examples':len(rows),'fidelity_passed':result['fidelity_passed'],'expert_validated':0}
