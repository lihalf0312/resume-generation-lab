# Resume evaluator: initial evidence-informed specification

## Useful result
Use a **factual-fidelity gate first**, then assess presentation on four distinct dimensions: JD relevance (35), clarity (25), supported achievements (25), and actual artifact readability (15). These weights are provisional product decisions—not empirical hiring weights. Never trade invented experience for a higher relevance score. No model has been trained by creating this specification or the synthetic fixtures.

`rubric.json` is the machine-readable contract. `sources.json` records six primary sources from an employer's recruiters, a recruitment firm, university career advisers, and an ATS vendor, checked 2026-10-27. `synthetic_cases.jsonl` is original, bilingual seed data for testing/annotation, not scraped resumes, validated training labels, or hiring-outcome data.

## Evidence and limits
- [Amazon's recruiter guidance](https://www.aboutamazon.com/news/workplace/amazon-job-application-resume-writing-tips) supports prioritizing relevant accomplishments, clear presentation, and available metrics. Its advice does not say every achievement requires a number.
- [Robert Half](https://www.roberthalf.com/us/en/insights/landing-job/8-tips-for-writing-a-resume) supports selecting from a master inventory, simple writing and truthful history. We deliberately exclude its generalized claim that software always blocks resumes before human review.
- [MIT's skills guide](https://capd.mit.edu/resources/resumes-writing-about-your-skills/) supports project/action/result descriptions and concrete scope. [MIT's toolkit](https://capd.mit.edu/resources/career-toolkit-crafting-an-effective-resume/) explicitly accommodates meaningful outcomes without exact numbers.
- [Greenhouse's parsing documentation](https://support.greenhouse.io/hc/en-us/articles/200989175-Unsuccessful-resume-parse) identifies extraction risks; parsing is not hiring selection. A failed parse can leave the document attached for manual entry. The documented 2.5 MB threshold applies to Greenhouse parsing, not every vendor or upload limit.
- [Greenhouse's language list](https://support.greenhouse.io/hc/en-us/articles/205019689-Resume-parsing-with-non-English-languages) includes English and Simplified Chinese. It establishes neither parity nor mixed-language accuracy; Traditional Chinese needs separate verification.

This is a practical initial source set, not “all internet” research. The strongest sources still offer guidance, not causal evidence for a universally valid resume score. Legal suffixes, expanded titles, or numeric impacts must never be invented to appease a parser. Source texts are not licensed training data: this folder retains short original summaries and URLs, not full copied pages.

## Evaluation procedure
1. Freeze user-confirmed source facts with IDs. Record whether facts were user-asserted, imported or separately verified; fidelity to supplied facts is not independent truth verification.
2. Split resume into material claims, preserving qualifiers, dates, team contribution, metrics, time windows and units. Mark supported, contradicted, or ambiguous against facts. Missing source facts trigger review, not an accusation.
3. Parse role requirements; separate required/preferred and reject protected or irrelevant criteria. Link each relevant requirement to a supported claim. Report missing evidence without rewriting history. Presentation quality is separate from qualification coverage: a truthful, well-presented resume may not establish every requirement.
4. Rate dimensions using anchored 0–4 judgments and evidence pointers. Exact keyword overlap is not a sufficient proxy for relevance. Do not punish a qualitative achievement because a source has no metric.
5. Export and inspect the real file. Verify extracted critical fields, glyphs and reading order, then rendered pages for overflow, clipping and contrast. Do not call HTML or JSON checks a PDF/DOCX ATS test.
6. Gate failure or uncertainty blocks approval and suppresses the overall score. Missing JD/artifact dimensions are not assessed, not zero. Optional partial scores disclose coverage and are not comparable to complete scores.
7. Give at most three prioritized fixes: location, issue, supporting facts, and a safe rewrite or precise question. Example: “Bullet 2 adds a 30% improvement absent from your source notes. Remove it, or provide the measurement and period.”

## Bilingual contract
Evaluate Chinese and English against the same canonical facts. Preserve institution names, official degree level, seniority, dates, metric units and attribution. Allow faithful transliteration and approved translations without forcing literal word order. An English action-verb or word-count rule must not be reused unchanged for Chinese. Chinese and English versions should be independently rendered and reviewed by language-competent raters. Translation mismatches are fidelity defects, not mere style issues.

## From heuristic to a defensible learned evaluator
The current deliverable is a source-informed rubric and synthetic fixtures. An optional LLM judge using it remains an uncalibrated judge, not a trained resume model. A learned model requires a separate, consented or licensed corpus, traceable annotation, a documented training job and held-out results.

Recommended next dataset: original/consented fact inventories + JDs + faithful and deliberately corrupted resume variants. Annotate claim entailment, dimension anchors, missing inputs and concise fixes. Use at least two independent reviewers, including competent Chinese/English reviewers; adjudicate disagreements. Save provenance, consent/license, language/locale, fact lineage, annotator confidence, rubric version and split assignment. Never include private resumes in a public repository by default.

Split by underlying person/fact inventory and related JD/template family *before* augmentation; translations and paraphrases of the same resume stay together. Keep a final untouched test set. Measure unsupported-claim detection precision/recall, blocker miss rate, agreement on ordinal scores, rewrite factuality, cross-language score consistency, and artifact extraction failures. Test name/pronoun/protected-trait counterfactual invariance without using those traits as score features. Test prompt-injection resistance, keyword stuffing, inflated titles, uncertain metrics, employment gaps, nontraditional experience and missing sources. Review errors by language and career stage rather than just overall averages. Report sample sizes and confidence intervals; do not manufacture performance or hiring-success claims.

## Stopping condition for this research pass
Delivered a diverse primary-source catalog, explicit rubric, feedback contract, and saved original seed cases. No external systems changed; no model was trained; production calibration and real artifact tests remain implementation work.
