# Independent review and status records

Review the actual candidate prose against the original source and preserve the review separately from generation. A quotation match, valid ID chain, scope annotation or schema pass does not establish entailment, completeness, factual truth or writing quality. Bind source review to the original input/material hash and identify the candidate version. Keep author answers and grading rubrics outside generation; assessment must not guide selection. Do not treat one person's versions, paraphrases or intentionally missing/conflicting variants as independent people in development evaluation. Small directional samples do not establish population error rates, causal effects of input format, or model rankings; a more expensive reviewer is not automatically ground truth.

Use one observation per distinct concern, while preserving the original review verbatim in a separate immutable record. A normalized observation has:

```json
{
  "category": "pending_ambiguity",
  "speech_act": "neutral_observation",
  "defect_confirmed": null,
  "original_problem_detected": null,
  "human_judgment_required": true,
  "reason": "Meaning requires source comparison or clarification."
}
```

These fields have independent meanings:

- `defect_confirmed`: true only when comparison of source and candidate establishes a defect; false for a checked non-defect or reasonable omission/paraphrase; null when unresolved. A source support gap is not proof that the real-world activity never happened.
- `original_problem_detected`: true if the preserved original review actually identified this particular concern, false if it did not, null when there is no prior review or it cannot be determined. Do not derive it from defect confirmation. If a prior reviewer noticed the concern but used a weaker category, preserve the detection detail instead of calling it a complete miss.
- `human_judgment_required`: whether a further editorial/source judgment is still needed. Set it explicitly; never derive all three states from one label.
- `speech_act`: `error_allegation`, `neutral_observation`, `positive_observation` or `expression_suggestion`, describing what the review statement does. A positive or neutral comment is not an error allegation merely because it shares a topic with a later issue. Count a factual-review false positive only when an explicit factual allegation is disproved by the source; do not turn neutral notes, optional suggestions or observation counts into confirmed factual errors.

The canonical field is `original_problem_detected`. If an imported review used `original_review_detected`, retain that original record and explicitly document its mapping to the canonical field in a separate normalization record. Do not overwrite raw labels, rationales or earlier evaluations. If a label and rationale conflict, save the conflict and a separate reassessment. Retractions update the current summary with a link to the earlier record, preserving history.

Allowed categories are `source_support_gap`, `factual_contradiction`, `responsibility_expansion`, `reasonable_paraphrase`, `pending_ambiguity`, `reasonable_omission`, `important_evidence_omission`, `expression`, `test_protocol`, `citation_integrity`, `job_fit_gap`, `positive_observation` and `duplicate`. Keep categories separate; observation counts are not factual-error counts. A missing/invalid citation or fact reference is citation integrity, not automatic factual contradiction. A precisely cited sentence can still expand responsibility. Unused intermediate analysis that never reached the candidate or evaluator is not that evaluator's missed resume defect. Confirmed reasonable omissions/paraphrases have `defect_confirmed=false`; ambiguity stays null and requires judgment. Important-evidence omission concerns selection; it is distinct from inventing a personal claim.

For any factual allegation, compare who acted, the action, object, medium, organization, period, phase, population, metric basis and result scope in complete context. Record the actual source fragments, candidate wording and version outside the resume. Support gaps, explicit contradictions and unresolved readings must remain distinct. Evaluate English naturalness, evidence targeting and experience organization separately from fidelity. An evaluator's proposed smoother verb can itself add unsupported authorship or execution; check suggestions before adopting them.

# Clarification, marker and layout responsibility

Necessary questions affect current truth or important selection; optional enhancements do not block a safe draft. Unanswered necessary questions retain `status=awaiting_user`, `answer=null` and existing `affected_fact_ids`; never invent an answer. An empty affected-fact list is allowed for new information without an existing fact, with an explanation outside the resume. A disputed claim used without safe omission blocks editorial acceptance; safe omission permits supported delivery while the question remains unresolved. Answered questions record the user's actual answer and source. The runtime validates reference integrity only, not whether a question is necessary, answered truthfully or safely omitted.

Synthetic identity is controlled by the explicit runtime input. Generation need not contain a marker; the delivery layer adds and checks it for synthetic input. A missing synthetic delivery marker is a test-protocol/delivery issue, not a personal factual error. Real resumes receive no synthetic marker by default. Preserve prior evaluations if this responsibility was misclassified; save corrections separately.

A failed PDF-token mapping is a measurement failure, not a confirmed short-tail defect. Headings, dates and one-line fields are exempt from prose-tail ratios. Multiline short-tail flags are advisory and require visual/editorial review; do not use filler or smaller type. A one-page render pass does not prove source fidelity, job fit, typography on another engine or ATS acceptance. Actual images, content extraction and the original source must still be inspected.

`review_rules.validate_observation()` validates only the declared record's fields, types and allowed categories/speech acts. If a self-review includes `observations`, freeze checks these record shapes. It does not independently classify prose, enforce the truth of declarations, prove a review was exhaustive, or infer one state from another. `synthetic_mark_review`, `clarification_review` and `tail_review` retain their narrower stage/responsibility/advisory roles.

`delivery_invariants(rows, source)` is enforced at freeze: it rejects missing, changed or duplicate synthetic markers, an automatic marker on real input, and missing/changed/duplicated or wrongly typed Target rows. Its source_truth_verified field remains null because this checks presentation against declared runtime intent/identity, not personal factual support.
