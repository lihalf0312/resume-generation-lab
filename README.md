# Resume Generation Lab

面向岗位的中英文简历生成与可追溯评价研究。Bilingual, fact-grounded resume generation and evaluation research.

## Progress / 当前进度

Last verified: 2026-10-27 UTC.

- [x] Public repository initialized.
- [ ] Import and sanitize the original formatting skill (awaiting source files).
- [ ] Establish evidence-informed resume-quality rubric and source catalog.
- [ ] Prepare diverse, explicitly synthetic profile examples and sourced job requirements.
- [ ] Implement reproducible generation, evaluation, feedback and artifact logging.
- [ ] Run tests, privacy checks and a small end-to-end pilot.
- [ ] Calibrate evaluation with independently reviewed labels.
- [ ] Train and validate a model on leakage-controlled splits.

No model training has completed. No performance or hiring-outcome claims are made.

## Principles

- Remove the project owner's private biographical information. Preserve only reviewed, reusable formatting requirements.
- Never add invented achievements to a real person's resume. Synthetic training personas are clearly labeled and kept separate from sourced real cases.
- Public availability does not establish permission to redistribute. Keep source/license metadata; publish only cleared material.
- Evaluate resume presentation and factual consistency, not protected traits or a person's employability.
- Save inputs, output, rubric/model/prompt versions, scores and feedback for analysis.
- Improve on the next distinct profile–job pair rather than repeatedly optimizing one example. Freeze held-out evaluation sets.
- Prompt iteration, heuristic scoring and model-weight training are distinct stages and will be reported separately.

## Checkpoint policy

Target: local recovery checkpoint every 10 processed examples; a reviewed publication milestone every 100 validated examples or a substantial code milestone. Counts are not a substitute for privacy, licensing and test gates. No automatic paid training jobs.
