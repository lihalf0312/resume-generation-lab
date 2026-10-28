# Public dataset v4 — factual content, scores and brief comments

Each case has exactly five files: factual `profile.public.json` and `job.public.json`, unchanged `resume.en.md` and `resume.zh.md`, and a minimal `evaluation.public.json`.

Factual views retain supplied fact and requirement text, without design annotations. They are not complete original inputs. Detailed original reviews and all process records remain private and unchanged; the public package is not a historical replay bundle.

## Evaluation fields

Only these fields are allowed:

- `case_id`
- `factual_status`: the actual native label, not a new assessment
- `overall_score`: always null in this content-only snapshot
- `dimension_ratings`: the four actual ratings with bilingual labels and their original 0–4 scale; null means not assessed
- `brief_feedback_zh`, `brief_feedback_en`: short newly prepared summaries, not verbatim full reviews
- `review_limitations`: fixed unvalidated/content-only statements
- `disputed_label`: true for the retained disputed interpretation

Only original dimension ratings are published; other partial-score fields are deliberately omitted. No aggregate/full score is computed or invented. Brief summaries use actual dimension outcomes or specific overall criticisms. High ratings are not summarized as proof of no problems.

No claim audit, coverage record, source/evidence mapping, detailed rationale, source quotation, technical pointer, original hash, prompt, ledger, gap, provenance or predecessor material is included in evaluation records. The validator rejects extra fields at every level and internal references in comments. Ordinary generic software assertions are not dataset answer keys.

```sh
python -m resume_pipeline.public_dataset --root .
```

This read-only command checks public file membership, schemas, identities, rating scales and short-comment boundaries. It never opens private full records. Structural validation is not semantic entailment, independent reviewer calibration or exhaustive privacy certification.

No actual rendered-document or ATS validation is claimed. Current-tree removal does not erase prior Git history. This milestone contains only cases 001–140; later work is separate.
