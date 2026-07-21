import re
import os
from .base import LanguageAdapter

class JSAdapter(LanguageAdapter):
    language = 'javascript'
    extensions = ['.js', '.jsx', '.ts', '.tsx']

    def extract(self, filepath):
        with open(filepath) as f:
            source = f.read()
        return self.extract_source(source, filepath)

    def extract_source(self, source, filepath='<unknown>'):
        symbols = []
        calls = []
        imports = []
        scope_stack = ['<global>']
        lines = source.split('\n')

        def current_scope():
            return '.'.join(scope_stack)

        def add_sym(kind, name, line, **extra):
            symbols.append({
                'kind': kind,
                'name': name,
                'scope': current_scope(),
                'line': line,
                'file': os.path.abspath(filepath),
                **extra,
            })

        def add_call(callee, line, args=None):
            calls.append({
                'callee': callee,
                'from_scope': current_scope(),
                'args': args or [],
                'line': line,
            })

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            line_num = i + 1

            # Skip comments and empty lines
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                i += 1
                continue

            # Multi-line comment
            if '/*' in stripped:
                while i < len(lines) and '*/' not in lines[i]:
                    i += 1
                i += 1
                continue

            # imports: import X from 'y' / import { X } from 'y'
            m = re.match(r'^import\s+(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]', stripped)
            if m:
                imports.append({
                    'module': m.group(1),
                    'names': [],
                    'from_module': m.group(1),
                    'line': line_num,
                })
                i += 1
                continue

            # require: const X = require('y')
            m = re.match(r'.*=\s*require\s*\([\'"]([^\'"]+)[\'"]\)', stripped)
            if m:
                imports.append({
                    'module': m.group(1),
                    'names': [],
                    'from_module': m.group(1),
                    'line': line_num,
                })
                i += 1
                continue

            # function declarations: function name(...
            m = re.match(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)', stripped)
            if m:
                name = m.group(1)
                params_match = re.search(r'\(([^)]*)\)', stripped)
                params = [p.strip() for p in params_match.group(1).split(',')] if params_match and params_match.group(1).strip() else []
                add_sym('function', name, line_num, params=params)

                # Collect calls inside function body
                scope_stack.append(name)
                brace_count = 0
                j = i + 1
                while j < len(lines):
                    body_line = lines[j]
                    body_stripped = body_line.strip()
                    # Find calls
                    call_m = re.findall(r'(\w+)\s*\(', body_stripped)
                    for callee in call_m:
                        if callee not in ('if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'typeof', 'delete', 'void', 'throw', 'new'):
                            add_call(callee, j + 1)
                    brace_count += body_stripped.count('{') - body_stripped.count('}')
                    if brace_count <= 0 and '{' not in body_stripped.split('//')[0]:
                        # Check if we're past the function body
                        pass
                    j += 1
                    if brace_count <= 0 and j > i + 1:
                        break
                scope_stack.pop()

                # Skip function body lines (approximate)
                brace_count = 0
                start_line = i
                while i < len(lines):
                    brace_count += lines[i].count('{') - lines[i].count('}')
                    i += 1
                    if brace_count <= 0 and i > start_line + 1:
                        break
                continue

            # arrow/const functions: const name = (params) => ...
            m = re.match(r'^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:\(([^)]*)\)|(\w+))\s*=>', stripped)
            if m:
                name = m.group(1)
                param_str = m.group(2) or m.group(3) or ''
                params = [p.strip() for p in param_str.split(',')] if param_str.strip() else []
                add_sym('function', name, line_num, params=params)
                i += 1
                continue

            # class declarations: class Name { ... }
            m = re.match(r'^(?:export\s+)?class\s+(\w+)', stripped)
            if m:
                name = m.group(1)
                add_sym('class', name, line_num)
                scope_stack.append(name)
                # Collect methods
                j = i + 1
                brace_count = 1
                while j < len(lines):
                    bj = lines[j].strip()
                    method_m = re.match(r'^(?:async\s+)?(\w+)\s*\(', bj)
                    if method_m and not bj.startswith('//'):
                        method_name = method_m.group(1)
                        if method_name not in ('constructor', 'static', 'get', 'set'):
                            add_sym('method', method_name, j + 1, parent_class=name)
                    brace_count += lines[j].count('{') - lines[j].count('}')
                    j += 1
                    if brace_count <= 0:
                        break
                scope_stack.pop()
                i = j
                continue

            # Arrow functions assigned to exports: exports.name = ...
            m = re.match(r'^exports\.(\w+)\s*=\s*(?:\(([^)]*)\)|(\w+))\s*=>', stripped)
            if m:
                name = m.group(1)
                add_sym('function', name, line_num)
                i += 1
                continue

            # Simple calls at top level
            call_m = re.match(r'^(\w+)\s*\(', stripped)
            if call_m:
                callee = call_m.group(1)
                if callee not in ('if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'typeof', 'delete', 'void', 'throw', 'new', 'console', 'import'):
                    add_call(callee, line_num)

            i += 1

        return self._make_index(symbols, calls, imports, filepath)
