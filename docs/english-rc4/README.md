# English RC4 alpha preview

This is an **English-only, fixed-template, model-assisted resume toolkit**.
It is a preview, not a stable product. A host assistant or editor selects evidence,
writes and reviews; local Python tools create and inspect Word/PDF files. Users
must verify the final facts, job fit and expression themselves.

## Source directory versus installable archive

- [Source skill](../../skills/resume-generation-en/SKILL.md): the unchanged RC4
  implementation, references, blank template, scripts and synthetic example.
- [Approved installation ZIP](../../releases/english-rc4/resume-generation-en-rc4.zip)
  and [archive SHA-256](../../releases/english-rc4/SHA256SUMS.txt).
- [Post-test validation annex](RC4_VALIDATION_SUMMARY.md) records completed RC4
  acceptance and its gaps. Installation documents inside the frozen skill retain
  their historical context; the annex does not change the implementation.

The ZIP SHA-256 is
`b2753db5475bf4cd26a8a9a3d27df5b6301e22800d5f025542d7bea11aeb850a`.
GitHub's automatically generated repository source ZIP is **not** this installable
archive. The [published RC4 prerelease](https://github.com/lihalf0312/resume-generation-lab/releases/tag/v0.1.0-en-alpha.4)
contains this ZIP and its checksum file as release assets. Download those two
attachments, not the automatically generated Source code archives.

Start with the [first-trial guide](FIRST_TRIAL.md) for environment requirements,
the trial sequence, the 2026-11-09 verification scope and safe feedback guidance.
The installation ZIP and implementation remain unchanged.

## Install on the observed WSL2/Linux environment

Download both files into the same directory, then verify before extracting:

```sh
sha256sum -c SHA256SUMS.txt
INSTALL_ROOT="$HOME/.local/share/resume-generation-en-rc4"
mkdir -p "$INSTALL_ROOT"
unzip resume-generation-en-rc4.zip -d "$INSTALL_ROOT"
SKILL_DIR="$INSTALL_ROOT/resume-generation-en"
TASK_ROOT="$HOME/.local/state/resume-generation-rc4-example"
mkdir -p "$TASK_ROOT"
python3 -m venv "$TASK_ROOT/.venv"
"$TASK_ROOT/.venv/bin/python" -m pip install -r "$SKILL_DIR/requirements.txt"
cp "$SKILL_DIR/runtime.example.json" "$TASK_ROOT/runtime.json"
cp "$SKILL_DIR/examples/input.synthetic.json" "$TASK_ROOT/input.json"
```

Use a new empty install directory; do not overwrite an existing installation.
These are example user-local paths, not project-specific private locations.
The installed skill entry point is
`~/.local/share/resume-generation-en-rc4/resume-generation-en/SKILL.md`.
Ask your host assistant to read that file and its linked resources explicitly,
or use the host's documented skill-discovery mechanism. No automatic host
registration is performed by extraction.

Install LibreOffice Writer, fontconfig (`fc-match`) and the Python virtual-environment
support using your Linux distribution's normal installation process. Obtain and
license Times New Roman regular/bold and Wingdings yourself. **Fonts, renderers and
dependency binaries are not included.** The exact observed Python packages are
pinned in requirements.txt; their installation can require network access.

Edit runtime.json privately: replace nulls with real absolute renderer, fontconfig
and font-file paths; set workdir to a separate task output directory, for example
TASK_ROOT/output. The resolved workdir must neither contain nor be contained by
the installed skill, and cannot equal it, including through symlinks. Do not use
an output directory inside the installed package. Configure fontconfig to resolve
the declared fonts exactly; missing/substituted fonts fail instead of silently
switching. For a normal system LibreOffice keep renderer_library_dirs empty;
relocated installations require their program library directory before support
library directories. See the [configuration instructions](../../skills/resume-generation-en/README.md).

```sh
"$TASK_ROOT/.venv/bin/python" "$SKILL_DIR/scripts/runtime.py" --config "$TASK_ROOT/runtime.json" preflight
"$TASK_ROOT/.venv/bin/python" "$SKILL_DIR/scripts/runtime.py" --config "$TASK_ROOT/runtime.json" init "$TASK_ROOT/input.json"
```

For real work, replace the invented example with your own unmodified material_text
and current jd_text; set synthetic to false. The supplied example remains explicitly
synthetic and sparse. It is an installation example, not evidence of dense-resume
writing quality. Keep personal inputs and all task workdirs private.

## Generate, inspect, recover

Follow the [full workflow and schemas](../../skills/resume-generation-en/README.md):
the assistant organizes sources/questions, selects evidence, authors first draft
and analysis, and uses first, render, structure, justified source-linked edit and
freeze. The CLI itself does not perform semantic generation. Review actual pages
and extracted text as well as source meaning. Do not invent facts to satisfy a JD.
Unanswered material conflicts may remain outside a safe provisional draft.

Inspect status after failure. A render is usable only with a valid accepted-render
receipt; measurement alone is not enough. Each version allows an initial render
and at most two recoveries, preserving every attempt. Semantic editing is capped
at four passes. Configuration corrections do not reset counters. An oversized or
otherwise unaccepted document cannot become a final delivery; retain incomplete
artifacts and diagnostics rather than deleting state or forcing freeze. A successful
freeze produces delivery/resume.docx, resume.pdf and resume.txt plus hashes.

## Validation and known limits

Observed only: WSL2/Linux, Python 3.10.12, LibreOffice 7.3.7.2 and the recorded pinned
Python dependencies with operator-supplied licensed fonts. This was a fresh-directory
run with pre-existing dependencies, not a clean-OS installation. Native Microsoft
Word, other operating systems, cross-renderer pagination, real ATS ingestion and
Chinese output have **not** been validated. Same-engine extraction agreement is
not cross-software compatibility.

The RC4 regressions and oversized-fixture rejection passed. In one new-context
writing trajectory, actual pages were 2 / 2 / 1 / 1; final source review found no
confirmed personal factual defect in that one sample. Shared filesystem access
was not OS-isolated. **Identified-only need / unimplemented-proposal preservation
through compression remains untested:** the source items were reasonably omitted
throughout. A short remaining tail line, readable date wrap and generic exhausted
status wording remain limitations/preferences. Fixture rejection is software evidence,
not a model quality score. There is no automatic guarantee of every factual rule,
zero hallucinations, HR gold-standard quality or model-weight training.

No API keys, model credits or hosted inference service are supplied. Host-model
usage and local execution still depend on your subscription, limits and permissions.
The scripts' lack of extra billed model API calls does not make host inference
unlimited or free. Private tests, real JD text, author ledgers, scoring answers,
budget ledgers and raw execution traces are not part of this publication.
