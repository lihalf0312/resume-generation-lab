# Development batch 001 — completed

Ten distinct fictional profile/JD pairs were generated once each, in English and Chinese, by the native assistant. A separate native reviewer evaluated every frozen pair before the next generation began. Scripts only persisted authored text, computed hashes and aggregated already-written evaluations; no paid model calls or training occurred.

## Outcomes

- Generated: **10**; independently evaluated: **10**; completed: **10**
- Factual fidelity: **9 pass, 1 needs_review, 0 fail**
- Retained issue: case-007 C06 English wording permits an unsupported printing action, unlike the intended use of printed instructions. It was not repaired or regenerated.
- Content presentation scores: 100, 100, 93, 100, 100, 100, 93 diagnostic, 100, 100, 93. Scores describe only assessed content dimensions, not candidate merit, job fit, hiring probability or validated HR judgment. The reviewer is `llm_judge_unvalidated`; model identity is `native_model_unknown`.
- All full scores are null, export_ready false and visual checks not_assessed. Only Markdown content was created; no Word/PDF or template/render claims.
- Source and frozen output SHA256 checks: no changes detected.

## Sequential improvements

1. Case-001 → case-002: bold project dates as well as employment/education dates.
2. Case-003 → case-004: natural Chinese collocations (具备/拥有权限; 承担职责), concise contribution-boundary phrasing. Case-009 subsequently used these in relevant authority/responsibility claims.
3. Case-007 → case-008: disambiguate coordinated verbs and participles to prevent a tool/material description from reading as an unsupported action.
4. Case-010 → next distinct case: preserve completed versus intended review status in both languages. Source says reviewed, so do not weaken it to merely for review.

Cases with no new reviewer repair recorded a no-change rationale; cumulative earlier rules remained in effect. No prior pair was rewritten.

## Requirement evidence disagreements

`source-label-disagreements.json` records five disagreements without changing sources: case-001 R02 (writing tests is not executing them), case-004 R02 (help/use is not maintenance ownership), case-005 R02 (invoice status is not explicit payment status), case-007 R04 (observed escalation directly supports general escalation behavior), and case-010 R01 (paid-worker availability is not volunteer availability). Source annotations are design aids, not gold labels; independent review is also unvalidated.

## Artifacts and continuation

Each case has source files, EN/ZH resumes, stable local claim IDs and fact links, external gaps, actual prompt, version-change record, five-file skill hashes, provenance/output hashes, and independent evaluation JSON/Markdown. `batch_manifest.json` is the compact completion index; `progress.json` embeds reviews. `base-prompt.md` plus `next-batch-prompt.md` are reusable instructions. Author scripts are persistence records of native authored content, not a generation service; frozen guards prevent overwriting outputs.

Continue with frozen case-011 in batch-002, applying case-010 feedback only forward. Keep the independent sequential review gate. Content-only development is not a final formatted resume evaluation.
