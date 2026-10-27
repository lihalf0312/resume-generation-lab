# Status / 实测进度 — 2026-10-27

| 项目 / Item | Verified state |
|---|---|
| Original skill imported | **1 uploaded skill, sanitized public edition linked** — real source/reference hashes; original templates/photos/private facts/render scripts not included |
| Production generator/evaluator models trained | **0** |
| HR/expert labels collected or validated examples | **0** |
| Real arithmetic regression fitting | Unit test fits synthetic numeric labels; no HR meaning, no persisted deployed model |
| Local tests | **22 passed** (`python -m unittest discover -s tests -v`); hosted CI not configured/run |
| Fictional smoke corpus | 20 fictional profiles + 20 fictional jobs; schema + public synthetic gate checked |
| Current deterministic optimization smoke | **10 processed, 10 exact-renderer fidelity passes, 0 expert validated**; private_runs/verified-v2 |
| Research-input structural smoke | 12 original synthetic profiles + 8 real-source employer JD summaries loaded; **10 dev examples processed, 10 exact-renderer fidelity passes, 0 expert validated** |
| Research split constraint | All 12 profiles share one source family and freeze into dev; **0 eligible train pairs**. Kept this honest grouping; did not re-seed or relabel to manufacture train data. Dev smoke is fixed-policy/non-adaptive, not training or a quality benchmark. |
| Checkpoint test | 10-example checkpoint, 100-example local manifest, continuation/restart, duplicate content grouping, tamper/truncation detection tested in temporary directories |
| Public release | Parent-controlled release workflow; local candidate manifest is not a push |
| Actual PDF/DOCX/ATS checks | **0**; overall score null, export_ready false |

Skill coverage is an exact-string inventory diagnostic. Research JD requirement paraphrases are not yet normalized to profile skills, so zeros or matches are not candidate-quality or resume-improvement evidence. All anchored quality dimensions remain `not_assessed`. The exact renderer fidelity gate checks only faithful copying of supplied data, not whether the source facts are true.

Real-source employer records, original inputs and private run artifacts are not included in the initial publication allowlist. Human review is required for personal data, copyright and secrets beyond pattern scanners.

Pending: original skill text imported and content adapter implemented; obtain actual templates/assets and implement/verify Word rendering; normalize requirements; diversify consented source-family datasets; obtain reviewed labels; evaluate on held-out cases; implement/verify actual rendered resume exports. No quantitative quality improvement is claimed.

Automated training scope: synthetic/heuristic/LLM-judge feedback can support separately labelled experimental training; human labels are not required to start all ML. The linear baseline accepts any explicit label origin on train-only inputs. Weak-label SFT/DPO export is planned separately from the strict human-qualified exporter. Expert labels remain necessary for credible human-calibration/HR-validity claims. No paid calls have been made.

## Original-skill integration / 原技能接入

`OriginalSkillAdapter` reads `skills/resume-generation/SKILL.md` and hashes available references, carries the source format contract when present, and prepares grounded content plus explicit dependency/check requirements. Chinese drafts require aligned supplied Chinese facts; this adapter does not invent translations. Draft heading labels remain the deterministic English baseline, not a localized deliverable. The machine checks cover only a subset of full skill requirements.

Format-report tests cover A4/portrait/separate one-page languages, no font shrinking/blank padding, paragraph last-line >50% (67–80% preferred), Chinese double/English lower heading rules, date/graduation bolding, effective spacing/punctuation, bullet alignment, Word export and selectable text. Reports are untrusted assertions: `reported_pass` is **not** rendered-artifact verification, and `export_ready` stays false. Native pilot artifacts are separately owned/reviewed; these counters do not claim their outputs were rendered or trained.

The stricter Microsoft Word export report gate is an added current-task constraint; the sanitized source itself permits equivalently verified DOCX export tools. No missing template dimensions or quantitative bottom-whitespace tolerance are invented.

## Native LLM pilot / 原生小批量试验

[Three-pair report](experiments/native-pilot-001/REPORT.md): 3 distinct fictional profile/JD pairs, 6 bilingual Markdown contents, 3 independent unvalidated LLM reviews, 70 supported material claim lines according to that judge, and 2 feedback updates applied to the next pair only. All 9 exact JD requirements remain unestablished; presentation scores are not suitability scores. No same-pair rewriting, paid API, weight training, document rendering or improvement claim. Full scores remain null. Source inputs, prompts, outputs, feedback and hashes are preserved.

Current execution choice: existing product plan only; external paid providers remain disabled. Original visual templates are still missing.
