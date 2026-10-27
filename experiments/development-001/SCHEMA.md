# Development corpus source contract

All people, organizations, educational establishments, activities, metrics, and vacancies are expressly fictional original authored material, released for public reuse under CC0-1.0. No names or contact details of real people occur. Each source lineage belongs to exactly one distinct fictional person; `creation_batch` only records the shared authoring run. These are development cases, never held-out test claims or split-diversity tricks. Reserved original pilot pairs SYN-007, SYN-004, and SYN-011 and their content are not reused.

## Files and IDs

`batch-NNN/case-NNN/profile.json` and `job.json` are frozen paired sources. Case IDs are global in this corpus; fact IDs F01… and requirement IDs R01… are local to the case and must be qualified as `case-NNN/F01` across cases. Profile has identity_id, source_family, creation_batch, synthetic=true, sector, career_stage, evidence_density, fit_type, and 8–12 facts. Each fact has id, kind, en, zh, and explicit synthetic provenance. Kind is education, employment, project, skill, outcome, or other. Job has case_id, synthetic=true, bilingual title, synthetic vacancy label, and 3–5 requirements.

Career-stage strings early/early-career, mid/mid-career, and career-change are synonymous spellings; density rich/sparse describes source depth, not candidate ability. Fit type is an authoring stratum, not an evaluation score.

Each requirement has id, en, zh, evidence_status, supporting_fact_ids. `direct` means listed source facts explicitly support the requirement at their stated scope; `transferable` means related evidence exists but must not be promoted to direct domain/tool/ownership experience; `missing` means the source provides no supporting evidence and its reference list is empty. Direct does not mean enterprise production work when a fact only supports a personal project. Explicit absence statements are boundary guards, not resume bullets. Bilingual factual text must preserve dates, qualifications, metric scope, attribution, and uncertainty.

## Use and evaluation boundaries

Resume generation must be sequential native-LLM, draw only from frozen facts, and create English/Chinese outputs and fact-level claim ledger outside source files. Do not fabricate contact data or missing qualifications. Keep material gaps explicit in a separate gap record; do not insert 'I lack X' into the resume. No generation or evaluation scores are included in this corpus.

## Freeze and verification

`source_manifest.sha256.json` at corpus root maps all 60 source files to SHA256 hashes. Batch-specific manifests predate any generation for that batch. Frozen sources may not be modified in place: correction requires explicit versioned sources and new provenance, never rewriting history. `validate_corpus.py` checks counts, unique identities/lineages, fact/requirement IDs and references, evidence labels, numeric/date consistency, degree translation heuristics, and full manifest coverage. It does not prove semantic entailment or qualification validity; native-LLM review remains necessary. The report states limitations.
