from .ast_nodes import *
from .tokens import TokenType
import sys

# ---- Type representation ----

class Type:
    __slots__ = ()
    def is_subtype(self, other): return self == other
    def __repr__(self): return self.__class__.__name__

class AnyType(Type):
    __slots__ = ()
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def is_subtype(self, other): return True
    def __repr__(self): return 'any'
    def __eq__(self, other): return isinstance(other, AnyType)
    def __hash__(self): return hash('any')

class NeverType(Type):
    __slots__ = ()
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def is_subtype(self, other): return True
    def __repr__(self): return 'never'
    def __eq__(self, other): return isinstance(other, NeverType)
    def __hash__(self): return hash('never')

class PrimitiveType(Type):
    __slots__ = ('name',)
    _cache = {}
    def __new__(cls, name):
        if name not in cls._cache:
            obj = super().__new__(cls)
            obj.name = name
            cls._cache[name] = obj
        return cls._cache[name]
    def __init__(self, name):
        pass
    def is_subtype(self, other):
        if isinstance(other, AnyType): return True
        if not isinstance(other, PrimitiveType): return False
        # int < float < complex
        sub_chain = {'int': 'float', 'float': 'complex'}
        cur = self.name
        while cur:
            if cur == other.name: return True
            cur = sub_chain.get(cur)
        return False
    def __repr__(self): return self.name
    def __eq__(self, other):
        return isinstance(other, PrimitiveType) and self.name == other.name
    def __hash__(self): return hash(('prim', self.name))

class FunctionType(Type):
    __slots__ = ('param_types', 'return_type', '_variadic')
    def __init__(self, param_types, return_type):
        self.param_types = tuple(param_types)
        self.return_type = return_type
        self._variadic = False
    def is_subtype(self, other):
        if isinstance(other, AnyType): return True
        if not isinstance(other, FunctionType): return False
        if len(self.param_types) != len(other.param_types): return False
        # contravariant params, covariant return
        for a, b in zip(self.param_types, other.param_types):
            if not b.is_subtype(a): return False
        return self.return_type.is_subtype(other.return_type)
    def __repr__(self):
        params = ', '.join(repr(p) for p in self.param_types)
        return f'({params}) -> {self.return_type}'
    def __eq__(self, other):
        return isinstance(other, FunctionType) and self.param_types == other.param_types and self.return_type == other.return_type
    def __hash__(self): return hash(('fn', self.param_types, self.return_type))

class ListType(Type):
    __slots__ = ('element_type',)
    def __init__(self, element_type):
        self.element_type = element_type
    def is_subtype(self, other):
        if isinstance(other, AnyType): return True
        return isinstance(other, ListType) and self.element_type.is_subtype(other.element_type)
    def __repr__(self): return f'list[{self.element_type}]'
    def __eq__(self, other):
        return isinstance(other, ListType) and self.element_type == other.element_type
    def __hash__(self): return hash(('list', self.element_type))

class DictType(Type):
    __slots__ = ('key_type', 'value_type')
    def __init__(self, key_type, value_type):
        self.key_type = key_type
        self.value_type = value_type
    def is_subtype(self, other):
        if isinstance(other, AnyType): return True
        return isinstance(other, DictType) and self.key_type == other.key_type and self.value_type.is_subtype(other.value_type)
    def __repr__(self): return f'dict[{self.key_type}, {self.value_type}]'
    def __eq__(self, other):
        return isinstance(other, DictType) and self.key_type == other.key_type and self.value_type == other.value_type
    def __hash__(self): return hash(('dict', self.key_type, self.value_type))

class TensorType(Type):
    __slots__ = ('shape', 'element_type')
    def __init__(self, shape, element_type):
        self.shape = tuple(shape) if shape else ()
        self.element_type = element_type
    def is_subtype(self, other):
        if isinstance(other, AnyType): return True
        if not isinstance(other, TensorType): return False
        if self.shape != other.shape: return False
        return self.element_type.is_subtype(other.element_type)
    def __repr__(self): return f'tensor[{self.element_type}]'
    def __eq__(self, other):
        return isinstance(other, TensorType) and self.shape == other.shape and self.element_type == other.element_type
    def __hash__(self): return hash(('tensor', self.shape, self.element_type))

