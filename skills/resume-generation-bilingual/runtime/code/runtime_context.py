"""One explicit clock reference reused by every stage of an offline workflow."""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from resume_controls.common import digest
from runtime_date_basis import DATE_BASIS_RULE

def clock_reference(*,observed_at=None,timezone=None):
    if observed_at is None:
        if timezone is not None:raise ValueError('timezone_without_clock')
        return {'as_of_date':None,'timezone':None,'authority':'unknown','observed_at':None}
    if not isinstance(observed_at,str) or 'T' not in observed_at:raise ValueError('aware_iso_clock_instant_required')
    dt=datetime.fromisoformat(observed_at.replace('Z','+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:raise ValueError('aware_iso_clock_instant_required')
    try:zone=ZoneInfo(timezone) if isinstance(timezone,str) else None
    except (ZoneInfoNotFoundError,ValueError) as exc:raise ValueError('known_iana_timezone_required')from exc
    if zone is None:raise ValueError('known_iana_timezone_required')
    return {'as_of_date':dt.astimezone(zone).date().isoformat(),'timezone':timezone,
        'authority':'caller_supplied_runtime_clock','observed_at':dt.isoformat()}

def validate_clock(value):
    if not isinstance(value,dict) or set(value)!={'as_of_date','timezone','authority','observed_at'}:
        raise ValueError('complete_runtime_clock_required')
    expected=clock_reference(observed_at=value['observed_at'],timezone=value['timezone'])
    if value!=expected:raise ValueError('runtime_clock_inconsistent')
    return deepcopy(value)

def attach_clock(request,basis):
    """Do not change source/date facts. Refuse a different in-flight clock."""
    basis=validate_clock(basis);q=deepcopy(request);q.pop('input_sha256',None)
    c=q['context']
    if 'runtime_date_basis' in c and c['runtime_date_basis']!=basis:
        raise ValueError('runtime_clock_changed_between_stages')
    c['runtime_date_basis']=basis
    if DATE_BASIS_RULE not in c['rules']:c['rules']+='\n'+DATE_BASIS_RULE
    if c['rules'].count(DATE_BASIS_RULE)!=1:raise ValueError('duplicate_runtime_clock_guidance')
    c['runtime_date_basis_sha256']=digest(basis)
    return {**q,'input_sha256':digest(q)}

def assert_clock(request,basis):
    basis=validate_clock(basis)
    if (request['context'].get('runtime_date_basis')!=basis
        or request['context'].get('runtime_date_basis_sha256')!=digest(basis)
        or DATE_BASIS_RULE not in request['context'].get('rules','')):
        raise ValueError('stage_runtime_clock_binding_missing')
    if request.get('input_sha256')!=digest({k:v for k,v in request.items() if k!='input_sha256'}):
        raise ValueError('stage_input_digest_changed')
    return True
