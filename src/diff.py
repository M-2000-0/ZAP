import json
from .lexer import Lexer
from .parser import Parser
from .analysis import extract_file

class PatchError(Exception):
    pass

def apply_patch(filepath, patch):
    with open(filepath, 'r') as f:
        source = f.read()
    lines = source.split('\n')

    patch_type = patch.get('type')
    if patch_type == 'replace_fn':
        return _patch_replace_fn(filepath, lines, patch)
    elif patch_type == 'replace_line':
        return _patch_replace_line(filepath, lines, patch)
    elif patch_type == 'insert_lines':
        return _patch_insert_lines(filepath, lines, patch)
    elif patch_type == 'delete_lines':
        return _patch_delete_lines(filepath, lines, patch)
    elif patch_type == 'rename_sym':
        return _patch_rename_sym(filepath, source, patch)
    elif patch_type == 'add_fn':
        return _patch_add_fn(filepath, lines, patch)
    else:
        raise PatchError(f"unknown patch type: {patch_type}")

def _find_fn_bounds(lines, fn_name):
    start = None
    depth = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f'fn {fn_name}(') or stripped.startswith(f'fn {fn_name} '):
            start = i
            depth = 1
        elif start is not None:
            indent = len(line) - len(line.lstrip())
            if stripped == '':
                if depth == 1 and indent == 0:
                    return start, i
                continue
            if indent == 0 and stripped:
                return start, i
            if indent == 0 and i == len(lines) - 1:
                return start, i + 1
    if start is not None:
        return start, len(lines)
    raise PatchError(f"function '{fn_name}' not found in {len(lines)} lines")

def _patch_replace_fn(filepath, lines, patch):
    fn_name = patch['name']
    new_body = patch['body']
    start, end = _find_fn_bounds(lines, fn_name)
    indent = len(lines[start]) - len(lines[start].lstrip())
    indented_body = '\n'.join(' ' * indent + line if line.strip() else line
                              for line in new_body.split('\n'))
    result = lines[:start] + [indented_body] + lines[end:]
    out = '\n'.join(result)
    with open(filepath, 'w') as f:
        f.write(out)
    return {'patched': filepath, 'type': 'replace_fn', 'name': fn_name}

def _patch_replace_line(filepath, lines, patch):
    line_num = patch['line']
    new_text = patch['text']
    if line_num < 1 or line_num > len(lines):
        raise PatchError(f"line {line_num} out of range (1-{len(lines)})")
    lines[line_num - 1] = new_text
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    return {'patched': filepath, 'type': 'replace_line', 'line': line_num}

def _patch_insert_lines(filepath, lines, patch):
    after_line = patch.get('after_line', len(lines))
    new_lines = patch['lines']
    insert_pos = after_line
    for l in new_lines:
        lines.insert(insert_pos, l)
        insert_pos += 1
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    return {'patched': filepath, 'type': 'insert_lines', 'at': after_line}

def _patch_delete_lines(filepath, lines, patch):
    start = patch['start_line']
    end = patch.get('end_line', start)
    if start < 1 or end > len(lines):
        raise PatchError(f"line range {start}-{end} out of range")
    del lines[start - 1:end]
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    return {'patched': filepath, 'type': 'delete_lines', 'range': [start, end]}

def _patch_rename_sym(filepath, source, patch):
    old_name = patch['old_name']
    new_name = patch['new_name']
    new_source = source.replace(old_name, new_name)
    with open(filepath, 'w') as f:
        f.write(new_source)
    return {'patched': filepath, 'type': 'rename_sym', 'from': old_name, 'to': new_name}

def _patch_add_fn(filepath, lines, patch):
    fn_def = patch['definition']
    insert_pos = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith('#'):
            continue
        if lines[i].strip() == '':
            continue
        insert_pos = i + 1
        break
    lines.insert(insert_pos, '')
    lines.insert(insert_pos + 1, fn_def)
    lines.insert(insert_pos + 2, '')
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    return {'patched': filepath, 'type': 'add_fn', 'name': fn_def.split('(')[0].replace('fn ', '').strip()}


def generate_diff(source_before, source_after):
    lines_before = source_before.split('\n')
    lines_after = source_after.split('\n')

    patches = []

    if lines_before == lines_after:
        return patches

    import difflib
    diff = list(difflib.unified_diff(lines_before, lines_after, n=1))

    add_lines = []
    del_start = None
    del_lines = []

    for line in diff:
        if line.startswith('@@'):
            if del_start is not None and del_lines:
                patches.append({
                    'type': 'delete_lines',
                    'start_line': del_start,
                    'end_line': del_start + len(del_lines) - 1,
                })
                del_start = None
                del_lines = []
            if add_lines:
                patches.append({
                    'type': 'insert_lines',
                    'after_line': None,
                    'lines': add_lines,
                })
                add_lines = []
        elif line.startswith('---') or line.startswith('+++'):
            continue
        elif line.startswith('-'):
            if del_start is None:
                del_start = 1
            del_lines.append(line[1:])
        elif line.startswith('+'):
            add_lines.append(line[1:])
        else:
            if del_start is not None and del_lines:
                patches.append({
                    'type': 'delete_lines',
                    'start_line': del_start,
                    'end_line': del_start + len(del_lines) - 1,
                })
                del_start = None
                del_lines = []
            if add_lines:
                patches.append({
                    'type': 'insert_lines',
                    'after_line': None,
                    'lines': add_lines,
                })
                add_lines = []

    if del_start is not None and del_lines:
        patches.append({
            'type': 'delete_lines',
            'start_line': del_start,
            'end_line': del_start + len(del_lines) - 1,
        })
    if add_lines:
        patches.append({
            'type': 'insert_lines',
            'after_line': None,
            'lines': add_lines,
        })

    return patches
