# ============================================================================
# Zap AST Node Definitions
# Ported from src/ast_nodes.py
# ============================================================================

# Base node
class Node:
  fn init(self, line=0, col=0):
    self.line = line
    self.col = col

# Program
class Program:
  fn init(self, stmts, line=0, col=0):
    self.line = line
    self.col = col
    self.stmts = stmts

# Statements
class LetStmt:
  fn init(self, name, value, type_annotation=none, line=0, col=0):
    self.line = line
    self.col = col
    self.name = name
    self.type_annotation = type_annotation
    self.value = value

class AssignStmt:
  fn init(self, target, value, line=0, col=0):
    self.line = line
    self.col = col
    self.target = target
    self.value = value

class AugAssignStmt:
  fn init(self, target, op, value, line=0, col=0):
    self.line = line
    self.col = col
    self.target = target
    self.op = op
    self.value = value

class ExprStmt:
  fn init(self, expr, line=0, col=0):
    self.line = line
    self.col = col
    self.expr = expr

class Block:
  fn init(self, stmts, line=0, col=0):
    self.line = line
    self.col = col
    self.stmts = stmts

class IfStmt:
  fn init(self, condition, body, else_body=none, line=0, col=0):
    self.line = line
    self.col = col
    self.condition = condition
    self.body = body
    self.else_body = else_body

class ForStmt:
  fn init(self, var, iterable, body, line=0, col=0):
    self.line = line
    self.col = col
    self.var = var
    self.iterable = iterable
    self.body = body

class WhileStmt:
  fn init(self, condition, body, line=0, col=0):
    self.line = line
    self.col = col
    self.condition = condition
    self.body = body

class RetStmt:
  fn init(self, value=none, line=0, col=0):
    self.line = line
    self.col = col
    self.value = value

class BreakStmt:
  fn init(self, line=0, col=0):
    self.line = line
    self.col = col

class ContinueStmt:
  fn init(self, line=0, col=0):
    self.line = line
    self.col = col

# Function definition
class FnDef:
  fn init(self, name, params, body, ret_type=none, is_async=false, line=0, col=0, decorators=none, contracts=none):
    self.line = line
    self.col = col
    self.name = name
    self.params = params
    self.ret_type = ret_type
    self.body = body
    self.is_async = is_async
    self.decorators = decorators or []
    self.contracts = contracts or []

# Contracts
class ContractClause:
  fn init(self, kind, condition, line=0, col=0):
    self.line = line
    self.col = col
    self.kind = kind
    self.condition = condition

class ContractAnnotation:
  fn init(self, kind, condition, line=0, col=0):
    self.line = line
    self.col = col
    self.kind = kind
    self.condition = condition

class Decorator:
  fn init(self, name, args=none, line=0, col=0):
    self.line = line
    self.col = col
    self.name = name
    self.args = args or []

# Class
class ClassDef:
  fn init(self, name, methods, base=none, line=0, col=0):
    self.line = line
    self.col = col
    self.name = name
    self.methods = methods
    self.base = base

# Import
class ImportStmt:
  fn init(self, module, names=none, from_module=none, line=0, col=0):
    self.line = line
    self.col = col
    self.module = module
    self.names = names
    self.from_module = from_module

# Match
class MatchStmt:
  fn init(self, value, cases, line=0, col=0):
    self.line = line
    self.col = col
    self.value = value
    self.cases = cases

# Expressions
class Literal:
  fn init(self, value, line=0, col=0):
    self.line = line
    self.col = col
    self.value = value

class Identifier:
  fn init(self, name, line=0, col=0):
    self.line = line
    self.col = col
    self.name = name

class BinOp:
  fn init(self, left, op, right, line=0, col=0):
    self.line = line
    self.col = col
    self.left = left
    self.op = op
    self.right = right

class UnaryOp:
  fn init(self, op, operand, line=0, col=0):
    self.line = line
    self.col = col
    self.op = op
    self.operand = operand

class Call:
  fn init(self, callee, args, line=0, col=0):
    self.line = line
    self.col = col
    self.callee = callee
    self.args = args

class Index:
  fn init(self, obj, index, line=0, col=0):
    self.line = line
    self.col = col
    self.obj = obj
    self.index = index

class Slice:
  fn init(self, obj, start, stop, step=none, line=0, col=0):
    self.line = line
    self.col = col
    self.obj = obj
    self.start = start
    self.stop = stop
    self.step = step

class MemberAccess:
  fn init(self, obj, member, line=0, col=0):
    self.line = line
    self.col = col
    self.obj = obj
    self.member = member

class ListLiteral:
  fn init(self, elements, line=0, col=0):
    self.line = line
    self.col = col
    self.elements = elements

class DictLiteral:
  fn init(self, entries, line=0, col=0):
    self.line = line
    self.col = col
    self.entries = entries

class TensorLiteral:
  fn init(self, data, shape=none, line=0, col=0):
    self.line = line
    self.col = col
    self.data = data
    self.shape = shape

