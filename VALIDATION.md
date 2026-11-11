# Validation · 验收记录

Version 0.2.0-v9.3-windows-test. Windows trial candidate for maintainer publication.

| Check | Result |
| --- | --- |
| Chinese Word layout | The Chinese Word path uses compatibility mode 15. Two long fictional Chinese previews aligned the starts of equal-width labels and colons with zero measured drift. A previously saved PDF with real drift still triggers one blocking finding. Repeated copies of an identical finding are reported once. |
| Offline regression | The packaged runtime passed 212 tests on Windows and 212 on WSL, including the education policy suite. The file-evidence regression passed 22 applicable Windows tests, with three privilege-dependent symlink tests and one POSIX-only test skipped. WSL passed all four applicable file-evidence tests. |
| Installation and first use | A local Git checkout and the bundled installer were tested against the final archives and manifest. The native Windows path exercised prepare, response binding, Word/PDF preview and saved-run audit in both languages. Tampered bindings, invalid responses and the missing-font path were exercised. |
| Long-source previews | The four long fictional drafts and both bundled drafts produced one-page Word/PDF previews and passed file and page integrity checks. The new Chinese pages were visually inspected. The six complete-review requests and sources matched their prior versions byte for byte. |
| Review and layout gates | The complete-review contract and strict greater-than-half tail threshold stay the same. Short last lines and pending visual evidence still block delivery. One of the four long fictional drafts has no completed source review. All trial previews remain pending final acceptance. |

The Windows check used existing desktop Word, Python and licensed fonts. WSL was used for offline regression. Public GitHub download, live agent discovery, clean-machine setup, macOS and live use on real application materials remain separate checks. The local file-evidence tests cover the exercised per-file behavior.

v9.3 修复 Word 渲染中的中文等长标签与冒号漂移，并合并完全相同的对齐警报。真实短末行、加粗证据和视觉审核仍按原门禁处理。推送后请核验真实地址下载及宿主发现。
