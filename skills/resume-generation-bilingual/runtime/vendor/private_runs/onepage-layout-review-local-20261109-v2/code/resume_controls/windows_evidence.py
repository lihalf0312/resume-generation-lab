"""Windows write-once evidence on a fixed local NTFS volume.

Open one literal component relative to an already opened directory. Keep every
ancestor open during the operation. Never use a path precheck followed by a
separate absolute-path read or write.
"""

from contextlib import contextmanager, ExitStack
import ctypes as ct
from ctypes import wintypes as wt
import msvcrt
import os
from pathlib import Path
import re
from uuid import uuid4


_kernel = ct.WinDLL("kernel32", use_last_error=True)
_advapi = ct.WinDLL("advapi32", use_last_error=True)
_ntdll = ct.WinDLL("ntdll")

_READ = 0x80000000
_WRITE = 0x40000000
_READ_ATTRIBUTES = 0x80
_TRAVERSE = 0x20
_DELETE = 0x10000
_SYNCHRONIZE = 0x100000
_SHARE_READ = 1
_FILE_OPEN = 1
_FILE_CREATE = 2
_FILE_OPEN_IF = 3
_DIRECTORY_FILE = 1
_WRITE_THROUGH = 2
_SYNCHRONOUS_IO_NONALERT = 0x20
_NON_DIRECTORY_FILE = 0x40
_OPEN_REPARSE_POINT = 0x00200000
_ATTR_DIRECTORY = 0x10
_ATTR_NORMAL = 0x80
_ATTR_REPARSE_POINT = 0x400
_OBJ_CASE_INSENSITIVE = 0x40
_OBJ_DONT_REPARSE = 0x1000
_INVALID_HANDLE = ct.c_void_p(-1).value
_FILE_RENAME_INFORMATION = 10
_FILE_DISPOSITION_INFORMATION = 13
_CHUNK_SIZE = 1024 * 1024
_PENDING_PREFIX = ".resume-pending-"


class _UnicodeString(ct.Structure):
    _fields_ = [("Length", wt.USHORT), ("MaximumLength", wt.USHORT), ("Buffer", wt.LPWSTR)]


class _ObjectAttributes(ct.Structure):
    _fields_ = [
        ("Length", wt.ULONG), ("RootDirectory", wt.HANDLE),
        ("ObjectName", ct.POINTER(_UnicodeString)), ("Attributes", wt.ULONG),
        ("SecurityDescriptor", wt.LPVOID), ("SecurityQualityOfService", wt.LPVOID),
    ]


class _IoStatus(ct.Structure):
    _fields_ = [("StatusOrPointer", ct.c_void_p), ("Information", ct.c_size_t)]


class _RenameInformation(ct.Structure):
    _fields_ = [("ReplaceIfExists", wt.BYTE), ("RootDirectory", wt.HANDLE),
                ("FileNameLength", wt.ULONG), ("FileName", wt.WCHAR * 1)]


class _FileInformation(ct.Structure):
    _fields_ = [
        ("attributes", wt.DWORD), ("created", wt.FILETIME), ("accessed", wt.FILETIME),
        ("written", wt.FILETIME), ("volume", wt.DWORD), ("size_high", wt.DWORD),
        ("size_low", wt.DWORD), ("links", wt.DWORD), ("index_high", wt.DWORD),
        ("index_low", wt.DWORD),
    ]


def _bind(library, name, result, *args):
    function = getattr(library, name)
    function.restype = result
    function.argtypes = args
    return function


_create_root = _bind(_kernel, "CreateFileW", wt.HANDLE, wt.LPCWSTR, wt.DWORD, wt.DWORD,
                     wt.LPVOID, wt.DWORD, wt.DWORD, wt.HANDLE)
_close = _bind(_kernel, "CloseHandle", wt.BOOL, wt.HANDLE)
_drive_type = _bind(_kernel, "GetDriveTypeW", wt.UINT, wt.LPCWSTR)
_final_name = _bind(_kernel, "GetFinalPathNameByHandleW", wt.DWORD, wt.HANDLE, wt.LPWSTR,
                    wt.DWORD, wt.DWORD)
_volume_info = _bind(_kernel, "GetVolumeInformationByHandleW", wt.BOOL, wt.HANDLE, wt.LPWSTR,
                     wt.DWORD, ct.POINTER(wt.DWORD), ct.POINTER(wt.DWORD),
                     ct.POINTER(wt.DWORD), wt.LPWSTR, wt.DWORD)