class Lambda:
  fn init(self, params, body, line=0, col=0):
    self.line = line
    self.col = col
    self.params = params
    self.body = body

class ListComprehension:
  fn init(self, expr, bindings, condition=none, line=0, col=0):
    self.line = line
    self.col = col
    self.expr = expr
    self.bindings = bindings
    self.condition = condition

class DictComprehension:
  fn init(self, key_expr, value_expr, bindings, condition=none, line=0, col=0):
    self.line = line
    self.col = col
    self.key_expr = key_expr
    self.value_expr = value_expr
    self.bindings = bindings
    self.condition = condition

# Native constructs
class ServiceDecl:
  fn init(self, name, methods, exposed=none, metadata=none, svc_version=none, permissions=none, line=0, col=0):
    self.line = line
    self.col = col
    self.name = name
    self.methods = methods
    self.exposed = exposed or []
    self.metadata = metadata or {}
    self.svc_version = svc_version
    self.permissions = permissions or []

class DatabaseDecl:
  fn init(self, name, tables, db_version=none, line=0, col=0):
    self.line = line
    self.col = col
    self.name = name
    self.tables = tables
    self.db_version = db_version

class ApiEndpoint:
  fn init(self, method, path, handler, params=none, ret_val=none, api_version=none, permissions=none, contracts=none, line=0, col=0):
    self.line = line
    self.col = col
    self.method = method
    self.path = path
    self.handler = handler
    self.params = params or []
    self.ret_val = ret_val
    self.api_version = api_version
    self.permissions = permissions or []
    self.contracts = contracts or []

class PageDecl:
  fn init(self, name, route, components, permissions=none, line=0, col=0):
    self.line = line
    self.col = col
    self.name = name
    self.route = route
    self.components = components or []
    self.permissions = permissions or []

class SchemaDecl:
  fn init(self, name, fields, line=0, col=0):
    self.line = line
    self.col = col
    self.name = name
    self.fields = fields

class SchemaField:
  fn init(self, name, field_type, constraints=none, line=0, col=0):
    self.line = line
    self.col = col
    self.name = name
    self.field_type = field_type
    self.constraints = constraints or []

class ModelDecl:
  fn init(self, name, fields, methods=none, line=0, col=0):
    self.line = line
    self.col = col
    self.name = name
    self.fields = fields
    self.methods = methods or []

# AI-native constructs
class PermissionDecl:
  fn init(self, name, description="", line=0, col=0):
    self.line = line
    self.col = col
    self.name = name
    self.description = description

class PermissionBlock:
  fn init(self, permissions, body, line=0, col=0):
    self.line = line
    self.col = col
    self.permissions = permissions
    self.body = body

class ConcurrentBlock:
  fn init(self, branches, line=0, col=0):
    self.line = line
    self.col = col
    self.branches = branches

class ChannelExpr:
  fn init(self, value_type, line=0, col=0):
    self.line = line
    self.col = col
    self.value_type = value_type

class SendStmt:
  fn init(self, chan, value, line=0, col=0):
    self.line = line
    self.col = col
    self.chan = chan
    self.value = value

class RecvExpr:
  fn init(self, chan, line=0, col=0):
    self.line = line
    self.col = col
    self.chan = chan

class SemanticMetadata:
  fn init(self, sections, line=0, col=0):
    self.line = line
    self.col = col
    self.sections = sections

class VersionAnn:
  fn init(self, value, line=0, col=0):
    self.line = line
    self.col = col
    self.value = value

class CheckBlock:
  fn init(self, assertions, line=0, col=0):
    self.line = line
    self.col = col
    self.assertions = assertions

class InvariantStmt:
  fn init(self, condition, line=0, col=0):
    self.line = line
    self.col = col
    self.condition = condition

class ExpectStmt:
  fn init(self, condition, message="", line=0, col=0):
    self.line = line
    self.col = col
    self.condition = condition
    self.message = message

class IntendStmt:
  fn init(self, text, line=0, col=0):
    self.line = line
    self.col = col
    self.text = text

# ============================================================================
# Test AST nodes
# ============================================================================

fn test_ast():
  let lit = Literal(42, 1, 0)
  print("Literal value: " + str(lit.value))
  
  let id = Identifier("x", 1, 0)
  print("Identifier name: " + id.name)
  
  let binop = BinOp(lit, "+", Literal(10, 1, 4), 1, 0)
  print("BinOp left: " + str(binop.left.value))
  
  let let_stmt = LetStmt("x", lit, none, 1, 0)
  print("LetStmt name: " + let_stmt.name)
  
  let fn_def = FnDef("add", ["a", "b"], Block([], 1, 0), none, false, 1, 0)
  print("FnDef name: " + fn_def.name)
  print("FnDef params count: " + str(len(fn_def.params)))
  
  print("AST nodes test passed!")

test_ast()
