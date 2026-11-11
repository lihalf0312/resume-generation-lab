# First Windows trial · Windows 首次试用

These steps use 0.2.0-v9.3-windows-test. Start with the included fictional case. It has a JD, education, project and work history, a matched target binding, and a hand-written response for each language. It exercises a full page without paid model calls. Its facts are invented for testing.

For your own private run, prepare the original JD and the target role, desired language, confirmed employer and project names, dates, your own contribution, and the scope of any results. Tell the agent which facts are uncertain or should be omitted. Keep your materials, names and documents in a separate task folder. The agent creates the local input files and asks about material gaps.

## Run the fictional case

Continue after [installation](INSTALL.md) with $Python and the printed $Skill path. In a fresh PowerShell session, set those two values again. The trial checks the current prerequisites before attempting preview. Set $TrialRoot to an unused, writable path separate from the skill and the repository. Run the two languages in distinct folders. If doctor reports a missing renderer dependency, you can run prepare and bind but should stop before preview.

~~~powershell
$TrialRoot = '<unused short local path>'
$Native = Join-Path $Skill 'runtime/native.py'
& $Python -B -X utf8 $Native doctor
$DoctorExit = $LASTEXITCODE
if ($DoctorExit -notin 0,2) { throw "The prerequisite check failed. Exit $DoctorExit." }
$CanRender = ($DoctorExit -eq 0)
$Fixture = Join-Path $Skill 'examples/full-fictional'
New-Item -ItemType Directory -Path $TrialRoot -ErrorAction Stop | Out-Null
function Invoke-ResumeTrial {
    & $Python -B -X utf8 $Native @args
    if ($LASTEXITCODE -ne 0) { throw "Local resume command failed. Exit $LASTEXITCODE." }
}
$Source = Join-Path $Fixture 'source.json'
foreach ($Language in 'en','zh') {
    $Run = Join-Path $TrialRoot $Language
    $Prepared = Join-Path $Run 'prepared'
    $Bound = Join-Path $Run 'bound'
    $Preview = Join-Path $Run 'preview'
    $Response = Join-Path $Fixture "$Language/response.txt"
    $Target = Join-Path $Fixture "$Language/target.json"
    Invoke-ResumeTrial product prepare --source $Source --language $Language --output $Prepared
    Invoke-ResumeTrial product bind-host-response --source $Source --language $Language --request (Join-Path $Prepared 'REQUEST.json') --response $Response --output $Bound
    if (-not $CanRender) {
        Write-Output "Prepared and bound the $Language text. Preview is paused until doctor passes."
        continue
    }
    Invoke-ResumeTrial product render-host-response --source $Source --language $Language --request (Join-Path $Bound 'REQUEST.json') --response (Join-Path $Bound 'RESPONSE.txt') --host-declaration (Join-Path $Bound 'HOST-DECLARATION.json') --target-role $Target --output $Preview
    $Result = Get-Content -LiteralPath (Join-Path $Preview 'RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Result.preview_error -or -not $Result.pdf -or -not (Test-Path -LiteralPath $Result.pdf -PathType Leaf)) {
        throw ('Preview unavailable. See RESULT.json in the local task folder. ' + $Result.preview_error)
    }
    $Docx = Join-Path $Preview 'deliverable/preview/round-00/render/resume.docx'
    if (-not (Test-Path -LiteralPath $Docx -PathType Leaf)) { throw "The $Language Word preview is missing." }
    $AuditPath = Join-Path $Run 'AUDIT.json'
    Invoke-ResumeTrial audit --source $Source --run (Join-Path $Preview 'deliverable') --output $AuditPath
    $Audit = Get-Content -LiteralPath $AuditPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Audit.status -ne 'needs_review' -or $Audit.final_acceptance -ne $false -or
        $Audit.mechanical_integrity_passed -ne $true -or $Audit.fresh_page_count -ne 1) {
        throw "The $Language preview did not pass the fictional trial's file and page checks. Inspect AUDIT.json locally."
    }
    Write-Output "Verified the $Language one-page preview. Source and visual review remain pending."
}
~~~

On success, each language has a PDF at the path in RESULT.json and the matching DOCX under preview/deliverable/preview/round-00/render/resume.docx. Open each page and check content against the source, right-aligned dates, bold labels, punctuation, fonts, clipping and wrapped last lines. Read the stage status and the audit findings. A successful command can still produce a pending draft. The fictional sample should produce needs_review with final_acceptance false because full source and visual review were intentionally left pending. For a graduate, use source-supported study dates and follow any explicit date requirement for the application. The display default does not establish a personal fact.

For your own inputs, let the agent read the exact prepared request and write a fresh response. Follow the installed [host workflow](skills/resume-generation-bilingual/runtime/HOST_FIRST_RUN.md). Skip the example if you cannot access its output files. Treat any text-only draft as text.

## Send privacy-safe feedback

Report the skill version, Windows version, selected language, failed step, and the shortest redacted error or finding code. Tell us what you expected and what you observed. Mention whether the issue also appears with the included fictional case. Use a fictional example or a cropped redacted screenshot to demonstrate a formatting issue.

Keep personal source files, generated resumes, raw requests, responses and audit logs out of public feedback. They can contain names, work history and local paths even when the problem is only layout.

中文简要步骤：先用虚构样例分别生成中英文预览，查看 Word、PDF 和审计状态。反馈只需版本、语种、失败步骤、脱敏错误和是否能用虚构样例复现。个人履历、原始素材及整份日志留在本地。