_file_info = _bind(_kernel, "GetFileInformationByHandle", wt.BOOL, wt.HANDLE,
                   ct.POINTER(_FileInformation))
_nt_create = _bind(_ntdll, "NtCreateFile", wt.LONG, ct.POINTER(wt.HANDLE), wt.ULONG,
                   ct.POINTER(_ObjectAttributes), ct.POINTER(_IoStatus), wt.LPVOID,
                   wt.ULONG, wt.ULONG, wt.ULONG, wt.ULONG, wt.LPVOID, wt.ULONG)
_nt_set = _bind(_ntdll, "NtSetInformationFile", wt.LONG, wt.HANDLE, ct.POINTER(_IoStatus),
                wt.LPVOID, wt.ULONG, wt.ULONG)
_nt_error = _bind(_ntdll, "RtlNtStatusToDosError", wt.ULONG, wt.LONG)
_write_file = _bind(_kernel, "WriteFile", wt.BOOL, wt.HANDLE, wt.LPVOID, wt.DWORD,
                    ct.POINTER(wt.DWORD), wt.LPVOID)
_flush_buffers = _bind(_kernel, "FlushFileBuffers", wt.BOOL, wt.HANDLE)
_current_process = _bind(_kernel, "GetCurrentProcess", wt.HANDLE)
_local_free = _bind(_kernel, "LocalFree", wt.HLOCAL, wt.HLOCAL)
_open_token = _bind(_advapi, "OpenProcessToken", wt.BOOL, wt.HANDLE, wt.DWORD,
                    ct.POINTER(wt.HANDLE))
_token_info = _bind(_advapi, "GetTokenInformation", wt.BOOL, wt.HANDLE, wt.DWORD, wt.LPVOID,
                    wt.DWORD, ct.POINTER(wt.DWORD))
_sid_string = _bind(_advapi, "ConvertSidToStringSidW", wt.BOOL, wt.LPVOID, ct.POINTER(wt.LPWSTR))
_sddl = _bind(_advapi, "ConvertStringSecurityDescriptorToSecurityDescriptorW", wt.BOOL,
              wt.LPCWSTR, wt.DWORD, ct.POINTER(wt.LPVOID), ct.POINTER(wt.ULONG))

_RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[1-9¹²³])", re.I)


def _components(path):
    path = Path(path)
    if path.anchor and not path.is_absolute():
        raise ValueError("windows_evidence_ambiguous_path")
    if not path.is_absolute():
        path = Path.cwd() / path
    if not re.fullmatch(r"[A-Za-z]:\\", path.anchor) or len(path.parts) < 2:
        raise ValueError("windows_evidence_requires_local_drive_path")
    parts = path.parts[1:]
    for part in parts:
        if (part in (".", "..") or part.endswith((" ", "."))
                or part.casefold().startswith(_PENDING_PREFIX)
                or any(ord(char) < 32 or char in '<>:"/\\|?*' for char in part)
                or _RESERVED.fullmatch(part.split(".", 1)[0].rstrip(" "))):
            raise ValueError("windows_evidence_invalid_component")
    return path.anchor, parts


def _attributes(handle, *, directory):
    info = _FileInformation()
    if not _file_info(handle, ct.byref(info)):
        raise ct.WinError(ct.get_last_error())
    if info.attributes & _ATTR_REPARSE_POINT:
        raise ValueError("windows_evidence_reparse_point_forbidden")
    if bool(info.attributes & _ATTR_DIRECTORY) != directory:
        raise ValueError("windows_evidence_unexpected_object_type")
    if not directory and info.links != 1:
        raise ValueError("windows_evidence_hard_link_forbidden")


