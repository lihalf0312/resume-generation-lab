# Development extension 004 — challenging sources

Cases031–040 are 10 new, entirely fictional people/vacancies with distinct original lineages. This extension is development data, not a held-out test set. All original 001–030 source files and their root SHA256 manifest are preserved. This extension has its own `source-manifest-v1.sha256.json` and `../validate_extension_004.py`. The initial validator is scoped to its original three batches so extensions do not invalidate its frozen coverage check.

## Changed contract

- Profiles contain 16–22 fact objects instead of 8–12; this batch has 170 facts total.
- `job.json` contains only bilingual requirement IDs/text, not evidence labels or fact support mappings.
- `curation-notes.json` holds author-designed direct/transferable/missing mappings. Keep this file out of generation and blinded evaluation context; independently judge factual support before using curation for comparison.
- `profile.json.uncertainties` explicitly marks unresolved notes using id, en, zh, affected_fact_ids, status=confirmation_required, and safe_handling. An unverified assertion inside a source fact is not permission to state it as true. Omit the disputed detail rather than resolving it by invention. Firm facts around an unresolved claim may still be used at their documented scope.
- Profile facts include overlapping full-time/part-time/volunteer dates with context, unfinished education, peak versus current volumes, team versus individual contributions, drafts versus delivered work, unrelated projects/hobbies, and outcome denominators and periods. Preserve these distinctions across English and Chinese.

## Workflow boundary

Only profile and job files are generation inputs. Sources contain enough directly relevant evidence to avoid all-gap samples, but explicit omissions and transferable skills must not be promoted into licences, certified language proficiency, technical production ownership, completed degrees, savings causality, authority, or implemented proposals. Gap notes belong outside the resume. Inconsistent dates/counts/titles should be omitted or flagged externally for confirmation. No resume or score is part of this extension preparation.

All content is original synthetic authoring, public-safe CC0-1.0; no real person, employer, contact details, or private dataset is represented. First-five manifest records the earlier freeze of cases031–035 and remains valid alongside the full extension manifest.