class UnionType(Type):
    __slots__ = ('types',)
    def __init__(self, types):
        flat = []
        for t in types:
            if isinstance(t, UnionType):
                flat.extend(t.types)
            else:
                flat.append(t)
        self.types = tuple(set(flat))
    def is_subtype(self, other):
        if isinstance(other, AnyType): return True
        return all(t.is_subtype(other) for t in self.types)
    def __repr__(self):
        return ' | '.join(repr(t) for t in self.types)
    def __eq__(self, other):
        return isinstance(other, UnionType) and set(self.types) == set(other.types)
    def __hash__(self): return hash(('union', self.types))

class TypeVar(Type):
    __slots__ = ('name', 'constraint')
    def __init__(self, name, constraint=None):
        self.name = name
        self.constraint = constraint
    def is_subtype(self, other):
        if isinstance(other, AnyType): return True
        if self.constraint: return self.constraint.is_subtype(other)
        return True
    def __repr__(self): return self.name
    def __eq__(self, other):
        return isinstance(other, TypeVar) and self.name == other.name
    def __hash__(self): return hash(('tvar', self.name))

# Singletons
ANY = AnyType()
NEVER = NeverType()
INT = PrimitiveType('int')
FLOAT = PrimitiveType('float')
STR = PrimitiveType('str')
BOOL = PrimitiveType('bool')
NONE = PrimitiveType('none')

# String -> Type for type annotations
PARSE_TYPE_MAP = {
    'int': INT, 'float': FLOAT, 'str': STR, 'bool': BOOL, 'none': NONE,
    'any': ANY, 'never': NEVER,
}

def parse_type_annotation(name):
    return PARSE_TYPE_MAP.get(name, ANY)

def type_of_literal(value):
    if isinstance(value, bool): return BOOL
    if isinstance(value, int): return INT
    if isinstance(value, float): return FLOAT
    if isinstance(value, str): return STR
    if value is None: return NONE
    if isinstance(value, list):
        if not value:
            return ListType(ANY)
        elem_types = [type_of_literal(v) for v in value]
        common = common_type(elem_types)
        return ListType(common)
    if isinstance(value, dict):
        if not value:
            return DictType(ANY, ANY)
        key_types = [type_of_literal(k) for k in value]
        val_types = [type_of_literal(v) for v in value.values()]
        return DictType(common_type(key_types), common_type(val_types))
    return ANY

def common_type(types):
    """Find the common supertype of a list of types."""
    if not types:
        return ANY
    result = types[0]
    for t in types[1:]:
        if result.is_subtype(t):
            result = t
        elif not t.is_subtype(result):
            result = ANY
    return result

BUILTIN_TYPES = {
    'int': INT, 'float': FLOAT, 'str': STR, 'bool': BOOL, 'none': NONE,
}

# ---- Type inference and checking ----

class TypeEnv:
    """Typed scope: maps names to (Type, is_mutable)."""
    def __init__(self, parent=None):
        self.bindings = {}
        self.parent = parent

    def get(self, name):
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.get(name)
        return None

    def set(self, name, typ, mutable=True):
        self.bindings[name] = (typ, mutable)

    def enter_scope(self):
        return TypeEnv(parent=self)

    def exit_scope(self):
        return self.parent


