"""Deterministic, write-once evidence helpers. No network or credential dependencies."""
from pathlib import Path
import hashlib,json,os,tempfile,math

if os.name == 'nt':
 from . import windows_evidence

def encode(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(obj):return hashlib.sha256(encode(obj)).hexdigest()
def text_hash(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def read_evidence_bytes(path):
 return windows_evidence.read_bytes(path) if os.name=='nt' else Path(path).read_bytes()
def file_hash(path):return hashlib.sha256(read_evidence_bytes(path)).hexdigest()
def read(path):
 if os.name=='nt':return strict_json(read_evidence_bytes(path).decode('utf-8'))
 p=Path(path)
 if p.is_symlink():raise ValueError('symlink_evidence_forbidden')
 return strict_json(p.read_text())
def strict_json(text):
 def pairs(items):
  out={}
  for k,v in items:
   if k in out:raise ValueError('duplicate_JSON_key:'+k)
   out[k]=v
  return out
 return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_JSON_number')))
def create_evidence_dir(path):
 if os.name=='nt':return windows_evidence.create_directory(path)
 Path(path).mkdir(parents=True,exist_ok=False)
def save_evidence_bytes(path,raw):
 if os.name=='nt':return windows_evidence.save(path,raw)
 with Path(path).open('xb') as stream:stream.write(raw)
def save(path,obj):
 raw=encode(obj)+b'\n'
 if os.name=='nt':return windows_evidence.save(path,raw)
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():
  if p.is_symlink() or p.read_bytes()!=raw:raise ValueError('immutable_evidence_changed:'+p.name)
  return
 fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 fsync_dir(p.parent)
def fsync_dir(path):
 if os.name=='nt':raise NotImplementedError('POSIX directory fsync is not available on Windows')
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def atomic_replace(path,obj):
 if os.name=='nt':raise NotImplementedError('Mutable evidence state is POSIX-only')
 p=Path(path)
 if p.is_symlink():raise ValueError('symlink_state_forbidden')
 fd,tmp=tempfile.mkstemp(prefix='.pending-',dir=p.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(encode(obj)+b'\n');f.flush();os.fsync(f.fileno())
  os.replace(tmp,p);fsync_dir(p.parent)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def finite_number(n):return type(n) in [int,float] and math.isfinite(n)
