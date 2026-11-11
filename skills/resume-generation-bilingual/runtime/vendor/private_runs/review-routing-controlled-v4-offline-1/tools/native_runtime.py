"""Local native renderer selection. No install, download, font copy or network client."""
from pathlib import Path
import hashlib, importlib.util, json, os, platform, shutil, subprocess, sys, tempfile, zipfile
from xml.etree import ElementTree as ET

FONT_NAMES = ('times.ttf', 'timesbd.ttf', 'simkai.ttf', 'wingding.ttf')

def font_directory():
    explicit = os.environ.get('RESUME_FONT_DIR')
    if explicit:
        return Path(explicit).expanduser().resolve()
    if sys.platform == 'win32':
        return Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts'
    if sys.platform == 'darwin':
        candidates = [Path.home()/'Library/Fonts', Path('/Library/Fonts'),
                      Path('/Library/Fonts/Microsoft'), Path('/Applications/Microsoft Word.app/Contents/Resources/DFonts')]
        return next((p for p in candidates if all((p/f).is_file() for f in FONT_NAMES)), candidates[0])
    return Path.home()/'.local/share/fonts'

def backend_name():
    name = os.environ.get('RESUME_RENDER_BACKEND', 'word' if sys.platform == 'win32' else 'libreoffice')
    if name not in ('word', 'libreoffice'):
        raise ValueError('RESUME_RENDER_BACKEND must be word or libreoffice.')
    return name

def renderer_path():
    if backend_name() == 'word':
        if sys.platform != 'win32':
            raise ValueError('The Word COM backend requires Windows. macOS Word is not validated.')
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\WINWORD.EXE') as key:
                value = Path(winreg.QueryValueEx(key, None)[0])
        except OSError as exc:
            raise ValueError('Desktop Microsoft Word was not found. Open an existing desktop Word installation, or keep the draft as text until Word is available. No renderer was selected as a fallback.') from exc
        if not value.is_file():
            raise ValueError('Microsoft Word registration points to a missing executable.')
        return value
    explicit = os.environ.get('RESUME_SOFFICE')
    candidate = explicit or shutil.which('soffice')
    value = Path(candidate).expanduser() if candidate else None
    if value is None or not value.is_file():
        raise ValueError('LibreOffice is not configured. Set RESUME_SOFFICE to the approved soffice executable. On macOS the usual application path is /Applications/LibreOffice.app/Contents/MacOS/soffice. No software was installed.')
    return value.resolve()

def environment():
    return dict(os.environ)

def doctor():
    errors = []
    packages = {}
    for name in ('docx', 'lxml', 'pymupdf', 'PIL', 'pdfplumber'):
        present = importlib.util.find_spec(name) is not None
        packages[name] = present
        if not present:
            errors.append('Missing Python package: '+name+'. Use this skill\'s requirements-native.txt in a virtual environment, after permission to install dependencies.')
    if sys.version_info < (3, 10):
        errors.append('Python 3.10 or newer is required.')
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo('Etc/UTC')
        timezone_ok = True
    except Exception:
        timezone_ok = False
        errors.append('IANA timezone data is missing. Install tzdata from requirements-native.txt after permission.')
    folder = font_directory()
    fonts = {}
    for name in FONT_NAMES:
        path = folder/name
        fonts[name] = {'path':str(path), 'present':path.is_file()}
        if path.is_file():
            try:
                fonts[name]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                errors.append('Required licensed font cannot be read: '+str(path)+'. Use a readable, licensed font folder.')
        else:
            errors.append('Missing required licensed font: '+str(path)+'. Set RESUME_FONT_DIR to an existing licensed folder; no fallback or redistribution is performed.')
    try:
        selected = backend_name()
        path = str(renderer_path())
    except ValueError as exc:
        selected = os.environ.get('RESUME_RENDER_BACKEND', 'word' if sys.platform == 'win32' else 'libreoffice')
        path = None
        errors.append(str(exc))
    if selected == 'word':
        for name in ('pythoncom','win32com'):
            packages[name] = importlib.util.find_spec(name) is not None
            if not packages[name]:
                errors.append('Missing native Word COM dependency: '+name+'. Ask before installing pywin32 from official PyPI into this skill\'s isolated Python environment. No PowerShell or security-policy change is needed.')
    return {'schema':'native-render-environment-v1', 'ok':not errors, 'platform':platform.platform(),
            'python':sys.version.split()[0], 'backend':selected, 'renderer':path,
            'packages':packages, 'timezone_data':timezone_ok, 'fonts':fonts, 'errors':errors,
            'font_substitution_allowed':False, 'api_calls':0,
            'scope':'Dependency presence only, not rendering, clean-machine installation, macOS acceptance, or semantic validation.'}

