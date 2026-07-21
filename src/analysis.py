import json
import os
from .lexer import Lexer
from .parser import Parser
from .ast_nodes import *

class SymbolExtractor:
    def __init__(self):
        self.symbols = []
        self.calls = []
        self.imports = []
        self.scope_stack = ['<global>']
        self.filepath = '<unknown>'

    def extract(self, ast, filepath='<unknown>'):
        self.filepath = filepath
        self.symbols = []
        self.calls = []
        self.imports = []
        self.scope_stack = ['<global>']
        self._visit(ast)
        return self._build_index()

    def _build_index(self):
        return {
            'file': self.filepath,
            'symbols': self.symbols,
            'calls': self.calls,
            'imports': self.imports,
        }

    def _current_scope(self):
        return '.'.join(self.scope_stack)

    def _visit(self, node):
        if isinstance(node, Program):
            for stmt in node.stmts:
                self._visit_stmt(stmt)
        elif isinstance(node, Block):
            for stmt in node.stmts:
                self._visit_stmt(stmt)
        else:
            self._visit_stmt(node)

    def _visit_stmt(self, stmt):
        if isinstance(stmt, FnDef):
            self._visit_fn_def(stmt)
        elif isinstance(stmt, ClassDef):
            self._visit_class_def(stmt)
        elif isinstance(stmt, LetStmt):
            self.symbols.append({
                'kind': 'let',
                'name': stmt.name,
                'type': stmt.type_annotation,
                'scope': self._current_scope(),
                'line': stmt.line,
                'file': self.filepath,
            })
        elif isinstance(stmt, ServiceDecl):
            self.symbols.append({
                'kind': 'service', 'name': stmt.name,
                'expose': stmt.expose,
                'methods': [m.name for m in stmt.methods],
                'scope': self._current_scope(), 'line': stmt.line, 'file': self.filepath,
            })
            self.scope_stack.append(stmt.name)
            for m in stmt.methods:
                self._visit_fn_def(m)
            self.scope_stack.pop()
        elif isinstance(stmt, DatabaseDecl):
            self.symbols.append({
                'kind': 'database', 'name': stmt.name,
                'tables': [t.name for t in stmt.tables],
                'scope': self._current_scope(), 'line': stmt.line, 'file': self.filepath,
            })
            for t in stmt.tables:
                self._visit_stmt(t)
        elif isinstance(stmt, ApiEndpoint):
            self.symbols.append({
                'kind': 'api', 'name': f"{stmt.method} {stmt.path}",
                'method': stmt.method, 'path': stmt.path,
                'returns': stmt.returns,
                'scope': self._current_scope(), 'line': stmt.line, 'file': self.filepath,
            })
            if stmt.handler:
                self._visit_fn_def(stmt.handler)
        elif isinstance(stmt, PageDecl):
            self.symbols.append({
                'kind': 'page', 'name': stmt.name,
                'route': stmt.route,
                'scope': self._current_scope(), 'line': stmt.line, 'file': self.filepath,
            })
        elif isinstance(stmt, SchemaDecl):
            self.symbols.append({
                'kind': 'schema', 'name': stmt.name,
                'fields': [{'name': f.name, 'type': f.field_type} for f in stmt.fields],
                'scope': self._current_scope(), 'line': stmt.line, 'file': self.filepath,
            })
        elif isinstance(stmt, ModelDecl):
            self.symbols.append({
                'kind': 'model', 'name': stmt.name,
                'fields': [{'name': f.name, 'type': f.field_type} for f in stmt.fields],
                'methods': [m.name for m in stmt.methods],
                'scope': self._current_scope(), 'line': stmt.line, 'file': self.filepath,
            })
            self.scope_stack.append(stmt.name)
            for m in stmt.methods:
                self._visit_fn_def(m)
            self.scope_stack.pop()
        elif isinstance(stmt, AssignStmt):
            if isinstance(stmt.target, Identifier):
                self.symbols.append({
                    'kind': 'assign',
                    'name': stmt.target.name,
                    'type': None,
                    'scope': self._current_scope(),
                    'line': stmt.line,
                    'file': self.filepath,
                })
        elif isinstance(stmt, ImportStmt):
            self.imports.append({
                'module': stmt.module,
                'names': stmt.names,
                'from_module': stmt.from_module,
                'line': stmt.line,
            })
        elif isinstance(stmt, ExprStmt):
            self._visit_expr(stmt.expr)
        elif isinstance(stmt, RetStmt):
            if stmt.value:
                self._visit_expr(stmt.value)
        elif isinstance(stmt, IfStmt):
            self._visit_expr(stmt.condition)
            self._visit(stmt.body)
            if stmt.else_body:
                self._visit(stmt.else_body)
        elif isinstance(stmt, ForStmt):
            self._visit_expr(stmt.iterable)
            self._visit(stmt.body)
        elif isinstance(stmt, WhileStmt):
            self._visit_expr(stmt.condition)
            self._visit(stmt.body)

    def _visit_fn_def(self, stmt):
        self.symbols.append({
            'kind': 'function',
            'name': stmt.name,
            'params': [p['name'] for p in stmt.params],
            'return_type': stmt.return_type,
            'scope': self._current_scope(),
            'line': stmt.line,
            'file': self.filepath,
        })
        self.scope_stack.append(stmt.name)
        self._visit(stmt.body)
        self.scope_stack.pop()

    def _visit_class_def(self, stmt):
        self.symbols.append({
            'kind': 'class',
            'name': stmt.name,
            'base': stmt.base,
            'methods': [m.name for m in stmt.methods],
            'scope': self._current_scope(),
            'line': stmt.line,
            'file': self.filepath,
        })
        self.scope_stack.append(stmt.name)
        for m in stmt.methods:
            self._visit_fn_def(m)
        self.scope_stack.pop()

    def _visit_expr(self, expr):
        if isinstance(expr, Call):
            callee_name = self._get_callee_name(expr.callee)
            args_info = []
            for a in expr.args:
                args_info.append(self._expr_type_hint(a))
            self.calls.append({
                'callee': callee_name,
                'from_scope': self._current_scope(),
                'args': args_info,
                'line': expr.line,
            })
            self._visit_expr(expr.callee)
            for a in expr.args:
                self._visit_expr(a)
        elif isinstance(expr, BinOp):
            self._visit_expr(expr.left)
            self._visit_expr(expr.right)
        elif isinstance(expr, UnaryOp):
            self._visit_expr(expr.operand)
        elif isinstance(expr, Identifier):
            pass
        elif isinstance(expr, Literal):
            pass
        elif isinstance(expr, ListLiteral):
            for e in expr.elements:
                self._visit_expr(e)
        elif isinstance(expr, DictLiteral):
            for k, v in expr.entries:
                self._visit_expr(k)
                self._visit_expr(v)
        elif isinstance(expr, MemberAccess):
            self._visit_expr(expr.obj)
        elif isinstance(expr, Index):
            self._visit_expr(expr.obj)
            self._visit_expr(expr.index)
        elif isinstance(expr, Slice):
            self._visit_expr(expr.obj)

    def _get_callee_name(self, expr):
        if isinstance(expr, Identifier):
            return expr.name
        if isinstance(expr, MemberAccess):
            return f"{self._get_callee_name(expr.obj)}.{expr.member}"
        return str(expr)

    def _expr_type_hint(self, expr):
        if isinstance(expr, Literal):
            if isinstance(expr.value, str):
                return 'string'
            if isinstance(expr.value, (int, float)):
                return 'number'
            if expr.value is True or expr.value is False:
                return 'bool'
            if expr.value is None:
                return 'none'
        if isinstance(expr, Identifier):
            return f"ref:{expr.name}"
        if isinstance(expr, ListLiteral):
            return 'list'
        if isinstance(expr, DictLiteral):
            return 'dict'
        if isinstance(expr, Call):
            return f'call:{self._get_callee_name(expr)}'
        if isinstance(expr, BinOp):
            return 'expr'
        return 'unknown'


