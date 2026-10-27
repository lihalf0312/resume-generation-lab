# Native bilingual pilot 001 — completed

**Three fixed synthetic profile/JD pairs produced once each: six Markdown resume contents, three independent native-LLM content reviews, and two feedback-driven prompt updates applied only to the next distinct pair.** No paid API or model-weight training was used. All original generations and their known defects remain unchanged.

## Results

| Pair | Profile / synthetic job | Material claim lines (both languages) | Factual gate | Full score |
|---|---|---:|---|---|
| 01 | SYN-007 / syn-001 accounting assistant | 22 | Pass | Not assessed |
| 02 | SYN-004 / syn-002 production improvement engineer | 24 | Pass | Not assessed |
| 03 | SYN-011 / syn-003 bilingual customer support | 24 | Pass | Not assessed |

The unvalidated independent judge found no unsupported material candidate claims among these 70 lines. This is **not** evidence that candidates meet the exact JD requirements: the judge marked all nine exact requirements `not_shown`, while identifying transferable or related evidence. Source-extract reconciliation was not relabeled invoice/ledger work; the technician was not upgraded to engineer; bilingual guide drafting was not upgraded to language proficiency.

Partial diagnostics were 93, 100 and 100 over the assessed 85% rubric weight. They are uncalibrated content-only judgments conditional on supplied fictional facts—not full scores, hire probabilities or comparable improvement measurements. Different inputs and prompts changed together; there is no controlled comparison or held-out evaluation.

## Feedback actually applied

1. Pair 01 → pair 02: remove repeated Chinese graduation date while retaining bold start/graduation field; add precise evidence questions outside the resume. Pair 01's redundant date remains preserved.
2. Pair 02 → pair 03: external gap criteria must not impose ownership/leadership beyond the JD; explicitly request actual customer-question-answering evidence in each language. Pair 02's overly strong ownership wording remains preserved.
3. Pair 03: no further content correction identified by this judge. No fourth generation or retrospective edits performed.

## Reproduction and audit trail

- `frozen_plan.json`: exact fixed sequence and flat-source hashes, saved before generation; `rich_sources_pre_generation.json`: supplemental rich-source snapshots including dates, also before generation. Existing split manifests were neither changed nor reseeded. These examples are exploratory development, not newly designated training pairs or a frozen benchmark.
- `prompt-v1.txt`, `prompt-v2.txt`, `prompt-v3.txt`: reusable instruction policies; each pair's decision record records its prompt hash and predecessor evaluation hash. Native generator model identity is unspecified, not invented.
- Each `pair-0N/` contains frozen source copies, bilingual text, line-level claim ledger, external requirement/gap notes, concise decision record, generation hashes and independent `evaluation.json`. `feedback_application_log.jsonl` links updates to the next pair.
- `skill_snapshot_manifest.json` hashes the sanitized formatting skill and references. `skill-snapshot/` preserves archival bytes but flattens references: its `formatting.md`, `format-contract.json`, `project.md` and `dependencies.md` map to `references/<same filename>` in the installable `../../skills/resume-generation/` tree. Use that tree for resolving skill links, not the flattened archive.
- `write_independent_evaluation.py`, if present, only serializes these specific manual/native-LLM judge decisions. Its fixed supported/pass labels are not a reusable semantic evaluator or an independent automated test.
- `pilot_summary.json` contains counters; final generation/source hashes were rechecked unchanged. Evaluation references marked pending inside frozen generation manifests are resolved by this final summary rather than mutating history.

## Limits and stopping condition

This run intentionally stops after three distinct pairs. No publication or push occurred. No benchmark or split metadata changed.

Outputs are **fictional content examples, not submission-ready documents**. No DOCX/PDF was generated or rendered. Absent original templates/fonts/margins/tab stops prevent template-fidelity claims. A4 page count, full-page utilization, paragraph final-line ratio >50%, preferred 67–80%, clipping, font fallback, alignment, effective Word spacing/punctuation settings, PDF extraction and ATS parsing are all **not assessed**. Markdown heading rules and bold dates only express formatting intent. Category ordering is provisional. Photos/political content/contact details were not supplied and were omitted. Sparse evidence was not padded to manufacture full-page density.

The facts are synthetic and not independently verified real accomplishments. One uncalibrated LLM judge is not HR validation. No reliability, generalization or quality-improvement claim is supported. A later authorized rendering phase needs actual templates and supported runtime; a valid improvement study needs a separate untouched benchmark and calibrated review.
