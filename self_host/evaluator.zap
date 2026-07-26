# evaluator.zap — Core evaluation loop for Zap
# Handles: let, fn, if, for, while, ret, class, match, try/catch, expressions

import "tokens.zap"
import "ast_nodes.zap"
import "env.zap"
import "builtins.zap"

class ReturnSignal:
  fn init(self, value):
    self.value = value

class BreakSignal:
  fn init(self):
    self.value = none

class ContinueSignal:
  fn init(self):
    self.value = none

class InterpreterError:
  fn init(self, msg, line, col):
    self.msg = msg
    self.line = line
    self.col = col

fn unwrap_list(val):
  if isinstance(val, ZapList):
    ret val.elements
  ret val

fn setup_builtins(env):
  env.define("print", print)
  env.define("len", len)
  env.define("str", str)
  env.define("range", range)
  env.define("int", int)
  env.define("float", float)
  env.define("isinstance", isinstance)
  env.define("abs", abs)
  env.define("max", max)
  env.define("min", min)
  env.define("sum", sum)
  env.define("round", round)
  env.define("ZapList", ZapList)
  env.define("ZapDict", ZapDict)
  env.define("ZapObject", ZapObject)
  env.define("ZapRange", ZapRange)
  env.define("ZapFunction", ZapFunction)
  env.define("ZapBuiltin", ZapBuiltin)
  env.define("ZapType", ZapType)
  print("setup_builtins done, print in env: " + str(env.has_name("print")))

fn evaluate(program, env):
  results = []
  let raw_stmts = program.stmts
  let stmts = unwrap_list(raw_stmts)
  for i in range(len(stmts)):
    let stmt = stmts[i]
    result = eval_stmt(stmt, env)
    if result != none:
      results.append(result)
  ret results

fn eval_stmt(stmt, env):
  if isinstance(stmt, LetStmt):
    value = eval_expr(stmt.value, env)
    env.define(stmt.name, value)
    ret none
  if isinstance(stmt, AssignStmt):
    value = eval_expr(stmt.value, env)
    # Use define for new locals in function scopes, set_value for existing/module
    if env.has_name(stmt.target.name) == false and env.parent != none:
      env.define(stmt.target.name, value)
    el:
      env.set_value(stmt.target.name, value)
    ret none
  if isinstance(stmt, FnDef):
    closure = env.clone()
    env.define(stmt.name, ZapClosure(stmt, closure))
    ret none
  if isinstance(stmt, ClassDef):
    methods = {}
    for method in unwrap_list(stmt.methods):
      methods[method.name] = method
    env.define(stmt.name, ZapClassDef(stmt.name, methods))
    ret none
  if isinstance(stmt, IfStmt):
    cond = eval_expr(stmt.condition, env)
    if is_truthy(cond):
      ret eval_block(stmt.body, env)
    if stmt.else_body != none:
      ret eval_block(stmt.else_body, env)
    ret none
  if isinstance(stmt, ForStmt):
    iterable = eval_expr(stmt.iterable, env)
    items = none
    if isinstance(iterable, ZapList):
      items = unwrap_list(iterable)
    if isinstance(iterable, ZapRange):
      items = iterable._iter()
    if items == none:
      raise InterpreterError("cannot iterate over " + str(type(iterable)), stmt.line, stmt.col)
    for item in items:
      env.define(stmt.var, item)
      try:
        eval_block(stmt.body, env)
      catch sig:
        if isinstance(sig, BreakSignal):
          break
        if isinstance(sig, ContinueSignal):
          continue
        raise sig
    ret none
  if isinstance(stmt, WhileStmt):
    while is_truthy(eval_expr(stmt.condition, env)):
      try:
        eval_block(stmt.body, env)
      catch sig:
        if isinstance(sig, BreakSignal):
          break
        if isinstance(sig, ContinueSignal):
          continue
        raise sig
    ret none
  if isinstance(stmt, RetStmt):
    if stmt.value == none:
      raise ReturnSignal(none)
    value = eval_expr(stmt.value, env)
    raise ReturnSignal(value)
  if isinstance(stmt, BreakStmt):
    raise BreakSignal()
  if isinstance(stmt, ContinueStmt):
    raise ContinueSignal()
  if isinstance(stmt, ExprStmt):
    ret eval_expr(stmt.expr, env)
  if isinstance(stmt, ImportStmt):
    ret do_import(stmt, env)
  if isinstance(stmt, MatchStmt):
    ret eval_match(stmt, env)
  if isinstance(stmt, TryStmt):
    ret eval_try(stmt, env)
  if isinstance(stmt, ThrowStmt):
    value = eval_expr(stmt.value, env)
    raise InterpreterError(str(value), stmt.line, stmt.col)
  ret none

