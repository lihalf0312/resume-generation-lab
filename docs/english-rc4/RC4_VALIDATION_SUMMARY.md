# RC4 validation annex — candidate, not published

This non-executable annex was added after testing. The 23 files under
`resume-generation-en/` are the unchanged frozen candidate actually exercised.
Its frozen file-set SHA-256 is
`ad8cdf46d42caf30c604b3a6aa6aaf1449ca4949ffbdf7f5cb57532065ab487d`.
The installation documents retain their dated historical context; this annex
records the completed RC4 acceptance outcomes rather than revising that snapshot.

## Software evidence

- 17 retained and 8 new Python regression tests passed (25 total).
- Four additional actual CLI rejection tests passed: identical, nested, ancestor
  and symlink-resolved nested workdirs. They used Python's bytecode suppression;
  source-open tracing and installed-file hashes showed no input read/write or
  package contamination in those tests. This is scoped evidence, not OS isolation.
- A real measurement followed by an explicitly injected font-validation failure
  left no accepted render. Correcting the private test configuration allowed the
  third, final permitted attempt to accept the same original DOCX. The failed
  attempts remain immutable. Exhaustion, stale receipts and downstream gates
  were also tested. No unbounded retry or font-size change was used.
- Acceptance requires actual embedded font evidence and bound artifact hashes;
  it does not prove a subset font binary equals the complete installed font.

## New-context writing acceptance A

One rich synthetic input was used in a fresh Codex context, without author facts,
expected answers or earlier drafts. The filesystem was shared, so this is not an
OS-enforced blind trial. Actual pages were 2 / 2 / 1 / 1: first draft, structural
pass, and two source-linked model-assisted edits. The final DOCX/PDF was inspected
and compared. Joint contribution and bounded result scope survived. No confirmed
final personal factual defect was found in this one assisted source review.

**Targeted content coverage is incomplete:** the identified-only need and
unimplemented proposal in the source were reasonably omitted throughout. Their
safe omission was checked, but preservation of their unfinished status inside
selected prose during compression was not exercised. No new generation was
performed to replace that result. An isolated tail line was repaired; a relatively
short remaining line and a readable date-range wrap remain layout preferences.

## Oversized software fixture B

A separate explicitly synthetic deterministic fixture remained four pages in
all six versions. Actual structural processing and four distinct source-linked
text edits were rendered. Final freeze was rejected, a fifth edit was rejected,
and state remained incomplete with no delivery. The operator inspected 24 pages;
an independent reviewer inspected the first/final eight pages and checked all
six PDF page counts. These are expected boundary-test results, not resume quality
scores or evidence of useful model compression. Recovery is bounded: four edits
used means zero remain. The generic status wording could state exhaustion more
clearly; the hard guard and documented counters are effective.

## Environment and limits

Observed platform: WSL2/Linux, Python 3.10.12 and LibreOffice 7.3.7.2, using
previously available local fonts and dependencies. This was not a clean-OS install.
For a relocated LibreOffice, its program library directory must precede support
library directories; configure these for the actual installation, for example
`${LO_ROOT}/usr/lib/libreoffice/program` before
`${LO_ROOT}/usr/lib/x86_64-linux-gnu`. No automatic font substitution is acceptable.

No hard software blocker was found for supervised trials on that same validated
platform. Full targeted content acceptance has not been established; this is not
an unattended-delivery or release approval. Native Microsoft Word, cross-engine
pagination, real ATS and Chinese output remain unvalidated. A/B are new runs;
predecessor development outcomes are not counted as RC4 acceptance.

Extra billed model APIs, credential changes and publication were prohibited for
this round. Those constraints and scoped command/hash observations are not an
OS-wide network or credential-access audit. The candidate awaits release review.
