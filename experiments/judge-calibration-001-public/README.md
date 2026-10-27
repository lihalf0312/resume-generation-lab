# Synthetic judge calibration 001
12 original independent fictional source/profile + JD + bilingual resume cases. Separate evaluator diagnostic only; not part of the requested 30 development pairs, not a pilot derivative, and not model-weight training. No real identities or contacts.

Only `blind_inputs/*.json` may enter the judge context. They include source facts in English and Chinese, a bilingual JD, and candidate English/Chinese resume content. They contain no gold labels or error/control hints. `gold/` contains withheld factual expectations and the predeclared confusion-matrix plan. `frozen_input_manifest.json` records input hashes frozen before judging; `blind_input_paths.txt` is the submission allowlist. No judge has been contacted or scores produced.

## Portable public export
This directory is a path-normalized copy, not the original frozen experiment. Source inputs and gold are byte-identical. Only path metadata changed in judgments, allowlist, and frozen-input manifest. The manifest freeze timestamp refers to the original freeze; the copied manifest has a different file hash after path normalization. Original audit-hash references in RESULTS.md and summary.json are historical, not hashes of the exported manifest. Consult export_transformation_ledger.json and public_safe_manifest.json for exported-byte hashes. No labels, findings, quotes, input bytes, or input hashes changed. Nothing has been published or pushed.

## Current status — supersedes the setup note above
All 12 blind judgments are complete and the post-judgment comparison is available in RESULTS.md and summary.json. The earlier statement “No judge has been contacted or scores produced” describes the original pre-judgment setup only and is historical/superseded. The completed reviewer produced categorical judgments, not overall scores. This correction applies only to the public export; the original experiment README remains unchanged.