def _volume_root(drive):
    if _drive_type(drive) != 3:  # DRIVE_FIXED
        raise ValueError("windows_evidence_requires_fixed_local_volume")
    handle = _create_root(drive, _READ_ATTRIBUTES | _TRAVERSE | _SYNCHRONIZE,
                          _SHARE_READ, None, 3, 0x02000000 | _OPEN_REPARSE_POINT, None)
    if handle == _INVALID_HANDLE:
        raise ct.WinError(ct.get_last_error())
    try:
        _attributes(handle, directory=True)
        fs_name = ct.create_unicode_buffer(32)
        if not _volume_info(handle, None, 0, None, None, None, fs_name, len(fs_name)):
            raise ct.WinError(ct.get_last_error())
        if fs_name.value.upper() != "NTFS":
            raise ValueError("windows_evidence_requires_ntfs")
        name = ct.create_unicode_buffer(128)
        length = _final_name(handle, name, len(name), 1)  # VOLUME_NAME_GUID
        if not length:
            raise ct.WinError(ct.get_last_error())
        if length >= len(name) or not re.fullmatch(r"\\\\\?\\Volume\{[0-9a-f-]{36}\}\\", name.value, re.I):
            raise ValueError("windows_evidence_drive_must_anchor_volume_root")
        return handle
    except BaseException:
        _close(handle)
        raise


def _reject_staged_file(handle):
    # An 8.3 alias can hide the reserved prefix from lexical validation.
    # Inspect the opened object's normalized name without reopening its path.
    required = _final_name(handle, None, 0, 1)  # FILE_NAME_NORMALIZED | VOLUME_NAME_GUID
    if not required:
        raise ct.WinError(ct.get_last_error())
    buffer = ct.create_unicode_buffer(required + 1)
    actual = _final_name(handle, buffer, len(buffer), 1)
    if not actual:
        raise ct.WinError(ct.get_last_error())
    if actual >= len(buffer):
        raise OSError("windows_evidence_normalized_name_changed")
    if buffer.value.rsplit("\\", 1)[-1].casefold().startswith(_PENDING_PREFIX):
        raise ValueError("windows_evidence_reserved_staging_file")


def _open_relative(parent, name, *, directory=False, disposition=_FILE_OPEN,
                   access=_READ, share=_SHARE_READ, security=None, allow_pending=False):
    name_bytes = len(name.encode("utf-16-le"))
    buffer = ct.create_unicode_buffer(name)
    text = _UnicodeString(name_bytes, name_bytes + 2, ct.cast(buffer, wt.LPWSTR))
    attributes = _ObjectAttributes(ct.sizeof(_ObjectAttributes), parent, ct.pointer(text),
                                  _OBJ_CASE_INSENSITIVE | _OBJ_DONT_REPARSE, security, None)
    status = _IoStatus()
    handle = wt.HANDLE()
    options = _SYNCHRONOUS_IO_NONALERT
    if directory:
        options |= _DIRECTORY_FILE
    else:
        options |= _NON_DIRECTORY_FILE | _OPEN_REPARSE_POINT
        if disposition == _FILE_CREATE:
            options |= _WRITE_THROUGH
    result = _nt_create(ct.byref(handle), access | _SYNCHRONIZE, ct.byref(attributes),
                        ct.byref(status), None, 0 if directory else _ATTR_NORMAL,
                        share, disposition, options, None, 0)
    if result < 0:
        raise ct.WinError(_nt_error(result))
    try:
        _attributes(handle, directory=directory)
        if not directory and not allow_pending:
            _reject_staged_file(handle)
    except BaseException:
        _close(handle)
        raise
    return handle.value


@contextmanager
def _parent(path, *, create=False):
    drive, components = _components(path)
    with ExitStack() as stack:
        handle = _volume_root(drive)
        stack.callback(_close, handle)
        for name in components[:-1]:
            try:
                child = _open_relative(handle, name, directory=True, access=_READ_ATTRIBUTES | _TRAVERSE)
            except FileNotFoundError:
                if not create:
                    raise
                child = _open_relative(handle, name, directory=True, access=_READ_ATTRIBUTES | _TRAVERSE,
                                       disposition=_FILE_OPEN_IF)
            handle = child
            stack.callback(_close, handle)
        yield handle, components[-1]


