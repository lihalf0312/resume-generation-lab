"""Opt-in offline generation delta; the caller supplies the trusted clock date."""
from copy import deepcopy
from datetime import date
import re

DATE_BASIS_RULE = (
    "Current-date reference: runtime_date_basis is the caller-supplied clock reference, "
    "not personal evidence. Use its as_of_date and timezone only for calendar comparisons. "
    "If as_of_date is null or the reference is absent, do not guess today, label a source "
    "date future/past relative to now, or ask to correct a date on that guessed basis. "
    "Preserve source-supported dates. Compare only at the precision actually supplied; "
    "a month-only date does not establish a particular day. A future date can be a "
    "supported plan, not automatically an error. Calendar position alone never establishes "
    "employment, current enrollment, graduation, award or completion status. Apply this "
    "to questions and selection_notes as well as resume text."
)

def add_runtime_date_basis(request, digest, *, as_of_date=None, timezone=None):
    if request.get('stage') != 'generate':
        raise ValueError('generation_only')
    if as_of_date is None:
        if timezone is not None:
            raise ValueError('timezone_without_date')
    else:
        if not isinstance(as_of_date,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',as_of_date):
            raise ValueError('iso_calendar_date_required')
        date.fromisoformat(as_of_date)
        if not isinstance(timezone,str) or not re.fullmatch(r'[A-Za-z0-9_+./-]{1,80}',timezone):
            raise ValueError('explicit_timezone_required')
    result=deepcopy(request)
    result.pop('input_sha256',None)
    context=result['context']
    if 'runtime_date_basis' in context:
        raise ValueError('existing_date_basis_requires_explicit_replacement')
    context['runtime_date_basis']={'as_of_date':as_of_date,'timezone':timezone,'authority':'caller_supplied_runtime_clock' if as_of_date else 'unknown'}
    context['rules'] += '\n' + DATE_BASIS_RULE
    return {**result,'input_sha256':digest(result)}
