# English resume release candidate

This is a self-contained skill and offline document toolkit. Codex or a human selects evidence and writes English; local tools construct and inspect the fixed approved Word/PDF layout. It ships no model API client, original candidate materials, real employer JD or runtime credentials. `examples/input.synthetic.json` is an invented smoke-test input, not a usable person's resume.

## Install

Use a local Python 3.10+ POSIX/Linux environment. Install the skill folder in your assistant's discoverable skills directory, or explicitly ask the assistant to read its SKILL.md. Keep task workdirs elsewhere. Install Python packages from requirements.txt in your own virtual environment (for example, `python3 -m venv .venv` followed by `.venv/bin/python -m pip install -r requirements.txt`). Dependency acquisition may need the user's normal network/install authorization; the runtime itself is offline. Versions are the observed tested set; other versions are unverified.

Install LibreOffice Writer and fontconfig (`fc-match`) using your OS package manager. Obtain licensed Times New Roman regular/bold and Wingdings fonts yourself. Fonts and LibreOffice binaries are not redistributed. Configure fontconfig to resolve these exact installed files; no font fallback is accepted. Python wheels alone do not supply the renderer/fonts. Templates use the supplied assets/blank-english-template.docx; style constructors assert identical styles, numbering and section geometry. Do not replace the template independently of those constructors.

Copy `runtime.example.json` OUTSIDE the skill installation and replace every null with your machine's absolute paths. The workdir is the task's sole output root. Its resolved real directory must be unrelated to the resolved skill installation: equality and containment in either direction are rejected before creating directories or copying input, including symlink aliases. `renderer_library_dirs` is optional for relocatable Linux LibreOffice installs; leave empty for a normal system install. The fontconfig file must reference the licensed fonts and may include your normal system configuration. A minimal file has `<fontconfig><dir>/absolute/font/directory</dir><cachedir>/absolute/writable/cache</cachedir></fontconfig>` (add the usual XML header and fontconfig doctype). Preflight verifies fc-match resolves the declared files and families; missing fonts/renderer/config fail clearly. Preserve full runtime config privately because it contains local paths.

Run `python3 /path/to/resume-generation-en/scripts/runtime.py --config /path/to/runtime.json preflight`. Save and inspect its JSON. It reports the actual environment and font hashes; it is not a cross-platform promise.

## Input and model-assisted work

Provide JSON `{ "synthetic": false, "target_role": "Intended position", "material_text": "Your unmodified source text", "jd_text": "The current job description" }`. Use true only for explicitly synthetic development material. Save a source index and hashes for additional authorized files; extract their content into material_text without erasing original evidence. No input form or example counts as confirmed personal facts. For scoped revisions, preserve the old source/output and restrict edits to the request; the CLI's immutable lifecycle creates another workdir for a later application or changed inputs.

Ask Codex to read SKILL.md and the two linked references, organize facts and questions, select relevant evidence, and author draft-first.json plus analysis-first.json. The draft is `{name, sections:[{heading,items:[{heading,date?,bullets:[text]}]}]}`. The target and synthetic setting are taken from input by delivery tools. Source/analysis schemas and citation requirements are in references/source-and-writing.md. No tool in this package turns raw materials into a semantic resume automatically. In an ordinary Codex session those are model-assisted operations within the current session, without extra paid model API calls by these scripts.

## Run and resume

For each command use `python3 /path/to/skill/scripts/runtime.py --config /path/to/runtime.json` followed by:

1. `init /path/to/input.json`
2. `first /path/to/draft-first.json --analysis /path/to/analysis-first.json`
3. `render` — inspect versions/v00 PDF, images and measurements.
4. `structure`, then `render` — inspect the preserved new version.
5. When justified, author a source-linked decision and run `edit /path/to/decision.json`, then `render`; repeat only as needed, at most four semantic passes.
6. Author a truthful review; run `freeze --review /path/to/self-review.json`.

`status` reports state and a `recovery` object with the actual current-version path, attempt-evidence paths and either the accepted receipt path or render blocker. If rendering fails, inspect the preserved attempt directory, fix the concrete runtime/configuration fault and repeat `render` on that same original DOCX, at most two recoveries after the initial attempt. Configuration correction does not reset the counter. No best-of, reset or alternative generation is provided. A failure before final acceptance leaves editable drafts and diagnostics. Preserve the terminal error privately with an incident record; do not claim an incomplete render succeeded.