def extract_file(filepath):
    with open(filepath, 'r') as f:
        source = f.read()
    lexer = Lexer(source, filepath)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    extractor = SymbolExtractor()
    return extractor.extract(ast, filepath)


def build_dependency_graph(indexes):
    all_symbols = {}
    all_calls = []
    file_symbols = {}

    for idx in indexes:
        filepath = idx['file']
        file_symbols[filepath] = set()
        for sym in idx['symbols']:
            key = f"{sym['scope']}.{sym['name']}"
            all_symbols[key] = sym
            file_symbols[filepath].add(key)
        for c in idx['calls']:
            all_calls.append({**c, 'file': filepath})

    deps = {}
    for filepath, syms in file_symbols.items():
        deps[filepath] = {'provides': list(syms), 'depends_on': set()}

    for c in all_calls:
        callee = c['callee']
        caller_scope = c['from_scope']
        # Find which file defines the callee
        for sym_key, sym in all_symbols.items():
            if sym['name'] == callee or sym_key.endswith(f".{callee}"):
                caller_file = c['file']
                callee_file = sym['file']
                if caller_file != callee_file:
                    deps[caller_file]['depends_on'].add(callee_file)

    result = {}
    for filepath, info in deps.items():
        result[filepath] = {
            'provides': info['provides'],
            'depends_on': list(info['depends_on']),
        }
    return result


def format_graph(dep_graph):
    lines = ['digraph zap_deps {']
    for filepath, info in dep_graph.items():
        label = os.path.basename(filepath)
        lines.append(f'  "{filepath}" [label="{label}" shape=box];')
        for dep in info['depends_on']:
            lines.append(f'  "{filepath}" -> "{dep}";')
    lines.append('}')
    return '\n'.join(lines)