def check_environment():
    report = doctor()
    if not report['ok']:
        raise ValueError('Native render prerequisites missing:\n'+'\n'.join(report['errors']))
    if sys.platform.startswith('linux'):
        for name, filename in [('Times New Roman','times.ttf'), ('楷体','simkai.ttf'), ('Wingdings','wingding.ttf')]:
            proc = subprocess.run(['fc-match','-f','%{file}',name], env=environment(), capture_output=True, text=True, check=True)
            if Path(proc.stdout).resolve() != (font_directory()/filename).resolve():
                raise ValueError('Configured font unavailable; no fallback: '+name)
    return report

def inspect_docx(path):
    """Refuse active content and network relationships before opening desktop Word."""
    with zipfile.ZipFile(path) as package:
        if any(any(s in name.lower() for s in ('vbaproject','activex','embeddings/')) for name in package.namelist()):
            raise ValueError('Unsafe DOCX: macro, active content or embedded object detected.')
        for name in package.namelist():
            if name.endswith('.rels'):
                root = ET.fromstring(package.read(name))
                if any(rel.get('TargetMode') == 'External' for rel in root):
                    raise ValueError('Unsafe DOCX: external relationship requires a separate user review.')
            if name.startswith('word/') and name.endswith('.xml'):
                root = ET.fromstring(package.read(name))
                ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                fields = [''.join(x.itertext()) for x in root.iter(ns+'instrText')]
                fields += [x.get(ns+'instr','') for x in root.iter(ns+'fldSimple')]
                if any(x.strip() for x in fields):
                    raise ValueError('Unsafe DOCX: dynamic field requires a separate user review.')
    return {'active_content':False, 'external_relationships':False, 'dynamic_fields':False}

def convert_docx(docx, output_dir, timeout=90):
    docx, output_dir = Path(docx).resolve(), Path(output_dir).resolve()
    pdf = output_dir/(docx.stem+'.pdf')
    if pdf.exists():
        raise ValueError('PDF output exists; choose a new run directory. Existing history is never overwritten.')
    inspect_docx(docx)
    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = renderer_path()
    if backend_name() == 'word':
        if importlib.util.find_spec('win32com') is None or importlib.util.find_spec('pythoncom') is None:
            raise ValueError('Native Word export requires pywin32. No automatic dependency install or PowerShell fallback is performed.')
        script = Path(__file__).with_name('word_export.py')
        args = [sys.executable, '-X', 'utf8', str(script), str(docx), str(pdf)]
        try:
            return subprocess.run(args, env=environment(), capture_output=True, text=True,
                                  encoding='utf-8', errors='replace', timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise ValueError('Word export timed out; outcome uncertain. Do not retry automatically. Inspect this run and the dedicated Word instance; never close unrelated user documents.') from exc
    with tempfile.TemporaryDirectory(prefix='resume-native-lo-') as profile:
        return subprocess.run([str(renderer),'--headless','--norestore','--nodefault','--nologo',
            '-env:UserInstallation='+Path(profile).as_uri(),'--convert-to','pdf:writer_pdf_Export',
            '--outdir',str(output_dir),str(docx)], env=environment(), capture_output=True,
            text=True, encoding='utf-8', errors='replace', timeout=timeout)

if __name__ == '__main__':
    report = doctor()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report['ok'] else 2)
