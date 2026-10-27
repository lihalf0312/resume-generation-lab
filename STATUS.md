# Status / 实测进度 — 2026-10-27

| 项目 / Item | Verified state |
|---|---|
| Original skill imported | **0** — Windows skill/template folder unavailable; adapter deliberately raises NotImplementedError |
| Production generator/evaluator models trained | **0** |
| HR/expert labels collected or validated examples | **0** |
| Real arithmetic regression fitting | Unit test fits synthetic numeric labels; no HR meaning, no persisted deployed model |
| Local tests | **16 passed** (`python -m unittest discover -s tests -v`); hosted CI not configured/run |
| Fictional smoke corpus | 20 fictional profiles + 20 fictional jobs; schema + public synthetic gate checked |
| Current deterministic optimization smoke | **10 processed, 10 exact-renderer fidelity passes, 0 expert validated**; private_runs/verified-v2 |
| Research-input structural smoke | 12 original synthetic profiles + 8 real-source employer JD summaries loaded; **10 dev examples processed, 10 exact-renderer fidelity passes, 0 expert validated** |
| Research split constraint | All 12 profiles share one source family and freeze into dev; **0 eligible train pairs**. Kept this honest grouping; did not re-seed or relabel to manufacture train data. Dev smoke is fixed-policy/non-adaptive, not training or a quality benchmark. |
| Checkpoint test | 10-example checkpoint, 100-example local manifest, continuation/restart, duplicate content grouping, tamper/truncation detection tested in temporary directories |
| Public release | Parent-controlled release workflow; local candidate manifest is not a push |
| Actual PDF/DOCX/ATS checks | **0**; overall score null, export_ready false |

Skill coverage is an exact-string inventory diagnostic. Research JD requirement paraphrases are not yet normalized to profile skills, so zeros or matches are not candidate-quality or resume-improvement evidence. All anchored quality dimensions remain `not_assessed`. The exact renderer fidelity gate checks only faithful copying of supplied data, not whether the source facts are true.

Real-source employer records, original inputs and private run artifacts are not included in the initial publication allowlist. Human review is required for personal data, copyright and secrets beyond pattern scanners.

Pending: obtain original skill; integrate its adapter; normalize requirements; diversify consented source-family datasets; obtain reviewed labels; evaluate on held-out cases; implement/verify actual rendered resume exports. No quantitative quality improvement is claimed.

Automated training scope: synthetic/heuristic/LLM-judge feedback can support separately labelled experimental training; human labels are not required to start all ML. The linear baseline accepts any explicit label origin on train-only inputs. Weak-label SFT/DPO export is planned separately from the strict human-qualified exporter. Expert labels remain necessary for credible human-calibration/HR-validity claims. No paid calls have been made.
