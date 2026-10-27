# Resume Generation Lab / 简历生成研究台

**可运行的离线研究基础设施，不是已优化的简历模型。** 已按用户确认采用新版通用公开技能，并接入可配置偏好 `skills/resume-generation`；原模板、照片、私有事实库及渲染脚本未包含。`OriginalSkillAdapter` 读取真实技能及引用哈希，输出有事实依据的内容草稿和格式检查契约，**不声称已恢复模板或完成 Word/PDF 排版**。离线基线不调用 LLM、不训练生成模型。

**Runnable offline infrastructure, not a trained resume product.** The user-approved newer public skill is now the active workflow, with validated inert JSON preferences. `OriginalSkillAdapter` links its actual source and reference hashes, prepares grounded content and an explicit format-validation handoff. Original templates, private facts/photos and rendering scripts were not supplied. This adapter does not render Word/PDF or claim template fidelity. The offline baseline remains deterministic; no paid calls or automatic external pushes.

## Run / 运行
Python 3.10+; standard library only, no installation required:

```sh
python -m unittest discover -s tests -v
python -m resume_pipeline validate
python -m resume_pipeline run --limit 10 --milestone
python -m resume_pipeline public-gate
```

Default data: 40 explicitly fictional CC0 smoke records (20 profiles, 20 jobs). Default output: git-ignored `private_runs/experiment-v2`. Run again to continue **different** pairs. A single corpus has 126 train pairs; exhaustion stops normally, it does not recycle examples. Research directories contain separately sourced evidence and must not be confused with smoke fixtures.

## Architecture / 设计

- `core.py`: strict core schema, provenance, synthetic/publication flags; immutable corpus+split manifest; identity and profile-source connected components, and JD source families, and normalized exact content duplicates remain wholly in train/dev/test. Semantic near-duplicates still require human audit. Only within-split pairings are eligible. New corpus => new versioned experiment. Test/dev are never in optimization stream.
- `GroundedRenderer`: copies profile facts verbatim; only existing skills can be reordered. Original adapter now reads the new public skill and required workspace/layout/preferences files; missing or malformed configuration fails closed. Defaults < measured template < confirmed user preferences < current explicit request. Output language must be selected; `zh` aliases `zh-CN`. Missing templates use an explicitly unrendered generic single-column fallback, not guessed template fidelity. `format_contract.py` checks supplied report completeness/consistency, not actual visual compliance; even a reported pass leaves `actual_style_verified=false` and `export_ready=false`. Native generation is a separate workflow, not an external paid API.
- `runs.jsonl`: durable append-only, hash-chained ledger with pair/input/output hashes, scores, feedback, policy, prompt/model/rubric versions. Lock prevents simultaneous writers. Restart recovers from verified ledger, not potentially stale checkpoint. Invalid/torn ledgers stop for review rather than silently discarding examples. Hash chains detect edits but are not cryptographic authentication.
- Feedback updates a versioned policy for the **next distinct example**, not repeated optimization on the same profile/JD. It is rule-based, not learned model improvement.
- Counters distinguish processed examples, exact-renderer fidelity passes and expert-validated examples (zero). Every 10 examples: local state checkpoint. Every 100 or explicit milestone: **local publication-candidate manifest only**, not a GitHub push. No auto external publishing.
- Diagnostic skill coverage uses exact string matching, **not candidate quality or rubric score**. All anchored rubric dimensions remain `not_assessed`, full score is null, and `export_ready=false` without actual artifact validation. See `research/evaluation/` for provisional evidence-informed rubric, which still needs human calibration.
- `evaluator.py`: real optional linear regression (`fit`/`predict`) on supplied train-only labelled numeric vectors, with origin/hash tracking. Unit tests fit invented arithmetic labels solely to test code. **No HR-labelled evaluator or generation model has been trained.** No trained weight artifact or quality gain is claimed.
- `export_qualified_labels`: future SFT/DPO examples require human origin, reviewer, rubric, consent, review and train split. Caller must verify attestations. Heuristic scores cannot be exported as **human-qualified** labels. This does not prohibit machine-feedback experiments; a separate weak-label path is planned below.

## Safety / 发布边界

`public_gate` permits only explicitly public synthetic records with clear allowlisted licenses and required attribution; rejects real records, unclear rights, email identifiers and common secrets. `release.audit_release` inventories only explicitly selected allowlisted code/docs and the approved smoke fixture; excludes private runs, raw corpora and research data by default. **Pattern scanning is not proof of privacy or copyright clearance**; human review is still required. Public availability of a CV/JD is not training or redistribution permission. Do not include confidential resume inputs, contact details, private credentials, source dumps or unreviewed employer text in GitHub.

The framework accepts research-only real-source records locally; they do not pass the public data gate. Code/docs and references may be manually released separately after review. No repository-wide automatic collection exists.

## Next / 待完成

1. New public skill and configurable adapter adopted. Obtain original templates only when restoration is requested, or record actual fonts/page parameters for the generic fallback. Implement compatible DOCX-to-PDF export and independently inspect rendered pages; Word is not mandatory.
2. Normalize real requirement ontology and validate human fact inventories; resolve data rights before any public corpus or model use.
3. Run provenance-labelled automatic evaluator experiments using synthetic, heuristic or LLM-judge feedback, with frozen held-out evaluation and cross-language/artifact tests. No paid judge call is enabled here.
4. Planned **separate weak-label SFT/DPO export**: record `label_origin` (`synthetic`, `heuristic`, `llm_judge`), evaluator/model/prompt/rubric versions and hashes, source permission/consent, train-only split, uncertainty, judge independence and artifact/fidelity gates. Keep these datasets distinct from human-qualified exports. Account for self-reinforcement, judge bias, reward hacking and train/test contamination; never call machine feedback HR ground truth.
5. Human/expert labels are needed for human calibration and HR-validity claims, **not a blanket prerequisite for automated ML experiments**. Compare actual trained versions on held-out data before claiming improvement. Current code implements the linear fitting baseline and human-qualified exporter; weak-label exporter and generator SFT/DPO execution remain planned, not delivered.

See [STATUS.md](STATUS.md) for measured progress. No CI workflow is included yet; local tests are the verified evidence, not an assertion that hosted CI passed.

## Inspect the actual native-agent pilot

[Report and saved examples](experiments/native-pilot-001/REPORT.md) demonstrate three sequential bilingual generations with independent judge feedback applied to the next distinct pair. This is prompt/workflow optimization, not model-weight training or demonstrated quality improvement. All content is explicitly fictional; no personal applicant record is bundled. That historical pilot retains its original skill snapshot unchanged. The active [new public skill](skills/resume-generation/SKILL.md) now uses configurable defaults; see [migration notes](docs/SKILL_MIGRATION.md). Actual source templates and final rendered-document validation remain unavailable.

## Preference adapter API

`OriginalSkillAdapter(confirmed_preferences=..., current_overrides=..., template_preferences=...).prepare(profile, job, policy, language="en")` reads and hashes required references and preferences. The resolved configuration controls page count/size, language, headings, final-line bounds, spacing and conditional punctuation handling. Default final-line acceptance is strictly **>0.5**, not >=0.5; explicit user overrides are recorded. Compatible export engines are allowed. Reports remain untrusted measurements: passing schema checks does not verify actual rendering or Word-specific properties. See migration notes for changed API/report keys and corrected historical Word-only claim.

## Current development batches

See [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md) for completed generation/evaluation counts, retained defects and linked artifacts. These are additional to the initial pilot, not production training or rendered resumes.
