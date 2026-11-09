# English RC4: first trial

Status: alpha preview. English-only, fixed template, model-assisted writing with local Word/PDF rendering.

## Before downloading

Use WSL2/Linux and a host assistant able to read SKILL.md and run local commands. Native Windows Python is not supported by this tested path. You need Python virtual-environment support, LibreOffice Writer, fontconfig, and legally installed Times New Roman regular/bold plus Wingdings. The archive includes no fonts, renderers, API keys, model credits, or automatic host registration.

## Download and verify

Open https://github.com/lihalf0312/resume-generation-lab/releases/tag/v0.1.0-en-alpha.4 and download resume-generation-en-rc4.zip and SHA256SUMS.txt. Do not substitute GitHub's automatically generated Source code ZIP.

Run sha256sum -c SHA256SUMS.txt before extraction. Expected ZIP SHA-256: b2753db5475bf4cd26a8a9a3d27df5b6301e22800d5f025542d7bea11aeb850a.

Extract into a new empty installation directory. Keep the task/output directory separate from it: neither directory may contain the other, including through symlinks.

Follow https://github.com/lihalf0312/resume-generation-lab/blob/v0.1.0-en-alpha.4/docs/english-rc4/README.md for dependency setup and runtime.json. Replace all null paths with your own actual paths. Start with preflight, then init using examples/input.synthetic.json. Do not start with personal material until setup works.

Ask the host assistant to read the installed SKILL.md and linked references. The CLI does not write a resume from raw material by itself. The assistant prepares the draft and source-linked analysis; the CLI then runs first, render, structure and review steps. Inspect the actual PDF and source facts before freeze. Retain failed attempts and respect the recorded recovery limits.

## What has been checked

On 2026-11-09, the existing RC4 archive was extracted into a new directory on the maintainer's WSL2 Ubuntu 22.04 machine. Its SHA-256 and internal manifest matched. All 25 existing regressions passed. Preflight, synthetic-example initialization, and one real LibreOffice render of a deliberately sparse synthetic mechanical fixture passed. The result was one page, with all content words mapped, unchanged style and zero outside-body words; its page image was inspected. One initial fixture analysis used incorrect paragraph IDs and was rejected; the schema was corrected and that failure record was retained. The installation files remained unchanged by the regression/init checks.

The run reused pre-existing pinned Python dependencies, LibreOffice 7.3.7.2 and operator-provided fonts. It was not a clean-OS installation, a dependency-download test, a new independent model-quality evaluation, or a completed final-resume freeze. The mechanical fixture used two bullets and does not test dense content or compression.

## What remains unverified

Native Windows/macOS execution, native Word layout, other renderer/font versions, real ATS ingestion, Chinese output and other host assistants have not been validated by this check. Model involvement in development does not establish compatibility with that model's separate app or another host. Review all facts and phrasing yourself.

## Useful feedback

Report the operating system, host application and model/version if available, Python and LibreOffice versions, exact command/stage, expected result and observed result. Include a redacted error or screenshot when useful. Do not upload API keys, runtime credentials, raw personal resumes/JDs, full work directories or unredacted logs to a public issue.