fn do_import(stmt, env):
  module_path = stmt.module
  if isinstance(module_path, str):
    if module_path.startswith('"') and module_path.endswith('"'):
      module_path = module_path[1:-1]
  source = read_file(str(module_path))
  tokens_list = tokenize(source, str(module_path))
  parser = Parser(tokens_list)
  prog = parser.parse()
  evaluate(prog, env)
  ret none

fn eval_block(block, env):
  for s in block.stmts:
    eval_stmt(s, env)
  ret none

fn eval_match(stmt, env):
  value = eval_expr(stmt.value, env)
  for case in unwrap_list(stmt.cases):
    pattern = case.pattern
    body = case.body
    if isinstance(pattern, Identifier) and pattern.name == "_":
      eval_block(body, env)
      ret none
    if isinstance(pattern, Identifier):
      if value != none:
        env.define(pattern.name, value)
        eval_block(body, env)
        ret none
  ret none

fn eval_try(stmt, env):
  try:
    eval_block(stmt.body, env)
  catch sig:
    if isinstance(sig, ReturnSignal):
      raise sig
    if isinstance(sig, BreakSignal):
      raise sig
    if isinstance(sig, ContinueSignal):
      raise sig
    if stmt.catch_body != none:
      if stmt.catch_var != none:
        env.define(stmt.catch_var, sig)
      eval_block(stmt.catch_body, env)
  ret none

fn eval_expr(expr, env):
  if isinstance(expr, Literal):
    ret expr.value
  if isinstance(expr, Identifier):
    value = env.get_value(expr.name)
    if value == none and env.parent != none:
      value = env.parent.get_value(expr.name)
    if value == none:
      raise InterpreterError("NameError: " + expr.name + " is not defined", expr.line, expr.col)
    ret value
  if isinstance(expr, BinOp):
    left = eval_expr(expr.left, env)
    right = eval_expr(expr.right, env)
    ret eval_binop(expr.op, left, right, env)
  if isinstance(expr, UnaryOp):
    operand = eval_expr(expr.operand, env)
    if expr.op == "-":
      ret -operand
    if expr.op == "not":
      ret not is_truthy(operand)
    ret operand
  if isinstance(expr, Call):
    callee = eval_expr(expr.callee, env)
    args = []
    for arg in unwrap_list(expr.args):
      args.append(eval_expr(arg, env))
    ret call_function(callee, args, env)
  if isinstance(expr, MemberAccess):
    obj = eval_expr(expr.obj, env)
    ret get_attr(obj, expr.member)
  if isinstance(expr, Index):
    obj = eval_expr(expr.obj, env)
    idx = eval_expr(expr.index, env)
    ret get_index(obj, idx)
  if isinstance(expr, ListLiteral):
    elements = []
    for elem in unwrap_list(expr.elements):
      elements.append(eval_expr(elem, env))
    ret ZapList(elements)
  if isinstance(expr, DictLiteral):
    entries = {}
    for entry in unwrap_list(expr.entries):
      key = str(eval_expr(entry.key, env))
      value = eval_expr(entry.value, env)
      entries[key] = value
    ret ZapDict(entries)
  if isinstance(expr, Lambda):
    closure = env.clone()
    ret ZapLambda(expr, closure)
  ret none

fn eval_binop(op, left, right, env):
  if op == "+":
    ret left + right
  if op == "-":
    ret left - right
  if op == "*":
    ret left * right
  if op == "/":
    if right == 0:
      raise InterpreterError("ZeroDivisionError: division by zero", 0, 0)
    ret left / right
  if op == "%":
    ret left % right
  if op == "**":
    ret left ** right
  if op == "==":
    ret left == right
  if op == "!=":
    ret left != right
  if op == "<":
    ret left < right
  if op == ">":
    ret left > right
  if op == "<=":
    ret left <= right
  if op == ">=":
    ret left >= right
  if op == "and":
    ret is_truthy(left) and is_truthy(right)
  if op == "or":
    ret is_truthy(left) or is_truthy(right)
  ret none

