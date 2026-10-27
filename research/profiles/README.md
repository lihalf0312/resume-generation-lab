# Career case research / 经历案例研究

## What is included
- 12 wholly original **synthetic** bilingual (English / Simplified Chinese) profiles, with 133 fact IDs.
- Graduate, career-switcher, returner, apprentice, freelance, mid-level, manager, senior and doctoral-candidate scenarios across 12 sectors.
- Education, dated work, scoped achievements, projects, skills and hobbies in every case. No real names, contact details or user experience.
- `synthetic/` is the rich fact-level representation. `synthetic_profiles.jsonl` is the pipeline adapter; aligned `fact_ids` and `facts_zh` preserve provenance.
- `sourced_references/source_registry.json` is a **separate reference registry**, not a genuine-profile training dataset. Four genuine career case references were found, but reuse rights remain unverified. No genuine biography was ingested. URLs may contain a publisher’s person slug; those are citations, not extracted identity fields.

## License and privacy
Original synthetic data is offered under CC0-1.0 (https://creativecommons.org/publicdomain/zero/1.0/). Source references retain their own status; CC0 does not apply to linked pages or third-party material. Public visibility is not consent to reuse a biography. BLS prose has a stated public-domain policy; excluded images and trademarks are not reused. O*NET licensing is specific to covered downloadable database files and requires attribution. JSON Resume schema licensing does not license personal registry data.

Do not add real identity/contact data to these fictional facts. Do not append invented accomplishments to genuine case-study people. Real-person ingestion requires a documented lawful basis, permission/license review, minimization and removal process. No sensitive attributes, patient records, student identifiers or reasons for career gaps were collected or inferred.

## Grounding contract
Each rich-profile fact has a stable ID and paired `en` / `zh` text. Dates and metrics are intentionally invented and marked synthetic, not attributed to any external source. BLS is occupational context only, not evidence for individual achievements. Generate only by selecting, translating, shortening and reordering source facts. Missing credentials, dates and metrics must remain missing or trigger a question. Preserve denominators, observation windows, team scope, uncertainty and non-causal qualifiers. Professional study is not licensure; a doctoral candidacy is not an awarded doctorate. Hobbies should be optional and must not become inferred protected characteristics.

## Diversity and limitations
Diversity here concerns sectors, experience levels, employment patterns and qualification routes, not inferred race, disability or other protected traits. Small fixtures are useful for integration tests, not representative labor-market training data. Synthetic numeric achievements are test inputs, not evidence of model factual accuracy in genuine resumes. Split by profile group so translations or paraphrases of one candidate never cross train/test partitions. Any later real examples must remain separately tagged and blocked from public export until cleared.
