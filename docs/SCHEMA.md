# Core record contract

JSONL; one validated object per line. All records require:

| Field | Contract |
|---|---|
| id | corpus-unique nonempty string |
| kind | `profile` or `job` |
| source_family | variants share original provenance family, not file URL variant |
| synthetic | explicit boolean; false for actual people or jobs |
| publication | `public`, `private`, or `review_required` |
| provenance | `source`, `retrieved_at`, `license`, `method`; nonempty strings; optional attribution |
| skills | list of strings; exact-string diagnostic requires normalization for useful interpretation |

Profiles additionally require `name`, `profile_group` (same identity across versions), and `facts` (verbatim strings). Jobs require `title`. All profile identities linked by shared source-family are one split component. Job source families are one split group. This conservative approach may reduce usable pair count. Any newly discovered cross-family duplicate requires a new dataset version and split audit; hashing cannot detect semantic duplicates.

Source permissions are metadata assertions, not independent legal verification. Synthetic profiles based on a source must not imply achievements belong to a real person. Publication flags do not authorize publication without the release gate and human review.

# Failure/recovery

One writer per experiment. If a process dies, inspect the JSONL and lock before manually removing `.writer.lock`. Do not edit historical events or reuse its experiment directory with different data. A partial last line stops run recovery: retain the original ledger for forensics and create a reviewed new experiment rather than secretly truncating history. Checkpoints are disposable derivatives; ledger is authoritative. Freeze splits before evaluation/optimization. A corpus revision invalidates the frozen manifest, by design.

Checkpoint hashes anchor ledger history through the most recent checkpoint. Deletion after that checkpoint is not detectable without an external immutable anchor; the local hash chain is tamper-evident only to its available anchors, not authentication.
