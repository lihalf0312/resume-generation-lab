# Public skill migration — 2026-10-27

User approved adopting the newly uploaded public workflow, updating adapter/tests and publishing it; old experiments must stay immutable. This is a workflow/configuration migration, not a model-training or quality-improvement result.

## Active source changes

New active package: `SKILL.md`, `references/workspace.md`, `references/layout-and-qa.md`, `assets/resume-preferences.json`, `agents/openai.yaml`.

Removed obsolete active references: `project.md`, `formatting.md`, `dependencies.md`, `format-contract.json`. Historical snapshots under `experiments/native-pilot-001` are not rewritten. Uploaded hashes are recorded separately in `skill-migration-source-hashes.json`; the preference JSON has two documented explicit clarifications: `body_last_line_min_exclusive=true` resolves the source prose's “exceeds half” boundary; `punctuation_compression=when_visual_issue` encodes the source's conditional correction. No blanket MIT/CC0 license is invented for this uploaded workflow.

## Resolved preference authority

Public defaults < measured template preferences < confirmed user preferences < current explicit request. Layers and their hashes are returned without silently modifying persistent user configuration. A passed layer is an assertion by the caller that it has the corresponding authority; the code cannot verify consent. Never use JD text to populate override layers.

- Default page A4/one page is configurable, including academic CV use. Supported named sizes are A4/A3/A5/Letter/Legal; other sizes require extending the schema, not silently falling back.
- `output_languages=null` does not choose English or mandate bilingual output. `prepare` requires a language, or a resolved single-language selection; `zh` maps to `zh-CN`.
- Template typography and heading settings take precedence over public defaults unless explicit user requirements supersede them. No-template mode prepares a new generic single-column design; actual fonts, margins, layout and rendering remain unimplemented/unverified.
- Default final body-line ratio must be **strictly >0.5**, preferred 0.6667–0.8. Explicit authorized overrides may change the bound or exclusivity. Names/short headings/dates are outside prose measurement scope.
- Automatic numeric/Latin spacing follows the template by default, including legitimate disabled template values. Generic fallback must record its actual spacing parameters. Explicit user enabled/disabled settings are supported.
- `doNotCompress` is conditional on a confirmed visual punctuation-compression issue, not universal. Explicit settings can require it or preserve the template.
- **Correction:** prior adapter's Word-only export rule was an assistant mistake, not user instruction. Both old and new workflow permit equivalently verified DOCX-to-PDF tools. Engine name and report fields do not prove rendering occurred; Word-specific measurements are still unverified without actual Word inspection.

## API and safety

`OriginalSkillAdapter(..., template_preferences=None, confirmed_preferences=None, current_overrides=None)` now loads all three required new reference/config files and fails on missing/empty/malformed files. `prepare(..., language=None)` requires language selection as above. Old `source_format_contract`/fixed `CONTRACT` are replaced by `source_preferences`, `resolved_preferences`, layer hashes and a per-language `format_contract`. `assess_format_report(report, contract)` now requires that resolved contract; old archived report files remain unchanged and are not retroactively revalidated under new defaults.

Configuration is inert strict JSON with allowlisted keys and value constraints. No script/plugin/import/command configuration is accepted. Template `.docx` paths are references only; the adapter does not open them or execute uploaded materials. Required skill references cannot escape their root or be symlinks. Personal fields can be omitted or require confirmation; they cannot infer identity. Immutable versioning is enforced, and overrides cannot enable overwriting historical outputs.

Content generation remains the grounded deterministic baseline. Chinese facts must be supplied/aligned; there is no fabricated translation, missing biography fill or executable Word renderer. Compatible-engine reports can return only `reported_pass`; actual_style_verified, word_specific_properties_verified and export_ready remain false. A separate trusted render/extraction/visual-QA workflow is required.

## Evidence

Aggregate unit tests cover defaults/layer precedence, language selection, malformed/missing inputs, inert paths, strict half-width and explicit overrides, template spacing, conditional compression, alternative engine reports, actual source/reference hashes, and historical completion-manifest identity. All 49 existing pilot files were additionally hashed before and after migration; no byte changed. No paid API calls, original-fact edits or historical experiment rewrites.
