# Native bilingual resume generation — development prompt v1
Generate exactly one English/Chinese resume pair from the frozen fictional source case using the five-file resume-generation skill. This is content-only Markdown; no template, pagination, DOCX/PDF, rendering or visual quality claims are permitted. Do not call paid APIs or perform training.
Read source facts, exclusions, corrections and requirements. JD requirements are not facts about the candidate; source evidence_status is only a design aid. Choose relevant supported experience and natural bilingual language without adding proficiency, qualifications, numbers, results or ownership. Keep organization, date, role, contribution and quantifier parity. Keep missing qualifications and clarification questions outside resume text. Use no placeholders or internal analysis in resume prose. Make evidence boundaries explicit where necessary, but do not turn the resume into a list of deficiencies.
Write resume.en.md and resume.zh.md once. Provide a stable claim-level ledger mapping corresponding EN/ZH factual spans to source fact IDs; external gaps with rationale and missing evidence; source, prompt, skill and output hashes; model native_model_unknown. Freeze the pair. Wait for independent reviewer evaluation before generating the next distinct case. Record applicable next-pair prompt changes or no-change rationale. Never repair a previously generated case, invent evaluator judgments or treat script checks as independent review.

# Version 14 cumulative addenda
Ensure every displayed date, including project and audit dates, is bold.
Read prompt-changes.json for case-specific review carry-forward; only adopt feedback relevant to this distinct source.
Chinese collocations: 具备/拥有权限 and 承担职责; avoid redundant qualifiers while preserving contribution limits.
Disambiguate coordinated verbs and participles; using printed instructions must never read as personally printing them. Keep grammatical actions within evidence in both languages.
Preserve completed versus intended review status: use reviewed by when review actually occurred, not merely for review.

Case-specific carry-forward record:
{
  "version": 14,
  "previous_case": "case-013",
  "previous_evaluation_sha256": "afea7a9d3622ca3b7b339ee0af293438aafb8699cc7a9b8d7db6f247fa1c1299",
  "changes": [],
  "reason": "Case013 had no new repair. Keep actual capability phrasing rather than upgrade can apply to unsupported project delivery or accessibility expertise."
}