fn is_truthy(value):
  if value == none:
    ret false
  if isinstance(value, bool):
    ret value
  if isinstance(value, int):
    ret value != 0
  if isinstance(value, float):
    ret value != 0.0
  if isinstance(value, str):
    ret len(value) > 0
  if isinstance(value, ZapList):
    ret len(value.elements) > 0
  if isinstance(value, ZapDict):
    ret len(value.entries) > 0
  ret true

fn call_function(callee, args, env):
  print("CALL_FUNCTION callee=" + str(callee))
  if isinstance(callee, ZapClosure):
    ret call_closure(callee, args, env)
  if isinstance(callee, ZapLambda):
    ret call_lambda(callee, args, env)
  if isinstance(callee, ZapClassDef):
    ret instantiate_class(callee, args, env)
  if isinstance(callee, ZapBuiltin):
    ret call_host_fn(callee, args)
  if isinstance(callee, ZapFunction):
    ret call_host_fn(callee, args)
  raise InterpreterError("TypeError: not callable", 0, 0)

fn call_closure(closure, args, env):
  new_env = Environment(closure.closure)
  func = closure.func
  let params = unwrap_list(func.params)
  for i in range(len(params)):
    param = params[i]
    if isinstance(param, Identifier):
      param_name = param.value
    el:
      param_name = str(param)
    if i < len(args):
      new_env.define(param_name, args[i])
    else:
      new_env.define(param_name, none)
  try:
    eval_block(func.body, new_env)
    ret none
  catch sig:
    if isinstance(sig, ReturnSignal):
      ret sig.value
    raise sig

fn call_lambda(lam, args, env):
  new_env = Environment(lam.closure)
  lambda_fn = lam.lambda_expr
  for i in range(len(lambda_fn.params)):
    param = lambda_fn.params[i]
    if isinstance(param, Identifier):
      param_name = param.value
    el:
      param_name = str(param)
    if i < len(args):
      new_env.define(param_name, args[i])
    else:
      new_env.define(param_name, none)
  ret eval_expr(lambda_fn.body, new_env)

fn instantiate_class(klass, args, env):
  obj_env = Environment(env)
  for attr_name in klass.fields:
    obj_env.define(attr_name, klass.fields[attr_name])
  for method_name in klass.methods:
    obj_env.define(method_name, ZapBoundMethod(klass.methods[method_name], obj_env))
  ret ZapInstance(klass.name, obj_env)

fn get_attr(obj, member):
  if isinstance(obj, ZapInstance) and obj.env.get_value(member) != none:
    ret obj.env.get_value(member)
  raise InterpreterError("AttributeError: " + member + " not found", 0, 0)

fn get_index(obj, idx):
  if isinstance(obj, ZapList):
    if isinstance(idx, ZapValue):
      idx_int = int(idx.value)
    el:
      idx_int = int(idx)
    if idx_int < len(obj.elements):
      ret obj.elements[idx_int]
    ret none
  if isinstance(obj, ZapDict):
    entry = obj.entries.get(str(idx))
    if entry != none:
      ret ZapValue(entry)
    el:
      ret none
  ret none

class ZapClosure:
  fn init(self, func, closure):
    self.func = func
    self.closure = closure

class ZapLambda:
  fn init(self, lambda_expr, closure):
    self.lambda_expr = lambda_expr
    self.closure = closure

class ZapClassDef:
  fn init(self, name, methods, fields=none):
    self.name = name
    self.methods = methods
    self.fields = fields or {}

class ZapBoundMethod:
  fn init(self, method, instance_env):
    self.method = method
    self.instance_env = instance_env

class ZapInstance:
  fn init(self, class_name, env):
    self.class_name = class_name
    self.env = env

class ZapValue:
  fn init(self, value):
    self.value = value
  fn to_string(self):
    ret str(self.value)

class ZapRange:
  fn init(self, start, stop, step=1):
    self.start = start
    self.stop = stop
    self.step = step
  fn _iter(self):
    result = []
    current = self.start
    while current < self.stop:
      result.append(current)
      current = current + self.step
    ret result