class TypeChecker:
    """Walks AST, infers types, collects errors."""

    def __init__(self):
        self.env = TypeEnv()
        self.errors = []  # list of (line, col, message)
        self.fn_return_types = {}  # fn_name -> Type
        self._current_return = None  # expected return type in current fn

        # Seed builtin functions
        self._seed_builtins()

    def _seed_builtins(self):
        # Variadic: param count None means any number of args
        def variadic(ptype, ret):
            ft = FunctionType([ptype], ret)
            ft.param_types = (ptype,)
            ft._variadic = True
            return ft
        builtins = {
            'say': variadic(ANY, NONE),
            'show': variadic(ANY, NONE),
            'print': variadic(ANY, NONE),
            'get': FunctionType([STR], ANY),
            'now': FunctionType([], STR),
            'len': FunctionType([ANY], INT),
            'str': FunctionType([ANY], STR),
            'int': FunctionType([ANY], INT),
            'float': FunctionType([ANY], FLOAT),
            'bool': FunctionType([ANY], BOOL),
            'range': variadic(INT, ListType(INT)),
            'tensor': variadic(ANY, TensorType((), INT)),
            'list': FunctionType([ANY], ListType(ANY)),
            'type': FunctionType([ANY], STR),
            'abs': FunctionType([FLOAT], FLOAT),
            'max': variadic(ANY, ANY),
            'min': variadic(ANY, ANY),
            'sum': FunctionType([ANY], ANY),
            'round': FunctionType([FLOAT], INT),
            'map': variadic(ANY, ListType(ANY)),
            'filter': variadic(ANY, ListType(ANY)),
            'random': FunctionType([], FLOAT),
            'randint': variadic(INT, INT),
            'exp': FunctionType([FLOAT], FLOAT),
            'log': FunctionType([FLOAT], FLOAT),
            'sin': FunctionType([FLOAT], FLOAT),
            'cos': FunctionType([FLOAT], FLOAT),
            'floor': FunctionType([FLOAT], INT),
            'ceil': FunctionType([FLOAT], INT),
            'sqrt': FunctionType([FLOAT], FLOAT),
            'wait': FunctionType([FLOAT], NONE),
            'ask': FunctionType([STR], STR),
            'today': FunctionType([], STR),
            'clear': FunctionType([], NONE),
            'zeros': variadic(INT, TensorType((), INT)),
            'ones': variadic(INT, TensorType((), INT)),
            'reshape': variadic(ANY, TensorType((), INT)),
            'pmap': FunctionType([ANY, ListType(ANY)], ListType(ANY)),
            'parallel': variadic(ANY, ListType(ANY)),
            'retry': FunctionType([ANY, INT, FLOAT], ANY),
            'context_set': FunctionType([STR, ANY], NONE),
            'context_get': FunctionType([STR, ANY], ANY),
            'context_save': FunctionType([], STR),
            'context_intents': FunctionType([], INT),
            'context_add_convention': FunctionType([STR], NONE),
            'context_add_decision': FunctionType([STR], NONE),

            # String operations
            'upper': FunctionType([STR], STR),
            'lower': FunctionType([STR], STR),
            'strip': FunctionType([STR], STR),
            'trim': FunctionType([STR], STR),
            'split': FunctionType([STR, STR], ListType(STR)),
            'join': FunctionType([STR, ListType(ANY)], STR),
            'replace': FunctionType([STR, STR, STR], STR),
            'startswith': FunctionType([STR, STR], BOOL),
            'endswith': FunctionType([STR, STR], BOOL),
            'contains': FunctionType([STR, STR], BOOL),
            'find': FunctionType([STR, STR], INT),
            'reverse': FunctionType([STR], STR),
            'format': FunctionType([STR, DictType(STR, ANY)], STR),

            # File I/O
            'read_file': FunctionType([STR], STR),
            'write_file': FunctionType([STR, STR], BOOL),
            'append_file': FunctionType([STR, STR], BOOL),
            'file_exists': FunctionType([STR], BOOL),
            'list_dir': FunctionType([STR], ListType(STR)),
            'mkdir': FunctionType([STR], BOOL),
            'remove': FunctionType([STR], BOOL),
            'file_size': FunctionType([STR], INT),

            # JSON
            'json_parse': FunctionType([STR], ANY),
            'json_stringify': FunctionType([ANY, INT], STR),

            # HTTP
            'http_get': FunctionType([STR], STR),
            'http_post': FunctionType([STR, STR, STR], STR),

            # Crypto
            'base64_encode': FunctionType([STR], STR),
            'base64_decode': FunctionType([STR], STR),
            'sha256': FunctionType([STR], STR),
            'md5': FunctionType([STR], STR),
            'uuid': FunctionType([], STR),
            'random_string': FunctionType([INT], STR),

            # OS / system
            'env_get': FunctionType([STR, STR], STR),
            'env_set': FunctionType([STR, STR], BOOL),
            'exit': FunctionType([INT], NONE),
            'sleep': FunctionType([FLOAT], BOOL),
            'time': FunctionType([], FLOAT),

            # Collections
            'sort': FunctionType([ListType(ANY), ANY, BOOL], ListType(ANY)),
            'reversed': FunctionType([ListType(ANY)], ListType(ANY)),
            'zip': variadic(ListType(ANY), ListType(ANY)),
            'enumerate': FunctionType([ListType(ANY), INT], ListType(ANY)),
            'flatten': FunctionType([ListType(ANY)], ListType(ANY)),
            'chunk': FunctionType([ListType(ANY), INT], ListType(ANY)),
            'unique': FunctionType([ListType(ANY)], ListType(ANY)),
            'any': FunctionType([ListType(ANY)], BOOL),
            'all': FunctionType([ListType(ANY)], BOOL),

            # Frontend DSL
            'element': FunctionType([STR, DictType(STR, ANY), ANY], STR),
            'html': FunctionType([ANY], STR),
            'render': FunctionType([ANY], STR),
            'html_escape': FunctionType([STR], STR),
            'css': FunctionType([STR], STR),
            'signal': FunctionType([ANY], ANY),
            'effect': FunctionType([ANY, FunctionType([ANY], NONE)], BOOL),

            # Zero-boilerplate
            'config': FunctionType([STR], DictType(STR, ANY)),
            'watch': FunctionType([STR, ANY], BOOL),
            'run': FunctionType([STR, ListType(STR)], STR),
            'http_server': FunctionType([INT, DictType(STR, ANY)], NONE),
            'serve': FunctionType([INT, DictType(STR, ANY)], NONE),

            # Parallel collections
            'par_map': FunctionType([FunctionType([ANY], ANY), ListType(ANY), INT], ListType(ANY)),
            'par_filter': FunctionType([FunctionType([ANY], BOOL), ListType(ANY), INT], ListType(ANY)),
            'par_for': FunctionType([ListType(ANY), FunctionType([ANY], NONE), INT], BOOL),

            # Database / SQLite
            'db_open': FunctionType([STR, STR], BOOL),
            'db_close': FunctionType([STR], BOOL),
            'db_exec': FunctionType([STR, STR, ANY], INT),
            'db_query': FunctionType([STR, STR, ANY], ListType(DictType(STR, ANY))),
            'db_query_one': FunctionType([STR, STR, ANY], DictType(STR, ANY)),
            'db_transaction': FunctionType([STR, FunctionType([], ANY)], ANY),
            'db_migrate': FunctionType([STR, ListType(ANY)], BOOL),
            'db_tables': FunctionType([STR], ListType(STR)),
            'db_schema': FunctionType([STR, STR], ListType(DictType(STR, ANY))),
        }
        for name, typ in builtins.items():
            self.env.set(name, typ, mutable=False)
        # Dict helpers
        self.env.set('has_key', FunctionType([DictType(ANY, ANY), ANY], BOOL), mutable=False)
        # Short aliases
        short_map = {
            'el': 'element', 'rd': 'read_file', 'wr': 'write_file',
            'ap': 'append_file', 'ls': 'list_dir', 'mv': 'remove',
            'sz': 'file_size', 'ex': 'file_exists', 'jp': 'json_parse',
            'js': 'json_stringify', 'sha': 'sha256',
            'b64e': 'base64_encode', 'b64d': 'base64_decode',
            'uid': 'uuid', 'rstr': 'random_string',
            'enc': 'env_get', 'ens': 'env_set',
            'has': 'contains', 'sw': 'startswith', 'ew': 'endswith',
            'trim': 'strip', 'rev': 'reverse',
        }
        for short_name, long_name in short_map.items():
            if long_name in builtins:
                self.env.set(short_name, builtins[long_name], mutable=False)
        self.env.set('True', BOOL, mutable=False)
        self.env.set('False', BOOL, mutable=False)
        self.env.set('result', ANY, mutable=True)  # implicit in ensures clauses

    def error(self, node, msg):
        line = getattr(node, 'line', 0)
        col = getattr(node, 'col', 0)
        self.errors.append((line, col, msg))

    # --- Expression inference ---

    def infer(self, node):
        if isinstance(node, Literal):
            return type_of_literal(node.value)
        if isinstance(node, Identifier):
            binding = self.env.get(node.name)
            if binding is None:
                self.error(node, f"undefined variable '{node.name}'")
                return ANY
            return binding[0]
        if isinstance(node, BinOp):
            return self._infer_binop(node)
        if isinstance(node, UnaryOp):
            return self._infer_unaryop(node)
        if isinstance(node, Call):
            return self._infer_call(node)
        if isinstance(node, Index):
            return self._infer_index(node)
        if isinstance(node, MemberAccess):
            return self._infer_member(node)
        if isinstance(node, ListLiteral):
            if not node.elements:
                return ListType(ANY)
            elem_types = [self.infer(e) for e in node.elements]
            return ListType(common_type(elem_types))
        if isinstance(node, DictLiteral):
            if not node.entries:
                return DictType(ANY, ANY)
            key_types = []
            for k, _ in node.entries:
                if isinstance(k, Identifier):
                    key_types.append(STR)
                else:
                    key_types.append(self.infer(k))
            val_types = [self.infer(v) for _, v in node.entries]
            return DictType(common_type(key_types), common_type(val_types))
        if isinstance(node, Lambda):
            return self._infer_lambda(node)
        if isinstance(node, TensorLiteral):
            return TensorType(node.shape, INT)
        return ANY

    def _infer_binop(self, node):
        lt = self.infer(node.left)
        rt = self.infer(node.right)
        op = node.op

        arithmetic_ops = {'+', '-', '*', '/', '%', '**', '//'}
        comparison_ops = {'==', '!=', '<', '>', '<=', '>=', 'in', 'not in'}
        boolean_ops = {'and', 'or'}
        bitwise_ops = {'&', '|', '^', '<<', '>>'}

        if op in arithmetic_ops:
            if op == '+' and (lt == STR or rt == STR):
                return STR
            if lt.is_subtype(INT) and rt.is_subtype(INT):
                return FLOAT if op == '/' else INT
            if (lt.is_subtype(FLOAT) or lt.is_subtype(INT)) and (rt.is_subtype(FLOAT) or rt.is_subtype(INT)):
                return FLOAT
            self.error(node, f"unsupported operand type(s) for {op}: {lt} and {rt}")
            return ANY
        if op in comparison_ops:
            if not self._compatible(lt, rt):
                self.error(node, f"cannot compare {lt} and {rt}")
            return BOOL
        if op in boolean_ops:
            return BOOL
        if op in bitwise_ops:
            if lt.is_subtype(INT) and rt.is_subtype(INT):
                return INT
            self.error(node, f"unsupported operand type(s) for {op}: {lt} and {rt}")
            return ANY
        if op == '.':
            return ANY  # member access, handled separately
        if op == '[':
            return ANY  # index, handled separately
        return ANY

    def _infer_unaryop(self, node):
        ot = self.infer(node.operand)
        if node.op == '-':
            if ot.is_subtype(INT) or ot.is_subtype(FLOAT):
                return ot
            self.error(node, f"bad operand type for unary -: {ot}")
            return ANY
        if node.op == 'not':
            return BOOL
        return ot

    def _infer_call(self, node):
        callee_type = self.infer(node.callee)
        if isinstance(callee_type, FunctionType):
            variadic = getattr(callee_type, '_variadic', False)
            min_params = len(callee_type.param_types)
            if variadic:
                if len(node.args) < 1:
                    self.error(node, "expected at least 1 argument")
                    return ANY
                elem_type = callee_type.param_types[0]
                for arg in node.args:
                    arg_type = self.infer(arg)
                    if not arg_type.is_subtype(elem_type):
                        self.error(arg, f"expected {elem_type}, got {arg_type}")
            elif min_params == 2 and len(node.args) == 1:
                # Allow 1-arg calls for range, map, filter etc.
                arg_type = self.infer(node.args[0])
                if not arg_type.is_subtype(callee_type.param_types[0]):
                    self.error(node.args[0], f"expected {callee_type.param_types[0]}, got {arg_type}")
            else:
                if len(node.args) != min_params:
                    self.error(node, f"expected {min_params} args, got {len(node.args)}")
                    return ANY
                for i, (arg, ptype) in enumerate(zip(node.args, callee_type.param_types)):
                    arg_type = self.infer(arg)
                    if not arg_type.is_subtype(ptype):
                        self.error(arg, f"expected {ptype}, got {arg_type}")
            return callee_type.return_type
        self.error(node, f"'{callee_type}' is not callable")
        return ANY

    def _infer_index(self, node):
        obj_type = self.infer(node.obj)
        if isinstance(obj_type, ListType):
            idx_type = self.infer(node.index)
            if not idx_type.is_subtype(INT):
                self.error(node.index, f"list index must be int, got {idx_type}")
            return obj_type.element_type
        if isinstance(obj_type, DictType):
            idx_type = self.infer(node.index)
            if not idx_type.is_subtype(obj_type.key_type):
                self.error(node.index, f"dict key must be {obj_type.key_type}, got {idx_type}")
            return obj_type.value_type
        if isinstance(obj_type, PrimitiveType) and obj_type.name == 'str':
            return STR
        self.error(node, f"cannot index {obj_type}")
        return ANY

    def _infer_member(self, node):
        obj_type = self.infer(node.obj)
        if isinstance(obj_type, TensorType) and node.member == 'shape':
            return ListType(INT)
        return ANY

    def _infer_lambda(self, node):
        inner = self.env.enter_scope()
        old_env, self.env = self.env, inner
        param_types = []
        for p in node.params:
            pt = parse_type_annotation(p.get('type')) if p.get('type') else ANY
            param_types.append(pt)
            self.env.set(p['name'], pt, mutable=False)
        body_type = self.infer(node.body)
        self.env = old_env
        return FunctionType(param_types, body_type)

    def _compatible(self, a, b):
        return a.is_subtype(b) or b.is_subtype(a)

    # --- Statement checking ---

    def check(self, node):
        if isinstance(node, Program):
            for stmt in node.stmts:
                self.check(stmt)
        elif isinstance(node, LetStmt):
            self._check_let(node)
        elif isinstance(node, AssignStmt):
            self._check_assign(node)
        elif isinstance(node, AugAssignStmt):
            self._check_aug_assign(node)
        elif isinstance(node, ExprStmt):
            self.infer(node.expr)
        elif isinstance(node, IfStmt):
            cond_type = self.infer(node.condition)
            self.check(node.body)
            if node.else_body:
                self.check(node.else_body)
        elif isinstance(node, ForStmt):
            iter_type = self.infer(node.iterable)
            inner = self.env.enter_scope()
            old_env, self.env = self.env, inner
            if isinstance(iter_type, ListType):
                self.env.set(node.var, iter_type.element_type, mutable=True)
            elif isinstance(iter_type, PrimitiveType) and iter_type.name == 'str':
                self.env.set(node.var, STR, mutable=True)
            elif isinstance(iter_type, DictType):
                self.env.set(node.var, iter_type.key_type, mutable=True)
            else:
                self.env.set(node.var, ANY, mutable=True)
            self.check(node.body)
            self.env = old_env
        elif isinstance(node, WhileStmt):
            cond_type = self.infer(node.condition)
            self.check(node.body)
        elif isinstance(node, RetStmt):
            if node.value:
                ret_type = self.infer(node.value)
                if self._current_return and not ret_type.is_subtype(self._current_return):
                    self.error(node, f"expected return {self._current_return}, got {ret_type}")
            elif self._current_return and self._current_return != NONE:
                self.error(node, f"expected return {self._current_return}, got none")
        elif isinstance(node, FnDef):
            self._check_fn(node)
        elif isinstance(node, Block):
            inner = self.env.enter_scope()
            old_env, self.env = self.env, inner
            for stmt in node.stmts:
                self.check(stmt)
            self.env = old_env
        elif isinstance(node, ImportStmt):
            pass
        elif isinstance(node, MatchStmt):
            val_type = self.infer(node.value)
            for pattern, body in node.cases:
                self.check(body)
        elif isinstance(node, ClassDef):
            self.env.set(node.name, ANY, mutable=False)
            for m in node.methods:
                self.check(m)
        elif isinstance(node, ServiceDecl):
            for m in node.methods:
                self.check(m)
        elif isinstance(node, DatabaseDecl):
            for t in node.tables:
                self.check(t)
        elif isinstance(node, SchemaDecl):
            for f in node.fields:
                self.check(f)
        elif isinstance(node, ModelDecl):
            for f in node.fields:
                self.check(f)
            for m in node.methods:
                self.check(m)
        elif isinstance(node, ApiEndpoint):
            pass
        elif isinstance(node, PageDecl):
            pass
        elif isinstance(node, ConcurrentBlock):
            for branch in node.branches:
                self.check(branch)
        elif isinstance(node, CheckBlock):
            for a in node.assertions:
                self.infer(a)
        elif isinstance(node, PermissionBlock):
            self.check(node.body)
        elif isinstance(node, InvariantStmt):
            self.infer(node.condition)
        elif isinstance(node, ExpectStmt):
            self.infer(node.condition)
        elif isinstance(node, IntendStmt):
            pass
        elif isinstance(node, ContractClause):
            self.infer(node.condition)
        elif isinstance(node, ContractAnnotation):
            self.infer(node.condition)

    def _check_let(self, node):
        if node.value:
            val_type = self.infer(node.value)
            if node.type_annotation:
                ann_type = parse_type_annotation(node.type_annotation)
                if not val_type.is_subtype(ann_type):
                    self.error(node, f"expected {ann_type}, got {val_type}")
                self.env.set(node.name, ann_type, mutable=True)
            else:
                self.env.set(node.name, val_type, mutable=True)
        else:
            ann_type = parse_type_annotation(node.type_annotation) if node.type_annotation else ANY
            self.env.set(node.name, ann_type, mutable=True)

    def _check_assign(self, node):
        val_type = self.infer(node.value)
        if isinstance(node.target, Identifier):
            binding = self.env.get(node.target.name)
            if binding is None:
                # Implicit declaration (Zap allows x = 5 without let)
                self.env.set(node.target.name, val_type, mutable=True)
                return
            if not binding[1]:
                self.error(node, f"cannot assign to immutable '{node.target.name}'")
                return
            if not val_type.is_subtype(binding[0]):
                self.error(node, f"cannot assign {val_type} to {binding[0]}")
        elif isinstance(node.target, Index):
            obj_type = self.infer(node.target.obj)
            if isinstance(obj_type, ListType) and not val_type.is_subtype(obj_type.element_type):
                self.error(node, f"list element expected {obj_type.element_type}, got {val_type}")
        elif isinstance(node.target, MemberAccess):
            obj_type = self.infer(node.target.obj)
            if isinstance(obj_type, TensorType) and node.target.member == 'data':
                pass

    def _check_aug_assign(self, node):
        val_type = self.infer(node.value)
        target = node.target
        if isinstance(target, Identifier):
            binding = self.env.get(target.name)
            if binding is None:
                self.env.set(target.name, val_type, mutable=True)
                return
            if not val_type.is_subtype(binding[0]):
                self.error(node, f"type mismatch in {node.op}=: {val_type} vs {binding[0]}")

    def _check_fn(self, node):
        inner = self.env.enter_scope()
        old_env, self.env = self.env, inner
        old_ret = self._current_return

        self._current_return = parse_type_annotation(node.return_type) if node.return_type else ANY

        for p in node.params:
            pt = parse_type_annotation(p.get('type')) if p.get('type') else ANY
            self.env.set(p['name'], pt, mutable=False)

        for c in node.contracts:
            self.check(c)

        self.check(node.body)

        self._current_return = old_ret
        self.env = old_env

        fn_type = FunctionType(
            [parse_type_annotation(p.get('type')) if p.get('type') else ANY for p in node.params],
            parse_type_annotation(node.return_type) if node.return_type else ANY
        )
        self.env.set(node.name, fn_type, mutable=False)
