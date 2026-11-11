# Local workflow · 本地工作流

Follow the current [host first-run guide](../runtime/HOST_FIRST_RUN.md) for prepare, host response binding, preview and saved-run audit. See the [Chinese](../runtime/INPUT_GUIDE_ZH.md) and [English](../runtime/INPUT_GUIDE_EN.md) input guides. Start from authorized, private task materials and run the two languages separately when both are requested.

The host assistant authors the response under its existing permissions. Save the exact raw response as UTF-8, then bind it. Keep invalid input intact and retain questions that affect material facts. Use a new output folder and never synthesize a provider or review receipt. Text readiness means required user input is no longer outstanding. Source review, rendering and visual review remain separate.

The host-assisted real-resume route sets user_resume in trusted code. Any developer creating synthetic review payloads through the Python API must pass document_kind="synthetic_development" explicitly from trusted configuration. Never infer the kind from source text, model notes or a case identifier. Changing the kind changes the review binding. Run a fresh complete review on each new candidate.

Review all visible material and each rendered page before presenting a final deliverable. A preview, render or pending audit is useful as progress and remains distinct from final acceptance.
