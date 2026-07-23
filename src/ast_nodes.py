class Node:
    __slots__ = ('line', 'col')
    def __init__(self, line, col):
        self.line = line
        self.col = col

class Program(Node):
    __slots__ = ('stmts',)
    def __init__(self, stmts, line=0, col=0):
        super().__init__(line, col)
        self.stmts = stmts
    def __repr__(self): return f"Program(...{len(self.stmts)} stmts)"

class LetStmt(Node):
    __slots__ = ('name', 'type_annotation', 'value')
    def __init__(self, name, value, type_annotation=None, line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.type_annotation = type_annotation
        self.value = value

class AssignStmt(Node):
    __slots__ = ('target', 'value')
    def __init__(self, target, value, line=0, col=0):
        super().__init__(line, col)
        self.target = target
        self.value = value

class AugAssignStmt(Node):
    __slots__ = ('target', 'op', 'value')
    def __init__(self, target, op, value, line=0, col=0):
        super().__init__(line, col)
        self.target = target
        self.op = op
        self.value = value

class ExprStmt(Node):
    __slots__ = ('expr',)
    def __init__(self, expr, line=0, col=0):
        super().__init__(line, col)
        self.expr = expr

class Block(Node):
    __slots__ = ('stmts',)
    def __init__(self, stmts, line=0, col=0):
        super().__init__(line, col)
        self.stmts = stmts

class IfStmt(Node):
    __slots__ = ('condition', 'body', 'else_body')
    def __init__(self, condition, body, else_body=None, line=0, col=0):
        super().__init__(line, col)
        self.condition = condition
        self.body = body
        self.else_body = else_body

class ForStmt(Node):
    __slots__ = ('var', 'iterable', 'body')
    def __init__(self, var, iterable, body, line=0, col=0):
        super().__init__(line, col)
        self.var = var
        self.iterable = iterable
        self.body = body

class WhileStmt(Node):
    __slots__ = ('condition', 'body')
    def __init__(self, condition, body, line=0, col=0):
        super().__init__(line, col)
        self.condition = condition
        self.body = body

class RetStmt(Node):
    __slots__ = ('value',)
    def __init__(self, value=None, line=0, col=0):
        super().__init__(line, col)
        self.value = value

class BreakStmt(Node):
    __slots__ = ()
    def __init__(self, line=0, col=0):
        super().__init__(line, col)

class ContinueStmt(Node):
    __slots__ = ()
    def __init__(self, line=0, col=0):
        super().__init__(line, col)

class FnDef(Node):
    __slots__ = ('name', 'params', 'return_type', 'body', 'is_async', 'decorators', 'contracts')
    def __init__(self, name, params, body, return_type=None, is_async=False, line=0, col=0,
                 decorators=None, contracts=None):
        super().__init__(line, col)
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body
        self.is_async = is_async
        self.decorators = decorators or []
        self.contracts = contracts or []

class ContractClause(Node):
    """requires condition / ensures condition — inside fn body before statements."""
    __slots__ = ('kind', 'condition')
    def __init__(self, kind, condition, line=0, col=0):
        super().__init__(line, col)
        self.kind = kind  # 'requires' or 'ensures'
        self.condition = condition

class ContractAnnotation(Node):
    """@requires(cond) / @ensures(cond) — decorator-style contracts."""
    __slots__ = ('kind', 'condition')
    def __init__(self, kind, condition, line=0, col=0):
        super().__init__(line, col)
        self.kind = kind
        self.condition = condition

class Decorator(Node):
    __slots__ = ('name', 'args')
    def __init__(self, name, args=None, line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.args = args or []

class ClassDef(Node):
    __slots__ = ('name', 'methods', 'base')
    def __init__(self, name, methods, base=None, line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.methods = methods
        self.base = base

class ImportStmt(Node):
    __slots__ = ('module', 'names', 'from_module')
    def __init__(self, module, names=None, from_module=None, line=0, col=0):
        super().__init__(line, col)
        self.module = module
        self.names = names
        self.from_module = from_module

class MatchStmt(Node):
    __slots__ = ('value', 'cases')
    def __init__(self, value, cases, line=0, col=0):
        super().__init__(line, col)
        self.value = value
        self.cases = cases

class Literal(Node):
    __slots__ = ('value',)
    def __init__(self, value, line=0, col=0):
        super().__init__(line, col)
        self.value = value

class Identifier(Node):
    __slots__ = ('name',)
    def __init__(self, name, line=0, col=0):
        super().__init__(line, col)
        self.name = name

class BinOp(Node):
    __slots__ = ('left', 'op', 'right')
    def __init__(self, left, op, right, line=0, col=0):
        super().__init__(line, col)
        self.left = left
        self.op = op
        self.right = right

class UnaryOp(Node):
    __slots__ = ('op', 'operand')
    def __init__(self, op, operand, line=0, col=0):
        super().__init__(line, col)
        self.op = op
        self.operand = operand

class Call(Node):
    __slots__ = ('callee', 'args')
    def __init__(self, callee, args, line=0, col=0):
        super().__init__(line, col)
        self.callee = callee
        self.args = args

class Index(Node):
    __slots__ = ('obj', 'index')
    def __init__(self, obj, index, line=0, col=0):
        super().__init__(line, col)
        self.obj = obj
        self.index = index

class Slice(Node):
    __slots__ = ('obj', 'start', 'stop', 'step')
    def __init__(self, obj, start, stop, step=None, line=0, col=0):
        super().__init__(line, col)
        self.obj = obj
        self.start = start
        self.stop = stop
        self.step = step

class MemberAccess(Node):
    __slots__ = ('obj', 'member')
    def __init__(self, obj, member, line=0, col=0):
        super().__init__(line, col)
        self.obj = obj
        self.member = member

class ListLiteral(Node):
    __slots__ = ('elements',)
    def __init__(self, elements, line=0, col=0):
        super().__init__(line, col)
        self.elements = elements

class DictLiteral(Node):
    __slots__ = ('entries',)
    def __init__(self, entries, line=0, col=0):
        super().__init__(line, col)
        self.entries = entries

class TensorLiteral(Node):
    __slots__ = ('data', 'shape')
    def __init__(self, data, shape=None, line=0, col=0):
        super().__init__(line, col)
        self.data = data
        self.shape = shape

class Lambda(Node):
    __slots__ = ('params', 'body')
    def __init__(self, params, body, line=0, col=0):
        super().__init__(line, col)
        self.params = params
        self.body = body

class ListComprehension(Node):
    """[expr for item in iterable] or [expr for item in iterable if condition]"""
    __slots__ = ('expr', 'bindings', 'condition')
    def __init__(self, expr, bindings, condition=None, line=0, col=0):
        super().__init__(line, col)
        self.expr = expr
        self.bindings = bindings  # list of (var, iterable) tuples
        self.condition = condition

class DictComprehension(Node):
    """{key: value for item in iterable}"""
    __slots__ = ('key_expr', 'value_expr', 'bindings', 'condition')
    def __init__(self, key_expr, value_expr, bindings, condition=None, line=0, col=0):
        super().__init__(line, col)
        self.key_expr = key_expr
        self.value_expr = value_expr
        self.bindings = bindings
        self.condition = condition

# ---- Native constructs ----

class ServiceDecl(Node):
    __slots__ = ('name', 'methods', 'expose', 'metadata', 'version', 'permissions')
    def __init__(self, name, methods, expose=None, metadata=None, version=None,
                 permissions=None, line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.methods = methods
        self.expose = expose or []
        self.metadata = metadata or {}  # {'requires': [...], 'guarantees': [...]}
        self.version = version
        self.permissions = permissions or []

class DatabaseDecl(Node):
    __slots__ = ('name', 'tables', 'version')
    def __init__(self, name, tables, version=None, line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.tables = tables
        self.version = version

class ApiEndpoint(Node):
    __slots__ = ('method', 'path', 'handler', 'params', 'returns', 'version', 'permissions', 'contracts')
    def __init__(self, method, path, handler, params=None, returns=None, version=None,
                 permissions=None, contracts=None, line=0, col=0):
        super().__init__(line, col)
        self.method = method
        self.path = path
        self.handler = handler
        self.params = params or []
        self.returns = returns
        self.version = version
        self.permissions = permissions or []
        self.contracts = contracts or []

class PageDecl(Node):
    __slots__ = ('name', 'route', 'components', 'permissions')
    def __init__(self, name, route, components, permissions=None, line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.route = route
        self.components = components or []
        self.permissions = permissions or []

class SchemaDecl(Node):
    __slots__ = ('name', 'fields')
    def __init__(self, name, fields, line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.fields = fields

class SchemaField(Node):
    __slots__ = ('name', 'field_type', 'constraints')
    def __init__(self, name, field_type, constraints=None, line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.field_type = field_type
        self.constraints = constraints or []

class ModelDecl(Node):
    __slots__ = ('name', 'fields', 'methods')
    def __init__(self, name, fields, methods=None, line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.fields = fields
        self.methods = methods or []

# ---- AI-native constructs ----

class PermissionDecl(Node):
    """permission filesystem.read — declare a capability."""
    __slots__ = ('name', 'description')
    def __init__(self, name, description='', line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.description = description

class PermissionBlock(Node):
    """with perm_a, perm_b: ... — scoped permission grant."""
    __slots__ = ('permissions', 'body')
    def __init__(self, permissions, body, line=0, col=0):
        super().__init__(line, col)
        self.permissions = permissions  # list of strings
        self.body = body

class ConcurrentBlock(Node):
    """concurrent: ... — structured concurrency."""
    __slots__ = ('branches',)
    def __init__(self, branches, line=0, col=0):
        super().__init__(line, col)
        self.branches = branches  # list of Block

class ChannelExpr(Node):
    """channel(type) — create a channel."""
    __slots__ = ('value_type',)
    def __init__(self, value_type, line=0, col=0):
        super().__init__(line, col)
        self.value_type = value_type

class SendStmt(Node):
    """chan <- value — send to channel."""
    __slots__ = ('channel', 'value')
    def __init__(self, channel, value, line=0, col=0):
        super().__init__(line, col)
        self.channel = channel
        self.value = value

class RecvExpr(Node):
    """<- chan — receive from channel."""
    __slots__ = ('channel',)
    def __init__(self, channel, line=0, col=0):
        super().__init__(line, col)
        self.channel = channel

class SemanticMetadata(Node):
    """requires: / guarantees: blocks on service/database/api/page."""
    __slots__ = ('sections',)
    def __init__(self, sections, line=0, col=0):
        super().__init__(line, col)
        self.sections = sections  # list of (kind, [conditions])

class VersionAnn(Node):
    """version "1.0.0" annotation."""
    __slots__ = ('value',)
    def __init__(self, value, line=0, col=0):
        super().__init__(line, col)
        self.value = value  # string like "1.0.0"

class CheckBlock(Node):
    """check: ... — compile-time validation block."""
    __slots__ = ('assertions',)
    def __init__(self, assertions, line=0, col=0):
        super().__init__(line, col)
        self.assertions = assertions  # list of expressions to verify

class InvariantStmt(Node):
    """invariant condition — class/module invariant."""
    __slots__ = ('condition',)
    def __init__(self, condition, line=0, col=0):
        super().__init__(line, col)
        self.condition = condition

class ExpectStmt(Node):
    """expect condition — test assertion."""
    __slots__ = ('condition', 'message')
    def __init__(self, condition, message='', line=0, col=0):
        super().__init__(line, col)
        self.condition = condition
        self.message = message

class IntendStmt(Node):
    __slots__ = ('text',)
    def __init__(self, text, line=0, col=0):
        super().__init__(line, col)
        self.text = text
