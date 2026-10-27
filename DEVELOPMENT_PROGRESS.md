# Development progress

Last verified: 2026-10-27 UTC. Counts below exclude the earlier three-pair pilot and deterministic smoke fixtures.

- Initial development target: 30 distinct profile/JD pairs; further batches may follow.
- Completed generation + independent evaluation: **30 / 30**.
- Factual gates: **29 pass, 1 needs_review, 0 fail** (unvalidated LLM judgment).
- Bilingual content outputs: 60 Markdown resumes; rendered DOCX/PDF outputs: 0.
- Initial source corpus: 30 fully fictional paired cases across 10 sectors.
- Current execution: native assistant workflow only; paid external model calls and weight-training runs: 0.

[Batch 003 summary](experiments/development-001/batch-003/SUMMARY.md) · [Batch 002 summary](experiments/development-001/batch-002/SUMMARY.md) · [Batch 001 summary](experiments/development-001/batch-001/SUMMARY.md) · [Evaluation report](experiments/development-001/batch-001/EVALUATION-REPORT.md) · [Publication limits](experiments/development-001/PUBLICATION_NOTES.md)

Scores describe presentation conditional on supplied facts, not candidate qualification or hiring odds. Missing requirements remain gaps; translations do not prove language proficiency. Each pair is generated once; subsequent feedback affects the next distinct pair. A small synthetic set does not establish reliability or improvement.

## Extension and evaluator diagnostic

The initial 30-pair target is complete. Richer additional cases 031–040 are in progress, separately counted only after generation and independent review.

A separate [12-case synthetic evaluator diagnostic](experiments/judge-calibration-001-public/RESULTS.md) is not part of the 30 development pairs. On these fixtures the judge flagged all 9 seeded issues (including 1 needs_review) and raised no issue on 3 controls. These small conspicuous examples do not establish general accuracy, calibrated confidence or HR-quality validity. The original inputs remain unchanged; public metadata paths are normalized with an explicit export ledger.
