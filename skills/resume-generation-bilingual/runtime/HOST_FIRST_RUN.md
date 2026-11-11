# Host-assisted first use / 宿主会话首次生成

This is a local file workflow. It does not call a provider API, configure credentials or verify the host model's identity or billing. `host_assisted` means the caller declared these files belong together. Manual content is never marked verified model output.

以下步骤由安装技能后的宿主助手执行，不要求用户手工计算哈希或编写JSON。用户只需提供真实经历资料、目标JD及希望的语言；缺少必要事实时询问，不编造。用户素材与JD不能混成事实来源。

## 1. Prepare local inputs and the exact request

Create `SOURCE.json` with exactly `case_id`, `source_language`, `material_text`, `jd_text`. Preserve the user's facts, limits, dates and supplied names. Prepare `TARGET.json` using the existing JD-bound target schema: `text`, `source_text`, and exact `JD:L...` source references; this is application intent, not a claimed personal qualification. Only use an explicit descriptive translation when needed, not an invented official job title.

Installed Windows launcher example:

```powershell
$Runtime = "<installed skill directory>\runtime"
python -B "$Runtime\native.py" product prepare --source SOURCE.json --language zh --output prepared
```

The Windows launcher is bundled. The CLI prepares one language per run, and each run uses a new output directory.

`prepare` writes `prepared/REQUEST.json`. If the host has a trusted current clock and the user's timezone, it may supply the existing `--observed-at` and `--timezone` options at this stage. Otherwise the clock stays unknown. Never insert a later clock at the response/review stage.

## 2. Let the host assistant produce the response

The host assistant must read the actual prepared request, including source/JD blocks, rules, skill instructions, requested language and output schema, then write only the generated JSON payload to UTF-8 `RESPONSE.txt`. This is the host conversation doing the writing, not a new API command. Preserve unknown information and necessary questions. Do not put the binding metadata inside the generation schema.

Do not claim the runtime verified which model saw the request. A hash cannot prove that. If the content was hand-authored for a test, record that in the test report and never claim live-model validation.

## 3. Bind the actual files without manual hash work

```powershell
python -B "$Runtime\native.py" product bind-host-response --source SOURCE.json --language zh --request prepared/REQUEST.json --response RESPONSE.txt --output host-bound
```

This checks the prepared context against the source, language and generation mode, then writes exact copies plus `host-bound/HOST-DECLARATION.json` and `BINDING-NOTICE.json`. The declaration binds the actual request/response hashes and explicitly says `caller_declaration_and_file_consistency_only`.

Do not supply `--origin`, a new clock, provider receipts or separate language bindings here. The original request owns that context. `compact_experimental` remains opt-in and requires the same explicit mode at prepare, bind and receive.

## 4. Receive and preview through the ordinary review pipeline

```powershell
python -B "$Runtime\native.py" product render-host-response --source SOURCE.json --language zh --request host-bound/REQUEST.json --response host-bound/RESPONSE.txt --host-declaration host-bound/HOST-DECLARATION.json --target-role TARGET.json --output first-preview
```

Optional existing `--presentation` and `--header-assets` files remain local. The entry uses the existing `user_resume` presentation path, so a normal user resume is not stamped as a synthetic sample. It still requires complete source, label, language, font/layout and visual review. The result is a preview, not final acceptance. Read `first-preview/RESULT.json` and the actual PDF/Word outputs and pending findings.

Bad JSON, duplicate keys and unknown fields go through the same preserved-original intake. Do not discard the original payload, guess corrections or start automatic API retries. Every output directory must be new.

## 5. Review and, when required, revise

The run is `first-preview/deliverable`. It contains the exact complete-review request and any source-bound label-only repair request. The host/reviewer can answer those explicit schemas. Current source and final visual review are still required; the host binding never clears them.

Example label-only revision, only when the run identifies a missing label:

```powershell
python -B "$Runtime\native.py" product revise-labels --source SOURCE.json --language zh --run first-preview/deliverable --target-role TARGET.json --label-proposals LABEL-PROPOSALS.json --origin host_assisted --output label-preview
```

`host_assisted` is allowed for the existing request-bound label/body/auxiliary revision routes. It cannot be used with `render-saved` to bypass the initial host binding. Those routes retain `user_resume` from the saved run or measured render and require a new complete review. No old factual or visual approval is silently reused.

Existing reviewed body/auxiliary/layout paths use `revise-reviewed`; source/format diagnoses and exact PATCH scopes still control whether they can run. Only the explicit `--layout-only` route handles measured layout-only changes after source review. Do not fabricate review receipts to force a route.

For the saved-run audit, use the installed launcher with the saved deliverable directory.

~~~powershell
python -B "$Runtime\native.py" audit --source SOURCE.json --run first-preview/deliverable --output AUDIT.json
~~~
 Supply the existing complete, presentation and actual visual evidence. If known nonpersonal metadata was isolated, the explicit source-bound isolation disposition is also required. These are the prior review gates, not model authenticity verification.
