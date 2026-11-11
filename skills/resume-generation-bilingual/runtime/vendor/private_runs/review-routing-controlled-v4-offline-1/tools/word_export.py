"""Native Word COM export through pywin32, not a PowerShell script.

This uses a new dedicated COM application instance. It never attaches to a
running document, invokes a shell script, installs anything or changes policy.
"""
from pathlib import Path
import argparse, json, sys

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('docx',type=Path)
    parser.add_argument('pdf',type=Path)
    args=parser.parse_args()
    if args.pdf.exists():
        raise ValueError('Refusing to overwrite existing PDF.')
    from native_runtime import inspect_docx
    inspect_docx(args.docx)
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise ValueError('pywin32 is required for native Word COM. Ask before installing it into this skill\'s isolated Python environment.') from exc
    application=None
    document=None
    pythoncom.CoInitialize()
    try:
        application=win32com.client.DispatchEx('Word.Application')
        application.Visible=False
        application.DisplayAlerts=0
        application.AutomationSecurity=3
        document=application.Documents.Open(str(args.docx.resolve()),False,True,False)
        document.ExportAsFixedFormat(str(args.pdf.resolve()),17)
        report={'backend':'word','implementation':'pywin32 DispatchEx',
                'version':application.Version,'pages':document.ComputeStatistics(2),
                'pdf':str(args.pdf.resolve()),'existing_user_documents_accessed':False}
        print(json.dumps(report,ensure_ascii=False))
    finally:
        try:
            if document is not None: document.Close(0)
        finally:
            document=None
            if application is not None: application.Quit(0)
            application=None
            pythoncom.CoUninitialize()

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print('Native Word export failed: '+str(exc),file=sys.stderr)
        raise SystemExit(2)
