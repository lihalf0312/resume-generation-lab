# Carry-forward prompt for next distinct development pair (v11)

Use base-prompt.md in this batch and all five files of the public resume-generation skill. Generate one bilingual Markdown pair exactly once from the next frozen source, preserving facts, dates, organizations, contribution, ownership, metrics and uncertainty. Do not infer qualifications from the JD or treat source requirement labels as truth. Keep gaps outside resume text and maintain a claim-level evidence ledger and source/prompt/skill/output hashes. Model identity remains native_model_unknown.

Cumulative reviewer-derived checks:
- Bold every displayed date, including projects/audits; rendering remains not_assessed.
- Use natural Chinese collocations: 具备/拥有权限, 承担职责. Avoid redundant scope qualifiers without dropping necessary boundaries.
- Disambiguate coordinated verbs/participles. A phrase about using printed instructions must not read as printing them; check EN/ZH action parity.
- NEW from case-010: preserve actual completion status. If evidence says a lead reviewed a checklist, use reviewed by, not merely for review; keep both languages equivalent.

Record previous_case=case-010 for case-011 and the newly applied completion-status change. Freeze output; request independent native evaluation and wait before generating case-012. Apply any new feedback only to the next distinct pair. Never revise earlier cases or self-score. Completed = generated + independently evaluated; separately count pass/needs_review/fail. No training, paid APIs, DOCX/PDF export or visual claims.