@contextmanager
def _private_file_security():
    """Protect a new file with the current process user's SID, like mode 0600."""
    token = wt.HANDLE()
    if not _open_token(_current_process(), 0x0008, ct.byref(token)):  # TOKEN_QUERY
        raise ct.WinError(ct.get_last_error())
    with ExitStack() as stack:
        stack.callback(_close, token)
        size = wt.DWORD()
        _token_info(token, 1, None, 0, ct.byref(size))  # TokenUser
        if ct.get_last_error() != 122 or not size.value:
            raise ct.WinError(ct.get_last_error())
        data = ct.create_string_buffer(size.value)
        if not _token_info(token, 1, data, size.value, ct.byref(size)):
            raise ct.WinError(ct.get_last_error())
        sid = ct.cast(data, ct.POINTER(wt.LPVOID))[0]  # TOKEN_USER.User.Sid
        sid_text = wt.LPWSTR()
        if not _sid_string(sid, ct.byref(sid_text)):
            raise ct.WinError(ct.get_last_error())
        stack.callback(_local_free, ct.cast(sid_text, wt.HLOCAL))
        descriptor = wt.LPVOID()
        sddl = f"O:{sid_text.value}D:P(A;;FA;;;{sid_text.value})"
        if not _sddl(sddl, 1, ct.byref(descriptor), None):
            raise ct.WinError(ct.get_last_error())
        stack.callback(_local_free, descriptor)
        yield descriptor


def _stream(handle):
    flags = os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT
    try:
        fd = msvcrt.open_osfhandle(handle, flags)
    except BaseException:
        _close(handle)
        raise
    try:
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def read_bytes(path):
    with _parent(path) as (parent, name):
        with _stream(_open_relative(parent, name)) as stream:
            return stream.read()


def create_directory(path):
    with _parent(path, create=True) as (parent, name):
        handle = _open_relative(parent, name, directory=True, disposition=_FILE_CREATE,
                                access=_READ_ATTRIBUTES | _TRAVERSE)
        _close(handle)


def _check_existing(parent, name, raw):
    try:
        handle = _open_relative(parent, name)
    except FileNotFoundError:
        return False
    with _stream(handle) as stream:
        if stream.read() != raw:
            raise ValueError("immutable_evidence_changed:" + name)
    return True


def _write_all(handle, raw):
    offset = 0
    while offset < len(raw):
        chunk = raw[offset:offset + _CHUNK_SIZE]
        count = wt.DWORD()
        if not _write_file(handle, ct.c_char_p(chunk), len(chunk), ct.byref(count), None):
            raise ct.WinError(ct.get_last_error())
        if not 0 < count.value <= len(chunk):
            raise OSError("windows_evidence_invalid_write_count")
        offset += count.value


def _sync(handle):
    if not _flush_buffers(handle):
        raise ct.WinError(ct.get_last_error())


def _set_info(handle, value, size, information_class):
    status = _IoStatus()
    return _nt_set(handle, ct.byref(status), ct.byref(value), size, information_class)


def _discard(handle):
    result = _set_info(handle, wt.BYTE(1), 1, _FILE_DISPOSITION_INFORMATION)
    if result != 0:
        raise ct.WinError(_nt_error(result))


def _publish(handle, name):
    # A simple leaf name with RootDirectory=NULL renames within the staging
    # file's own directory. ReplaceIfExists stays false (zeroed buffer).
    encoded = name.encode("utf-16-le")
    offset = _RenameInformation.FileName.offset
    size = max(ct.sizeof(_RenameInformation), offset + len(encoded))
    buffer = ct.create_string_buffer(size)
    info = _RenameInformation.from_buffer(buffer)
    info.FileNameLength = len(encoded)
    ct.memmove(ct.addressof(buffer) + offset, encoded, len(encoded))
    return _set_info(handle, buffer, size, _FILE_RENAME_INFORMATION)


def save(path, raw):
    with _parent(path, create=True) as (parent, name):
        if _check_existing(parent, name, raw):
            return
        pending = _PENDING_PREFIX + uuid4().hex
        with _private_file_security() as security:
            handle = _open_relative(parent, pending, disposition=_FILE_CREATE,
                                    access=_WRITE | _READ_ATTRIBUTES | _DELETE,
                                    share=0, security=security, allow_pending=True)
        cleanup = True
        try:
            _write_all(handle, raw)
            _sync(handle)
            # An interrupt can arrive after the kernel has renamed this same
            # handle. Delete it only while we know it still names a staging file.
            cleanup = False
            result = _publish(handle, name)
            if result < 0:
                cleanup = True
                error = ct.WinError(_nt_error(result))
                if not isinstance(error, FileExistsError) or not _check_existing(parent, name, raw):
                    raise error
            elif result != 0:
                raise OSError("windows_evidence_publish_status_unknown")
        finally:
            try:
                if cleanup:
                    _discard(handle)
            finally:
                _close(handle)
