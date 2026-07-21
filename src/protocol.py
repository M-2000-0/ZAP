import json
import os
from .diff import apply_patch, PatchError, generate_diff
from .analysis import extract_file
from .indexer import ProjectIndex

def verify_edit(edit, filepath):
    errors = []
    edit_type = edit.get('type')

    if not os.path.exists(filepath):
        errors.append(f"file not found: {filepath}")
        return {'valid': False, 'errors': errors}

    if edit_type == 'replace_fn':
        fn_name = edit.get('name')
        if not fn_name:
            errors.append("'name' required for replace_fn")
        try:
            idx = extract_file(filepath)
            found = any(s['kind'] == 'function' and s['name'] == fn_name for s in idx['symbols'])
            if not found:
                errors.append(f"function '{fn_name}' not found in {filepath}")
        except Exception as e:
            errors.append(f"parse error: {e}")

    elif edit_type == 'replace_line':
        line = edit.get('line')
        with open(filepath) as f:
            lines = f.readlines()
        if line < 1 or line > len(lines):
            errors.append(f"line {line} out of range (1-{len(lines)})")

    elif edit_type == 'insert_lines':
        after = edit.get('after_line')
        if after is not None:
            with open(filepath) as f:
                lines = f.readlines()
            if after < 0 or after > len(lines):
                errors.append(f"after_line {after} out of range")

    elif edit_type == 'delete_lines':
        start = edit.get('start_line')
        end = edit.get('end_line', start)
        with open(filepath) as f:
            lines = f.readlines()
        if start < 1 or end > len(lines):
            errors.append(f"line range {start}-{end} out of range (1-{len(lines)})")

    elif edit_type == 'rename_sym':
        old = edit.get('old_name')
        new = edit.get('new_name')
        if not old or not new:
            errors.append("'old_name' and 'new_name' required")

    elif edit_type == 'add_fn':
        if not edit.get('definition'):
            errors.append("'definition' required for add_fn")

    elif edit_type == 'batch':
        sub_edits = edit.get('edits', [])
        for i, sub in enumerate(sub_edits):
            sub_result = verify_edit(sub, filepath)
            if not sub_result['valid']:
                for e in sub_result['errors']:
                    errors.append(f"edit[{i}]: {e}")

    else:
        errors.append(f"unknown edit type: {edit_type}")

    return {'valid': len(errors) == 0, 'errors': errors}


def apply_edit(edit, filepath):
    result = verify_edit(edit, filepath)
    if not result['valid']:
        return {'applied': False, 'errors': result['errors']}

    if edit.get('type') == 'batch':
        results = []
        for sub in edit.get('edits', []):
            r = apply_edit(sub, filepath)
            results.append(r)
        return {'applied': all(r['applied'] for r in results), 'results': results}

    try:
        with open(filepath) as f:
            before = f.read()
        apply_result = apply_patch(filepath, edit)
        with open(filepath) as f:
            after = f.read()
        diff = generate_diff(before, after)
        return {
            'applied': True,
            'patches': diff,
            'summary': apply_result,
        }
    except (PatchError, IOError) as e:
        return {'applied': False, 'errors': [str(e)]}


def ai_query(query, project_root='.'):
    idx = ProjectIndex(project_root)
    idx.load()

    q = query.lower()
    results = []

    if q.startswith('show me ') or q.startswith('find '):
        target = q.split('the ')[-1] if 'the ' in q else q.split(' ', 1)[-1] if ' ' in q else q
        target = target.strip().rstrip('.')
        syms = idx.query_symbol(target)
        results.append({
            'type': 'symbol_query',
            'query': target,
            'results': [{
                'file': s.get('file', ''),
                'line': s.get('line', 0),
                'kind': s.get('kind', ''),
                'name': s.get('name', ''),
            } for s in syms],
        })

    elif q.startswith('depends') or 'dependency' in q:
        graph = idx.dep_graph
        results.append({
            'type': 'dependency_graph',
            'graph': graph,
        })

    elif q.startswith('callers') or 'calls' in q:
        parts = q.split(' ')
        target = parts[-1]
        callers = idx.query_calls_to(target)
        results.append({
            'type': 'callers',
            'target': target,
            'callers': callers,
        })

    elif q.startswith('all ') or q.startswith('list '):
        target_type = q.split(' ')[-1]
        type_map = {
            'functions': 'function', 'services': 'service', 'apis': 'api',
            'pages': 'page', 'schemas': 'schema', 'models': 'model',
            'databases': 'database',
        }
        kind = type_map.get(target_type, target_type.rstrip('s'))
        all_syms = []
        for filepath, file_idx in idx.files.items():
            for sym in file_idx.get('symbols', []):
                if sym.get('kind') == kind:
                    all_syms.append({**sym, 'file': filepath})
        results.append({
            'type': 'list',
            'kind': kind,
            'results': all_syms,
        })

    if not results:
        syms = idx.query_symbol(query)
        results.append({
            'type': 'search',
            'query': query,
            'results': [{
                'file': s.get('file', ''),
                'line': s.get('line', 0),
                'kind': s.get('kind', ''),
                'name': s.get('name', ''),
            } for s in syms],
        })

    return results
