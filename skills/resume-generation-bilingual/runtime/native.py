"""Native local entry. Run: python native.py doctor | product <arguments> | audit <arguments>."""
from pathlib import Path
import json, subprocess, sys
sys.dont_write_bytecode = True
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT/'code'),
                str(ROOT/'vendor/private_runs/review-routing-controlled-v4-offline-1/tools')]
from workflow_cli_args import RENDER_COMMANDS, audit_parser, product_parser
import native_runtime

def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h','--help'):
        print(__doc__)
        return 0
    if sys.version_info < (3, 10):
        print('Python 3.10 or newer is required. Use an existing supported interpreter.', file=sys.stderr)
        return 2
    if args[0] == 'doctor':
        report = native_runtime.doctor()
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0 if report['ok'] else 2
    if args[0] not in ('product', 'audit'):
        print('Unknown command. Use doctor, product or audit.',file=sys.stderr)
        return 2
    product = args[0] == 'product'
    parser = product_parser() if product else audit_parser()
    parsed = parser.parse_args(args[1:])
    if product and parsed.command in RENDER_COMMANDS:
        report = native_runtime.doctor()
        if not report['ok']:
            print('\n'.join(report['errors']),file=sys.stderr)
            return 2
    try:
        if product:
            from workflow_v3 import cli
            cli(args=parsed)
        else:
            from audit_saved import cli
            cli(parsed)
    except FileExistsError as exc:
        print('Output already exists. Choose a new output directory; previous evidence was not overwritten. '+str(exc),file=sys.stderr)
        return 2
    except ModuleNotFoundError as exc:
        print('Required Python module is unavailable: '+str(exc)+'. Run doctor with the same Python, check the install path, and use the declared dependencies in an approved virtual environment.', file=sys.stderr)
        return 2
    except OSError as exc:
        print('Local file access stopped: '+str(exc)+'. Check that the source is readable, close files in use, and choose a fresh writable local folder.', file=sys.stderr)
        return 2
    except ValueError as exc:
        print('Local resume workflow stopped: '+str(exc),file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    if sys.version_info >= (3, 10) and not sys.flags.utf8_mode:
        # Keep interpreter isolation and site flags when enabling UTF-8.
        interpreter_args = sys.orig_argv[1:-len(sys.argv)]
        if interpreter_args and interpreter_args[-1] in ('-m', '--'):
            interpreter_args.pop()
        command = [sys.executable, *interpreter_args, '-X', 'utf8',
                   str(Path(__file__).resolve()), *sys.argv[1:]]
        raise SystemExit(subprocess.call(command))
    raise SystemExit(main())
