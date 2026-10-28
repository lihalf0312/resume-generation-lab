# Resume Generation Lab / 简历生成研究台

**140 fictional profile/job pairs, 280 bilingual Markdown resumes, and 140 brief score/comment views.** This is a content-only public snapshot, not a trained resume product or held-out benchmark.

## Browse

- [All 140 cases](data/development-140/index.json)
- [Results and limitations](DEVELOPMENT_PROGRESS.md)
- [Public data contract](docs/PUBLIC_DATASET.md)
- [General evaluation rubric](research/evaluation/rubric.json)
- [Generic resume skill](skills/resume-generation/SKILL.md)

Each case contains only factual `profile.public.json`/`job.public.json`, unchanged English/Chinese resume text, and `evaluation.public.json`. Evaluations publish **only the actual factual-status label, original dimension ratings, null overall score and brief bilingual comments**. No numerical full score is invented. Comments are newly prepared short summaries, not verbatim full reviews.

Detailed review reasoning, claim assessments, evidence/source mappings, coverage records, quotations, prompts, ledgers, gaps, provenance, snapshots, technical review metadata and design notes are **not included**. Private full records remain unchanged. Current-tree removal does not erase prior Git history.

## Run

Python 3.10+, standard library; safe filesystem checks require POSIX:

```sh
python -m unittest discover -s tests -q
python -O -m unittest discover -s tests -q
python -m resume_pipeline.public_dataset --root .
python -m resume_pipeline validate
python -m resume_pipeline public-gate
```

The exact public distribution passes **54 tests** normally and under optimization. Its validator checks only the five-file contract, factual source schemas and strictly limited score/comment fields. It does not read private full reviews, reproduce original source validation or certify semantic truth. The separate 40-record fictional fixture supports generic software tests; it is not part of the 140 reviewed pairs.

Generic code supports grounded content preparation, inert skill preferences and provisional format-report checks. No paid model calls, model-weight training, HR ground truth, demonstrated quality improvement, rendered-document verification, ATS certification or production readiness is claimed.

This publication is fixed at case 140; later authorized work is separate. See [STATUS](STATUS.md) and the [public-v4 manifest](publication-public-v4.json). A prepared package is not proof of an updated remote branch.
