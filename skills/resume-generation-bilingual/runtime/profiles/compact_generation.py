"""Offline, generation-only prompt candidate. No provider calls or ledger code."""
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent


def describe_schema(schema, path='$'):
    """Derive field paths/limits from the actual schema, not stale prose."""
    if 'const' in schema:
        return [f'{path}: exactly {schema["const"]!r}']
    if 'enum' in schema:
        return [f'{path}: one of {schema["enum"]!r}']
    kind = schema['type']
    if kind == 'object':
        assert schema.get('additionalProperties') is False
        assert set(schema['required']) == set(schema['properties'])
        order = ['schema_version', 'state', 'necessary_questions', 'optional_questions', 'selection_notes', 'resume'] if path == '$' else sorted(schema['properties'])
        assert set(order) == set(schema['properties'])
        result = [f'{path}: object, required keys only {order}']
        for key in order:
            result += describe_schema(schema['properties'][key], path + '.' + key)
        return result
    if kind == 'array':
        return [f'{path}: array, {schema["minItems"]}..{schema["maxItems"]} items'] + describe_schema(schema['items'], path + '[]')
    if kind == 'string':
        return [f'{path}: string, {schema["minLength"]}..{schema["maxLength"]} characters']
    raise ValueError('unsupported_generation_schema_type:' + kind)


def output_rules(schema):
    p = schema['properties']
    expected = {'schema_version', 'resume', 'state', 'necessary_questions', 'optional_questions', 'selection_notes'}
    assert set(p) == set(schema['required']) == expected
    assert set(p['resume']['properties']) == {'name', 'sections'}
    version = p['schema_version']['const']
    return (
        'Generate one JSON object only, with no code fence, preface, suffix or second object. '
        'The supplied output_schema is the sole wire contract. Follow GENERATION_GUIDE.md for writing.\n'
        'Write these ROOT siblings in this order: schema_version, state, necessary_questions, '
        'optional_questions, selection_notes, resume. Write resume LAST; it contains only name and sections. '
        'The state, questions and selection_notes fields are never inside resume or a section. '
        'Bullets and notes are strings, never objects. Empty arrays and empty date strings are allowed only '
        'where the schema allows them. Use double-quoted JSON strings and escape internal quotes/newlines.\n'
        f'schema_version is {version!r}. After finishing the sections array, close the resume object, '
        'then close the ROOT object. Do not stop after closing only resume. '
        'Check balanced braces/brackets and required fields before returning.\n'
        'Exact field paths and limits derived from output_schema:\n' + '\n'.join(describe_schema(schema))
    )


def compact_request(baseline_request, digest):
    """Keep source/schema/template fields; change only two instruction carriers."""
    if baseline_request['stage'] != 'generate':
        raise ValueError('generation_only')
    request = deepcopy(baseline_request)
    request.pop('input_sha256', None)
    context = request['context']
    context['skill_files'] = {'GENERATION_GUIDE.md': (HERE / 'GENERATION_GUIDE.md').read_text(encoding='utf-8')}
    context['rules'] = output_rules(context['output_schema'])
    return {**request, 'input_sha256': digest(request)}