Final files are delivery/resume.docx, resume.pdf and resume.txt, with FREEZE.json hashes. Each version keeps its original DOCX/text/content/changes. Every render attempt has a separate immutable `render-attempt-NN/` directory containing copied inputs, obtainable PDF/images/text/measurement/font evidence, `started.json` and a terminal `result.json` with the real renderer returncode/stdout/stderr or exception. Successful acceptance creates `accepted-render.json`, which identifies the actual attempt and hashes its artifacts, measurement and embedded-font evidence plus runtime/configuration/font/template/code identities. Inspect the PDF and images in that accepted attempt directory. A standalone or legacy measurement is diagnostic only; it never authorizes reuse, structure, editing or freeze. input.json, source-linked analyses/decisions, preflight, self-review and state stay outside the resume. Raw receipts may contain local paths; do not publish private workdirs. A final freeze stops editing that workdir. Timing covers monotonic init-to-freeze on one machine, including pauses, and excludes earlier gathering or model work; it is not an API latency benchmark.

## Limits and review

Read references/operations.md for evidence/declaration distinctions and bounded recovery. Supported implementation is English fixed-style one-page employment resumes with plain text content. No photos, arbitrary template interchange, automatic hyperlink creation, academic CV adaptation, translation guarantee or local model is included. Nothing is uploaded or published. Review each actual final page and all factual scope yourself. Requirements cannot be met by shrink-to-fit or invented filler. A validated installation does not validate every resume or another OS/render engine.

`INSTALLATION-VALIDATION.md` records this candidate's observed synthetic clean-install checks and their limits; private paths, raw traces and private install config are deliberately excluded.

## Local invariant checks

Run `python3 /path/to/skill/tests/validate.py` and `python3 /path/to/skill/tests/test_render_acceptance.py` in the installed dependency environment. These cases exercise generic transformations, citation rejection, marker/target rules, source-scope declarations and the Python network guard; they do not replace rendering a real task or source/writing review. See RELEASE-CHECKLIST.md and INSTALLATION-VALIDATION.md for the exact observed release evidence and its limits.

## RC2 scope and provenance additions

Read VERSION-DELTA.md for the reference-schema migration and RC1 preservation. The complete capability matrix is references/capability-coverage.md; independent review fields/status rules are in references/review-status.md. Selection uses fact_ids; questions use affected_fact_ids (possibly empty for new information); claim maps use fact_ids. All declared references must exist. The old affected_facts key fails explicitly. Optional self-review observations use separate defect_confirmed, original_problem_detected, human_judgment_required and speech_act fields. Programmatic shape/reference checks do not certify natural-language meaning or complete annotation.

## RC3 date-field edits

RC3 date-edit behavior is retained in RC4; predecessor archives and evidence remain distinct. On an entry row, a source-linked replace operation may use after_date to correct the date while preserving text, or combine after_date with after. The exact before includes the old displayed date. String types, entry-row/action constraints, literal material evidence and full before/after row logs are enforced. The editor still verifies the replacement date against actual source meaning; the tool never infers a year from the JD. VERSION-DELTA.md records the complete delta chain.

RC3 freeze also verifies synthetic-marker and Target intent invariants after all semantic edits, so removal/mutation of those rows cannot silently pass a one-page check. Marker/Target acceptance is a delivery check against declared input, separate from truth of personal claims.

## RC4 acceptance and incomplete recovery

Only an accepted receipt with matching hashes and identities permits progression. Measurement must complete with successful token mapping and style checks, and all actual PDF font programs must be embedded and use the expected families. An accepted render may still overflow: one-page/body-bound and editorial acceptance remain separate freeze checks. Cached reuse validates the receipt and performs no conversion. Changed inputs, artifacts, runtime configuration, fonts or mechanics invalidate reuse; restore the exact accepted artifacts/configuration rather than relabeling them. Legacy measured files are never upgraded silently; any remaining bounded attempt must actually render and validate.

Use `status` after a failure or rejected freeze. Follow the actual `recovery.attempt_evidence` entries to `result.json`; follow `recovery.accepted_render` to its `attempt_directory` for actual measurements/images. The editable DOCX and content are under the reported `recovery.version` directory. Keep diagnostics and first-draft history. After overflow, use structure once if still available, then only the remaining source-linked semantic passes (four total), rendering each new version. At the four-pass cap, an overflowing/out-of-bounds or otherwise unaccepted version remains **incomplete**: retain its DOCX/PDF, errors, status and unresolved issues; no extra edit, counter reset, restart or forced freeze is provided. At three failed render attempts, retain the incomplete same-version draft and receipts; further rendering is blocked. A new application or new authorized source task is separate work, never a retry-limit bypass. No native Microsoft Word pagination or semantic quality is established by these mechanisms.
