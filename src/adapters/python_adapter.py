import ast
import os
from .base import LanguageAdapter

class PythonAdapter(LanguageAdapter):
    language = 'python'
    extensions = ['.py']

    def extract(self, filepath):
        with open(filepath) as f:
            source = f.read()
        return self.extract_source(source, filepath)

    def extract_source(self, source, filepath='<unknown>'):
        symbols = []
        calls = []
        imports = []
        scope_stack = ['<global>']

        try:
            tree = ast.parse(source, filename=filepath)
        except SyntaxError:
            return self._make_index(symbols, calls, imports, filepath)

        def current_scope():
            return '.'.join(scope_stack)

        def add_sym(kind, name, node, **extra):
            symbols.append({
                'kind': kind,
                'name': name,
                'scope': current_scope(),
                'line': getattr(node, 'lineno', 0),
                'file': os.path.abspath(filepath),
                **extra,
            })

        def add_call(callee, node, args=None):
            calls.append({
                'callee': callee,
                'from_scope': current_scope(),
                'args': args or [],
                'line': getattr(node, 'lineno', 0),
            })

        def visit_body(body):
            for node in body:
                visit(node)

        def visit(node):
            if isinstance(node, ast.FunctionDef):
                params = [arg.arg for arg in node.args.args]
                add_sym('function', node.name, node, params=params,
                        returns=ast.dump(node.returns) if node.returns else None)
                scope_stack.append(node.name)
                for d in node.decorator_list:
                    if isinstance(d, ast.Call):
                        add_call(ast.dump(d.func), d)
                    elif isinstance(d, ast.Name):
                        add_call(d.id, d)
                    elif isinstance(d, ast.Attribute):
                        add_call(ast.dump(d), d)
                visit_body(node.body)
                scope_stack.pop()

            elif isinstance(node, ast.AsyncFunctionDef):
                params = [arg.arg for arg in node.args.args]
                add_sym('function', node.name, node, params=params, async_=True)
                scope_stack.append(node.name)
                visit_body(node.body)
                scope_stack.pop()

            elif isinstance(node, ast.ClassDef):
                bases = [ast.dump(b) for b in node.bases]
                add_sym('class', node.name, node, bases=bases,
                        methods=[n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))])
                scope_stack.append(node.name)
                visit_body(node.body)
                scope_stack.pop()

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        add_sym('assign', target.id, node)
                if isinstance(node.value, ast.Call):
                    callee = _callee_name(node.value.func)
                    add_call(callee, node, args=[ast.dump(a) for a in node.value.args])

            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    add_sym('assign', node.target.id, node, annotation=ast.dump(node.annotation))

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'module': alias.name,
                        'names': [alias.asname or alias.name],
                        'from_module': None,
                        'line': getattr(node, 'lineno', 0),
                    })

            elif isinstance(node, ast.ImportFrom):
                names = [alias.asname or alias.name for alias in node.names]
                imports.append({
                    'module': node.module or '',
                    'names': names,
                    'from_module': node.module,
                    'line': getattr(node, 'lineno', 0),
                })

            elif isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Call):
                    callee = _callee_name(node.value.func)
                    add_call(callee, node, args=[ast.dump(a) for a in node.value.args])

            elif isinstance(node, ast.Call):
                callee = _callee_name(node.func)
                add_call(callee, node, args=[ast.dump(a) for a in node.args])

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                 ast.Assign, ast.AnnAssign, ast.Import, ast.ImportFrom,
                                 ast.Expr)):
                if node is tree:
                    continue
                visit(node)

        # Top-level statements
        for node in ast.iter_child_nodes(tree):
            visit(node)

        return self._make_index(symbols, calls, imports, filepath)


def _callee_name(func):
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return _callee_name(func.value) + '.' + func.attr
    if isinstance(func, ast.Call):
        return _callee_name(func.func) + '()'
    return ast.dump(func)
