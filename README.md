# Resume Generation Lab / 简历生成研究台

**可运行的离线研究基础设施，不是已优化的简历模型。** 原 Windows 技能尚未获得或迁移；没有恢复、模仿或验证用户原模板。`OriginalSkillAdapter` 明确报未实现。当前生成器只按原文渲染事实并调整已有技能顺序，不调用 LLM，不训练生成模型。

**Runnable offline infrastructure, not a trained resume product.** The original Windows skill remains unavailable. The baseline is deterministic and grounded in supplied facts; it is not a reconstruction of that skill. No paid calls, downloads, pushes, hiring predictions or background automation.

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
- `GroundedRenderer`: copies profile facts verbatim; only existing skills can be reordered. Original adapter deliberately unavailable. Missing original style is not guessed.
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

1. Obtain original skill folder and required templates/assets; review and implement its adapter without losing format.
2. Normalize real requirement ontology and validate human fact inventories; resolve data rights before any public corpus or model use.
3. Run provenance-labelled automatic evaluator experiments using synthetic, heuristic or LLM-judge feedback, with frozen held-out evaluation and cross-language/artifact tests. No paid judge call is enabled here.
4. Planned **separate weak-label SFT/DPO export**: record `label_origin` (`synthetic`, `heuristic`, `llm_judge`), evaluator/model/prompt/rubric versions and hashes, source permission/consent, train-only split, uncertainty, judge independence and artifact/fidelity gates. Keep these datasets distinct from human-qualified exports. Account for self-reinforcement, judge bias, reward hacking and train/test contamination; never call machine feedback HR ground truth.
5. Human/expert labels are needed for human calibration and HR-validity claims, **not a blanket prerequisite for automated ML experiments**. Compare actual trained versions on held-out data before claiming improvement. Current code implements the linear fitting baseline and human-qualified exporter; weak-label exporter and generator SFT/DPO execution remain planned, not delivered.

See [STATUS.md](STATUS.md) for measured progress. No CI workflow is included yet; local tests are the verified evidence, not an assertion that hosted CI passed.
