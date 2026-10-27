# Development sample publication notes

This is exploratory synthetic development data, not a held-out benchmark or production training run. Native generator and evaluator identities are unspecified; the evaluator is uncalibrated and its labels are not HR ground truth.

The initial corpus-wide source manifest records its freeze at 18:06:45 UTC on 2026-10-27, after case-001 generation at 18:06:08. The earlier batch source manifest has no timestamp. Case-001 generation provenance captures input hashes matching the released sources, but this does not establish a timestamped corpus-wide preregistration before that generation. History is preserved, not backdated.

Source evidence-status annotations are corpus-author design aids, not gold labels. The independent evaluator receives a projected job view without these answers; source-label disagreements remain available for analysis.

Public files include sources, prompts, actual generated contents, evidence ledgers, evaluations, forward feedback and hash manifests. Temporary authored-text/judgment serialization helpers and mutable progress checkpoints are excluded: they are not reusable model inference services. The reusable corpus validator is included. Replaying native model output is not guaranteed.

Batch manifests cover their documented artifacts and transitive output hashes. The parent publication manifest additionally inventories released reports, schemas and other final files. Completed means generated and independently evaluated, not passed: case-007 remains needs_review because one English clause can imply an unsupported printing action. All originals are retained without retrospective correction.

No paid model API, model-weight training, DOCX/PDF rendering, visual validation, ATS certification or causal quality improvement is claimed.
