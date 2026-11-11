# Windows test runtime · Windows 测试运行时

Start with native.py --help and native.py doctor. The product command prepares a source-bound request, binds a saved host response, and receives it as a preview. The audit command reports pending gates from a saved run. See [host first run](HOST_FIRST_RUN.md), [Chinese input guide](INPUT_GUIDE_ZH.md) and [English input guide](INPUT_GUIDE_EN.md). Required Python packages are in requirements-native.txt. The Word backend, system fonts and Python packages are installed separately with user authorization.

Local tasks use a new output directory per run. Keep real source files, responses and generated documents outside the installed skill and repository. Never interpret a successful process exit, an input binding, a ready text response or a rendered page as final approval.
