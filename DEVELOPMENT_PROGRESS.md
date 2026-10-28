# Development results — fixed 180-case public snapshot

**180 fictional pairs, 360 bilingual resumes and 180 simple score/comment records.** Actual native factual-status labels remain 175 pass, 5 needs_review and 0 fail. These labels are unvalidated.

## Browse

| Cases | First case | Last case |
|---|---|---|
| 001–010 | [case-001](data/development-140/case-001/evaluation.public.json) | [case-010](data/development-140/case-010/evaluation.public.json) |
| 011–020 | [case-011](data/development-140/case-011/evaluation.public.json) | [case-020](data/development-140/case-020/evaluation.public.json) |
| 021–030 | [case-021](data/development-140/case-021/evaluation.public.json) | [case-030](data/development-140/case-030/evaluation.public.json) |
| 031–040 | [case-031](data/development-140/case-031/evaluation.public.json) | [case-040](data/development-140/case-040/evaluation.public.json) |
| 041–050 | [case-041](data/development-140/case-041/evaluation.public.json) | [case-050](data/development-140/case-050/evaluation.public.json) |
| 051–060 | [case-051](data/development-140/case-051/evaluation.public.json) | [case-060](data/development-140/case-060/evaluation.public.json) |
| 061–070 | [case-061](data/development-140/case-061/evaluation.public.json) | [case-070](data/development-140/case-070/evaluation.public.json) |
| 071–080 | [case-071](data/development-140/case-071/evaluation.public.json) | [case-080](data/development-140/case-080/evaluation.public.json) |
| 081–090 | [case-081](data/development-140/case-081/evaluation.public.json) | [case-090](data/development-140/case-090/evaluation.public.json) |
| 091–100 | [case-091](data/development-140/case-091/evaluation.public.json) | [case-100](data/development-140/case-100/evaluation.public.json) |
| 101–110 | [case-101](data/development-140/case-101/evaluation.public.json) | [case-110](data/development-140/case-110/evaluation.public.json) |
| 111–120 | [case-111](data/development-140/case-111/evaluation.public.json) | [case-120](data/development-140/case-120/evaluation.public.json) |
| 121–130 | [case-121](data/development-140/case-121/evaluation.public.json) | [case-130](data/development-140/case-130/evaluation.public.json) |
| 131–140 | [case-131](data/development-140/case-131/evaluation.public.json) | [case-140](data/development-140/case-140/evaluation.public.json) |
| 141–150 | [case-141](data/development-140/case-141/evaluation.public.json) | [case-150](data/development-140/case-150/evaluation.public.json) |
| 151–160 | [case-151](data/development-140/case-151/evaluation.public.json) | [case-160](data/development-140/case-160/evaluation.public.json) |
| 161–170 | [case-161](data/development-140/case-161/evaluation.public.json) | [case-170](data/development-140/case-170/evaluation.public.json) |
| 171–180 | [case-171](data/development-140/case-171/evaluation.public.json) | [case-180](data/development-140/case-180/evaluation.public.json) |

The [full index](data/development-140/index.json) lists all cases. Only factual sources, resume text, original dimension ratings and brief comments are published; detailed review bases remain private.

## Important qualifications

- Case 007: English wording may imply an unestablished printing action; the needs_review label remains.
- Case 101: an unresolved eligibility question was flagged, not a proven false eligibility claim. The needs_review label is disputed and remains unchanged.
- Case 103: English wording adds an unsupported approval-authority inference; the negative comment remains.
- Case 119: a date may be read as applying to undated work; the temporal ambiguity remains.
- Case 166: Chinese wording leaves tree relocation versus removal ambiguous; the needs_review label and brief criticism remain.
- Pass-labelled examples can still need improvement: case 073 has an unclear subject transition and case 078 has a mismatched application heading.

No resume was repaired or regenerated for publication. Overall scores remain null, and unassessed dimension ratings are not converted to zero. Brief comments summarize actual ratings or specific reader-facing findings without publishing the detailed basis. No quality improvement, hiring likelihood, HR calibration, production readiness or rendered-document quality is established.

This release is fixed at case 180; later authorized development is separate. Current-tree removal of declined material does not erase earlier Git history.
