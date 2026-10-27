# Initial requirements corpus — 2026-10-27

## Public subset and local research
This public release includes this methodology, source_catalog.json, and synthetic_scenarios.json only. The 12 sourced requirements records, pipeline adapter and build script listed below remain local pending redistribution review; their paths are not downloadable assets in this release. Source links are citations, not a grant to train on or republish third-party text.

## Local research delivered
- `requirements_records.json`: 12 sourced role records: **8 employer postings + 4 occupation references**, NOT 12 verified live vacancies.
- `source_catalog.json`: provenance, retrieval dates and licensing references.
- `synthetic_scenarios.json`: three **fictional** evaluation scenarios, separate from sourced records.
- `build_corpus.py`: reproducible local serialization of this manually reviewed research pass; it does not crawl sites.

Coverage: technical/software/security, analytics, finance, marketing, operations, design, health administration and manufacturing/engineering. Employer examples cover early, mid and senior career stages. Seniority is a curator annotation; taxonomy profiles do not imply seniority or universal hiring requirements. Empty requirements lists mean not extracted, NOT no requirements.

## Status and evidence limits
Official employer content was inspected through the web tool on the retrieval date. `appears_live` means the retrieved page displayed an application affordance, not that an application was submitted or the employer confirmed hiring. Cached/indexed content may lag. No application endpoints were exercised.

- Amazon analyst 10414756: indexed official qualifications exist, but direct fetch returned 404. Stored as `unavailable_likely_expired`; closure is not confirmed.
- Boeing JR2026509159-1: indexed official ATS requirements were available; direct open returned an empty body. Status remains `unknown`, not expired or live.
- Walmart and Idera: posting pages retrieved; hiring-open status remains unverified.
- Adobe: discovery listing changed between search and direct open; the dedicated official Adobe Design page was used instead.
- A guessed ESCO licensing URL was inaccessible via the web tool. No workaround was used; the official searchable FAQ supplied reuse conditions instead.

This is a small convenience sample, biased toward English-language US/India postings and large employers; it does not establish job-market frequency, skill prevalence, regional norms or representativeness. Source excerpts were minimized and paraphrased; full page text, names, emails and phone numbers are not stored. Employer job-title/product strings are retained as identifiers.

## Reuse and attribution
Employer postings: no open redistribution permission was established. Public availability is not an open license. Keep only these compact factual paraphrases and source links; do not redistribute full JDs, scrape at scale, or treat this file as permission to train on source text. Recheck relevant terms and rights before a public dataset release.

O*NET core occupation material: the source's license permits reuse/adaptation with attribution, license link and notice of changes. Third-party content on O*NET pages may have different terms; this set excludes wage data, external links, credentials and external datasets.

Attribution for the four occupation summaries: This material adapts information from O*NET OnLine, U.S. Department of Labor, Employment and Training Administration (USDOL/ETA), under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). O*NET® is a trademark of USDOL/ETA. The project has shortened and paraphrased the information; USDOL/ETA has not approved, endorsed or tested these modifications. Changes are visible in the short `responsibilities` summaries; source URLs identify the originals. [Source license](https://www.onetonline.org/help/license).

The downloadable O*NET 31.0 database has its own documented CC BY 4.0 scope. No bulk database was downloaded in this pass. Pin version and file-level provenance if importing later: https://www.onetcenter.org/database.html.

ESCO classification reuse is addressed in its [official FAQ](https://esco.ec.europa.eu/en/about-esco/faq): reuse under Commission Decision 2011/833/EU requires acknowledging ESCO and clearly indicating adaptations. API software licensing (EUPL 1.2) is distinct from classification data reuse. No ESCO occupation records were imported here.

## Bilingual use
ESCO v1.2 language coverage includes English and 27 other languages, **not Chinese**, according to its [language page](https://esco.ec.europa.eu/en/about-esco/escopedia/escopedia/esco-languages). Do not present generated Chinese skill translations as official ESCO terms. If Chinese/English is the intended pair, retain canonical English skills and source IDs; add reviewed Chinese aliases with explicit `translation_origin` and review status. This corpus remains English-only pending a translation/locale specification. Translated resume output never proves a candidate's language proficiency.

## Safe evaluation use
- Keep employer-required qualifications separate from preferences and duties.
- Never fabricate a degree, credential, clearance, years of experience, tools or results to satisfy a JD.
- Employer-specific eligibility conditions must not become global resume scoring rules. The Boeing clearance note is a role fact, not authorization to infer citizenship or sensitive attributes.
- Taxonomy competencies are context, not employer requirements. Synthetic scenarios are evaluation fixtures, not market evidence.
- Avoid numeric match-score claims without validated scoring criteria. Test evidence-linked tailoring, omission of unsupported claims and clear candidate-confirmation prompts instead.
