# Judge calibration 001 — observed results

This is a small, independently authored **synthetic evaluator diagnostic**, separate from the requested 30 development pairs and not model-weight training. No human-expert annotation or candidate-quality claim is made.

## Integrity and method

All 12 input SHA-256 hashes match the pre-judge freeze and hashes recorded by the judge. The freeze-manifest hash is unchanged (`98eff0c6674f90d60807889cd7a22268e5c178a640b88707614b10f63d5d62f6`). Gold matches the original authoring bytes reconstructed in a separate temporary directory. Inputs, gold, judgments, allowlist and freeze manifest were unchanged by this assessment. Specific issue explanations and quoted locations were compared with frozen gold; a failing verdict alone did not count as detection.

The parent reports reviewer access was restricted to the allowlisted blind inputs and rubric. This assessment did not independently audit access logs. The reviewer is labeled `llm_judge_unvalidated/native_model_unknown`, rubric `0.1.0`; subjective confidence calibration remains **unknown**.

## Observations

- Actionable issue (including `needs_review`): **TP 9, FN 0, FP 0, TN 3**. Within this fixture only, sensitivity is 9/9 and specificity 3/3.
- All nine expected issue categories were detected, with supporting source reasoning; all 18 gold language/span entries were localized. The bilingual mismatch case identified both its wrong year and wrong count.
- Verdicts: **3 pass, 8 fail, 1 needs_review**. Controls `b4t9`, `d9k4`, `r8g5` have no alleged factual issues.
- Three-class comparison: **12/12 match** the interpretation of frozen expectations. Important: gold originally froze binary labels and prose, not explicit three-class fields; this is not a separately preregistered three-class accuracy result.

| Case | Frozen target | Derived expected | Observed | Target detected |
|---|---|---|---|---|
| q7m2 | unsupported_degree | fail | fail | yes |
| b4t9 | truthful control | pass | pass | not applicable |
| n8c3 | percent_vs_percentage_point | fail | fail | yes |
| v2r6 | inflated_team_ownership | fail | fail | yes |
| h5p1 | bilingual_numbers_dates | fail | fail | yes |
| d9k4 | truthful control | pass | pass | not applicable |
| s3w8 | inferred_language_proficiency | fail | fail | yes |
| f6a2 | in_progress_as_awarded | fail | fail | yes |
| j1u7 | historical_peak_as_current | fail | fail | yes |
| m4e9 | draft_as_executed | fail | fail | yes |
| r8g5 | truthful control | pass | pass | not applicable |
| c2z6 | unresolved_source_contradiction | needs_review | needs_review | yes |

## Ambiguity and limitations

The conflicting-date case `c2z6` appropriately received `needs_review`, not a claim that 2024 is demonstrably false. Its frozen expectation explicitly required confirmation and forbade assuming 2023 correct. No gold adjustment was needed or made. The reviewer additionally identified that the role title is absent from source facts: a valid unconfirmed-title concern, not an injected target and not a false positive on a control. This means that case was not perfectly isolated to one defect.

English fluency is unsupported, not proven false: `fail` here means a source-relative unsupported claim. No inference about actual candidate proficiency is warranted.

These are short, deliberately conspicuous cases, one per defect category and only three controls, with no repeated runs, human adjudication, externally verified source facts, or real-world prevalence sampling. Results show this judge caught these known problems; they do **not** establish perfect general accuracy, calibrated confidence, resume quality, ATS/export readiness, or hiring outcomes. Overall scores were null and rendering was not assessed.

## Portable-export caveat
The integrity findings above describe the original frozen experiment and comparison, not byte identity of this entire export. This export changes only absolute-path metadata in the allowlist, frozen manifest, and judgments; inputs and gold remain byte-identical. The original freeze-manifest SHA quoted above and in summary.json is historical. Exported-byte hashes and every changed field are recorded in public_safe_manifest.json and export_transformation_ledger.json. Judgment semantics, issue quotes, labels, findings and input hashes are unchanged.
