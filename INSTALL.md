# Install from the repository URL · 从仓库地址安装

Give the agent the root repository clone URL and the test branch or tag from the maintainer. For a GitHub page ending in /tree/… or /blob/…, use the root clone URL and obtain the exact ref separately. If the maintainer also gives a full commit SHA, check that the selected ref resolves to it. Use a desktop agent that can read and write local files and run commands.

## Resolve, verify and install

The PowerShell example below uses a fresh local skill directory for the first trial. That installation supports the trial commands. Agent discovery is checked separately. For a live install, use the current agent's supported skill location and preserve any existing version. Keep both the checkout and the skill path short on Windows. Avoid folders shared with unrelated processes.

Set the input variables at the top of the example. $Python is a path to an existing Python 3.10+ executable. When Windows provides Python through the py launcher, run py -3 -c "import sys; print(sys.executable)" and use the path it prints. The default branch is used when $TrialRef is empty. Set $ExpectedCommit when the maintainer supplied a full SHA.

~~~powershell
$RepoUrl = '<root repository clone URL>'
$TrialRef = ''
$ExpectedCommit = ''
$TrialBase = '<new short local directory>'
$Python = '<full path to Python 3.10 or newer>'
$Checkout = Join-Path $TrialBase 'checkout'
$SkillsRoot = Join-Path $TrialBase 'skills'
if ($RepoUrl -match '^https?://github\.com/[^/]+/[^/]+/(tree|blob)/') { throw 'Use the root clone URL and set the exact test branch or tag separately.' }
if ($ExpectedCommit -and $ExpectedCommit -notmatch '^[0-9a-f]{40}$') { throw 'Use a full 40-character commit SHA.' }
& $Python -B -X utf8 -c "import sys; print(sys.version.split()[0]); sys.exit(sys.version_info < (3,10))"
if ($LASTEXITCODE -ne 0) { throw 'A working Python 3.10+ interpreter is required.' }
New-Item -ItemType Directory -Path $TrialBase -ErrorAction Stop | Out-Null
$GitArgs = @('-c', 'core.longpaths=true', 'clone')
if ($TrialRef) { $GitArgs += "--branch=$TrialRef" }
git @GitArgs -- $RepoUrl $Checkout
if ($LASTEXITCODE -ne 0) { throw 'Repository checkout failed.' }
if ($ExpectedCommit -and -not $TrialRef) {
    git -C $Checkout checkout --detach $ExpectedCommit
    if ($LASTEXITCODE -ne 0) { throw 'The requested commit is unavailable in the checkout.' }
}
$Commit = git -C $Checkout rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $Commit -notmatch '^[0-9a-f]{40}$') { throw 'Could not identify the checked-out commit.' }
if ($ExpectedCommit -and $ExpectedCommit -ine $Commit) { throw 'The selected ref does not match the requested commit.' }

function Get-CheckoutFile($RelativePath) {
    $Entry = git -C $Checkout ls-tree $Commit -- $RelativePath
    if ($LASTEXITCODE -ne 0 -or $Entry -notmatch '^100(644|755) blob [0-9a-f]{40}\t') { throw "Expected a regular file in the selected commit. $RelativePath" }
    $Item = Get-Item -LiteralPath (Join-Path $Checkout $RelativePath) -ErrorAction Stop
    if ($Item.PSIsContainer -or ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Expected a regular checkout file. $RelativePath" }
    $Item.FullName
}

$Manifest = Get-Content -LiteralPath (Get-CheckoutFile 'install-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Manifest.schema -ne 'agent-skill-install-manifest-v1' -or $Manifest.version -ne '0.2.0-v9.3-windows-test' -or $Manifest.skill_path -ne 'skills/resume-generation-bilingual') { throw 'This is not the requested bilingual v9.3 test snapshot.' }
if ($Manifest.archive_path -ne 'resume-generation-bilingual-0.2.0-v9.3-windows-test.zip' -or $Manifest.installer_path -ne 'scripts/install_local.py') { throw 'Unexpected archive or installer path in the manifest.' }
$Archive = Get-CheckoutFile $Manifest.archive_path
$Installer = Get-CheckoutFile $Manifest.installer_path
if ((Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash -ine $Manifest.archive_sha256) { throw 'Skill ZIP SHA-256 mismatch.' }
if ((Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash -ine $Manifest.installer_sha256) { throw 'Installer SHA-256 mismatch.' }
$InstallJson = & $Python -B -X utf8 $Installer --archive $Archive --sha256 $Manifest.archive_sha256 --skills-dir $SkillsRoot
if ($LASTEXITCODE -ne 0) { throw ($InstallJson -join [Environment]::NewLine) }
$Install = ($InstallJson -join [Environment]::NewLine) | ConvertFrom-Json
if (-not $Install.installed -or $Install.file_count -ne $Manifest.file_count) { throw 'Installation was not verified.' }
$Skill = $Install.destination
$Native = Join-Path $Skill 'runtime/native.py'
Write-Output "Installed from $Commit at $Skill"
~~~

Inspect the installer and relevant runtime source from the selected commit before execution. Hash checks compare the downloaded files with the manifest from that commit. Use a maintainer-trusted source for the commit and manifest. If Git is unavailable, obtain the exact commit archive and confirmed hashes from the maintainer, then verify its files before following the local installer and [trial steps](TRIAL.md).

The installer preserves existing versions and supports --verify-only. Read the installed SKILL.md. For Codex or another agent, use that host's supported skill directory when you want the skill to appear in its catalog. The first trial can use the fresh directory from this example. Continue with the [first trial](TRIAL.md), which runs the prerequisite check in its own session.

## If a prerequisite is missing

| Missing | What you can still do |
| --- | --- |
| Python 3.10+ | Collect the JD and confirmed facts. Ask your agent to produce a text draft for review. Local file checks and Word export require Python. |
| Desktop Microsoft Word | Use the text draft and, if Python works, prepare and bind the response. Resume Word and PDF preview after the doctor passes. |
| Required font | Point RESUME_FONT_DIR at a readable folder with the exact legally available font files, or continue with text. The Windows preview uses Times New Roman, its bold face, KaiTi and Wingdings. |
| Python packages | Use the same interpreter for doctor and the workflow. The doctor lists missing packages. Ask before using requirements-native.txt in an isolated environment. Text preparation and binding can be used without the rendering libraries. |

The validated Windows route uses desktop Word. The runtime does not automatically install software, switch renderers, substitute fonts or change system settings. Report actual document paths only when they exist. Keep dependency diagnostics private.

中文简要步骤：先从仓库根地址定位试用分支或标签，再核对提交、安装器和技能 ZIP 的哈希。可先在短临时目录试用，之后再按当前宿主的支持路径验证发现。缺少 Python 时可先做文本稿。缺少 Word、字体或渲染依赖时，试用流程会停在文本准备和绑定。
