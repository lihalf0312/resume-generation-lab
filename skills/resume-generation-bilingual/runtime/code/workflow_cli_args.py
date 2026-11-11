"""Command arguments load without a renderer or document libraries."""

import argparse
from pathlib import Path

MODES = ("full", "compact_experimental")
COMMANDS = tuple(['prepare','render-receipt','render-saved','batch-replay','revise-reviewed','apply-name-bindings','revise-labels','bind-host-response','render-host-response'])
RENDER_COMMANDS = set(COMMANDS) - {"prepare", "bind-host-response"}


def product_parser():
    a=argparse.ArgumentParser(description="Local bilingual resume workflow.",epilog="Prepare your input / 先准备简历资料: INPUT_GUIDE_ZH.md and INPUT_GUIDE_EN.md beside product.py. This CLI uses structured local files; it is not an upload interface.")
    a.add_argument('command',choices=COMMANDS)
    a.add_argument('--source',type=Path);a.add_argument('--language',choices=['en','zh'])
    a.add_argument('--output',type=Path,required=True);a.add_argument('--mode',choices=MODES,default='full')
    a.add_argument('--observed-at');a.add_argument('--timezone')
    a.add_argument('--receipt',type=Path);a.add_argument('--context',type=Path);a.add_argument('--response',type=Path)
    a.add_argument('--request',type=Path);a.add_argument('--host-declaration',type=Path)
    a.add_argument('--target-role',type=Path);a.add_argument('--presentation',type=Path);a.add_argument('--header-assets',type=Path)
    a.add_argument('--complete-review',type=Path);a.add_argument('--batch',type=Path)
    a.add_argument('--run',type=Path);a.add_argument('--body-patch',type=Path);a.add_argument('--auxiliary-patch',type=Path)
    a.add_argument('--language-bindings',type=Path)
    a.add_argument('--label-proposals',type=Path)
    a.add_argument('--layout-only',action='store_true',help='Explicitly request measured tail-only repair after complete source review; revise-reviewed only.')
    a.add_argument('--origin',choices=['manual_development_fixture','synthetic_fake_new_contract','offline_editor_revision','host_assisted'])
    return a


def audit_parser():
    a=argparse.ArgumentParser(description="Audit a saved local resume run.")
    a.add_argument('--source',type=Path,required=True);a.add_argument('--run',type=Path,required=True)
    a.add_argument('--output',type=Path,required=True)
    for name in ('body','labels','presentation','visual-proof'):a.add_argument('--'+name,type=Path)
    a.add_argument('--complete-review',type=Path)
    a.add_argument('--response-disposition',type=Path)
    a.add_argument('--prepare-response-disposition',action='store_true',help='Save an exact isolation review request; never creates an accepted receipt.')
    return a
