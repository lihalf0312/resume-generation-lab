# Status / 实测进度 — 2026-10-27

| 项目 / Item | Verified state |
|---|---|
| Original skill imported | **New user-approved public skill adopted** — required workflow/layout/preferences read and hashed; original templates/photos/private facts/render scripts not included |
| Production generator/evaluator models trained | **0** |
| HR/expert labels collected or validated examples | **0** |
| Real arithmetic regression fitting | Unit test fits synthetic numeric labels; no HR meaning, no persisted deployed model |
| Local tests | **27 passed** (`python -m unittest discover -s tests -v`); hosted CI not configured/run |
| Fictional smoke corpus | 20 fictional profiles + 20 fictional jobs; schema + public synthetic gate checked |
| Current deterministic optimization smoke | **10 processed, 10 exact-renderer fidelity passes, 0 expert validated**; private_runs/verified-v2 |
| Research-input structural smoke | 12 original synthetic profiles + 8 real-source employer JD summaries loaded; **10 dev examples processed, 10 exact-renderer fidelity passes, 0 expert validated** |
| Research split constraint | All 12 profiles share one source family and freeze into dev; **0 eligible train pairs**. Kept this honest grouping; did not re-seed or relabel to manufacture train data. Dev smoke is fixed-policy/non-adaptive, not training or a quality benchmark. |
| Checkpoint test | 10-example checkpoint, 100-example local manifest, continuation/restart, duplicate content grouping, tamper/truncation detection tested in temporary directories |
| Public release | Parent-controlled release workflow; local candidate manifest is not a push |
| Actual PDF/DOCX/ATS checks | **0**; overall score null, export_ready false |

Skill coverage is an exact-string inventory diagnostic. Research JD requirement paraphrases are not yet normalized to profile skills, so zeros or matches are not candidate-quality or resume-improvement evidence. All anchored quality dimensions remain `not_assessed`. The exact renderer fidelity gate checks only faithful copying of supplied data, not whether the source facts are true.

Real-source employer records, original inputs and private run artifacts are not included in the initial publication allowlist. Human review is required for personal data, copyright and secrets beyond pattern scanners.

Pending: original skill text imported and content adapter implemented; obtain requested templates or record generic fallback parameters and implement/verify compatible DOCX/PDF rendering; normalize requirements; diversify consented source-family datasets; obtain reviewed labels; evaluate on held-out cases; implement/verify actual rendered resume exports. No quantitative quality improvement is claimed.

Automated training scope: synthetic/heuristic/LLM-judge feedback can support separately labelled experimental training; human labels are not required to start all ML. The linear baseline accepts any explicit label origin on train-only inputs. Weak-label SFT/DPO export is planned separately from the strict human-qualified exporter. Expert labels remain necessary for credible human-calibration/HR-validity claims. No paid calls have been made.

## Active skill migration / 新版技能迁移

New public workflow adopted with defaults < measured template < confirmed preferences < current request. `OriginalSkillAdapter` requires actual workspace/layout references and a valid preference JSON; malformed/missing configuration fails closed. Explicit language selection, `zh`→`zh-CN` compatibility, configurable pages/headings, strict default final-line >0.5 with explicit override support, template-following spacing, conditional doNotCompress, and equivalent DOCX-to-PDF engine reports are tested.

No-template mode is explicitly `generic_single_column_unrendered`, not recovered original design. No uploaded code is executed; configured template paths are inert references, not opened by this adapter. All measurement reports retain `actual_style_verified=false`, `word_specific_properties_verified=false`, `export_ready=false` until a separate trusted artifact workflow verifies them.

**Correction:** The earlier Word-only default was an assistant-introduced mistake, not a user requirement. Both skill sources permit equivalently verified tools. The active adapter removes that restriction. Historical pilot files, outputs and source snapshots remain byte-for-byte unchanged; their old assumptions are historical, not active defaults.

See [migration notes](docs/SKILL_MIGRATION.md) and [uploaded-source hashes](docs/skill-migration-source-hashes.json). No template dimensions, fonts or bottom-whitespace numeric tolerances are fabricated.

## Native LLM pilot / 原生小批量试验

[Three-pair report](experiments/native-pilot-001/REPORT.md): 3 distinct fictional profile/JD pairs, 6 bilingual Markdown contents, 3 independent unvalidated LLM reviews, 70 supported material claim lines according to that judge, and 2 feedback updates applied to the next pair only. All 9 exact JD requirements remain unestablished; presentation scores are not suitability scores. No same-pair rewriting, paid API, weight training, document rendering or improvement claim. Full scores remain null. Source inputs, prompts, outputs, feedback and hashes are preserved.

Current execution choice: existing product plan only; external paid providers remain disabled. Original visual templates are still missing.
