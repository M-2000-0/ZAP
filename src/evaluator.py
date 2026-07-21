import time
from concurrent.futures import ThreadPoolExecutor
from .ast_nodes import *
from .environment import Environment
from .values import *
from .context import get_context, save_context
from .tracer import trace, get_tracer

class Evaluator:
    _current = None

    def __init__(self, is_main=True, current_file=None):
        self.global_env = make_zap_builtins()
        self.env = self.global_env
        self.distributed_pool = None
        self._current_file = current_file
        if is_main:
            Evaluator._current = self

    def evaluate(self, node):
        if isinstance(node, Program):
            return self._eval_program(node)
        raise RuntimeError(f"cannot evaluate {type(node).__name__} at top level")

    def _eval_program(self, node):
        result = None
        for stmt in node.stmts:
            try:
                result = self._eval_stmt(stmt)
            except Exception as e:
                trace('error', '<program>', {'error': str(e)[:200], 'stmt': type(stmt).__name__})
                raise
        return result

    def _eval_stmt(self, stmt):
        if isinstance(stmt, ExprStmt):
            return self._eval_expr(stmt.expr)
        if isinstance(stmt, LetStmt):
            return self._eval_let(stmt)
        if isinstance(stmt, AssignStmt):
            return self._eval_assign(stmt)
        if isinstance(stmt, AugAssignStmt):
            return self._eval_aug_assign(stmt)
        if isinstance(stmt, RetStmt):
            val = self._eval_expr(stmt.value) if stmt.value else None
            raise ReturnSignal(val)
        if isinstance(stmt, IfStmt):
            return self._eval_if(stmt)
        if isinstance(stmt, ForStmt):
            return self._eval_for(stmt)
        if isinstance(stmt, WhileStmt):
            return self._eval_while(stmt)
        if isinstance(stmt, Block):
            return self._eval_block(stmt)
        if isinstance(stmt, FnDef):
            return self._eval_fn_def(stmt)
        if isinstance(stmt, ClassDef):
            return self._eval_class_def(stmt)
        if isinstance(stmt, ImportStmt):
            return self._eval_import(stmt)
        if isinstance(stmt, MatchStmt):
            return self._eval_match(stmt)
        if isinstance(stmt, IntendStmt):
            return self._eval_intend(stmt)
        if isinstance(stmt, ServiceDecl):
            return self._eval_service(stmt)
        if isinstance(stmt, DatabaseDecl):
            return self._eval_database(stmt)
        if isinstance(stmt, ApiEndpoint):
            return self._eval_api(stmt)
        if isinstance(stmt, PageDecl):
            return self._eval_page(stmt)
        if isinstance(stmt, SchemaDecl):
            return self._eval_schema(stmt)
        if isinstance(stmt, ModelDecl):
            return self._eval_model(stmt)
        if isinstance(stmt, PermissionDecl):
            return self._eval_permission(stmt)
        if isinstance(stmt, ConcurrentBlock):
            return self._eval_concurrent(stmt)
        if isinstance(stmt, CheckBlock):
            return self._eval_check(stmt)
        if isinstance(stmt, InvariantStmt):
            return self._eval_invariant(stmt)
        if isinstance(stmt, ExpectStmt):
            return self._eval_expect(stmt)
        if isinstance(stmt, ContractClause):
            # Handled inside fn body, not as standalone stmt
            return None
        raise RuntimeError(f"unknown statement: {type(stmt).__name__}")

    def _eval_block(self, block):
        env = Environment(self.env)
        prev = self.env
        self.env = env
        result = None
        try:
            for stmt in block.stmts:
                result = self._eval_stmt(stmt)
                if isinstance(result, ReturnSignal):
                    return result
        finally:
            self.env = prev
        return result

    def _eval_let(self, stmt):
        value = self._eval_expr(stmt.value) if stmt.value else None
        self.env.define(stmt.name, value)
        trace('assign', f"let {stmt.name}", {'name': stmt.name, 'value': repr(value)[:100]})
        return value

    def _eval_assign(self, stmt):
        value = self._eval_expr(stmt.value)
        target_name = None
        if isinstance(stmt.target, Identifier):
            self.env.set(stmt.target.name, value)
            target_name = stmt.target.name
        elif isinstance(stmt.target, MemberAccess):
            obj = self._eval_expr(stmt.target.obj)
            if isinstance(obj, ZapObject):
                obj.fields[stmt.target.member] = value
            elif isinstance(obj, ZapDict):
                obj.entries[stmt.target.member] = value
            target_name = f"{stmt.target.obj}.{stmt.target.member}"
        elif isinstance(stmt.target, Index):
            obj = self._eval_expr(stmt.target.obj)
            idx = self._eval_expr(stmt.target.index)
            if isinstance(obj, ZapList):
                obj.elements[idx] = value
            elif isinstance(obj, ZapTensor):
                obj.data[idx] = value
            elif isinstance(obj, ZapDict):
                obj.entries[idx] = value
            elif isinstance(obj, list):
                obj[idx] = value
            target_name = f"{stmt.target.obj}[{idx}]"
        trace('assign', target_name or 'unknown', {'name': target_name, 'value': repr(value)[:100]})
        return value

    def _eval_aug_assign(self, stmt):
        target = stmt.target
        cur = self._eval_expr(target)
        val = self._eval_expr(stmt.value)
        if stmt.op == '+=':
            result = cur + val
        elif stmt.op == '-=':
            result = cur - val
        else:
            raise RuntimeError(f"unknown augop: {stmt.op}")
        if isinstance(target, Identifier):
            self.env.set(target.name, result)
        return result

    def _eval_if(self, stmt):
        cond = self._eval_expr(stmt.condition)
        if self._is_truthy(cond):
            return self._eval_block(stmt.body)
        elif stmt.else_body:
            if isinstance(stmt.else_body, IfStmt):
                return self._eval_if(stmt.else_body)
            return self._eval_block(stmt.else_body)
        return None

    def _eval_for(self, stmt):
        iterable = self._eval_expr(stmt.iterable)
        result = None
        items = self._iterable_to_list(iterable)
        first = True
        for item in items:
            if first:
                self.env.define(stmt.var, item)
                first = False
            else:
                self.env.set(stmt.var, item)
            r = self._eval_block(stmt.body)
            if isinstance(r, ReturnSignal):
                return r
            if r is not None:
                result = r
        return result

    def _eval_while(self, stmt):
        result = None
        while self._is_truthy(self._eval_expr(stmt.condition)):
            r = self._eval_block(stmt.body)
            if isinstance(r, ReturnSignal):
                return r
            if r is not None:
                result = r
        return result

    def _eval_fn_def(self, stmt):
        fn = ZapFunction(stmt.name, stmt.params, stmt.body, self.env,
                        stmt.return_type, stmt.is_async,
                        decorators=stmt.decorators, contracts=stmt.contracts)
        self.env.define(stmt.name, fn)
        for dec in stmt.decorators:
            dec_args = [self._eval_expr(a) for a in dec.args]
            if dec.name == 'retry':
                self._apply_retry(fn, dec_args)
            elif dec.name == 'fallback':
                self._apply_fallback(fn, dec_args)
            elif dec.name == 'distributed':
                self._apply_distributed(fn, dec_args)
        return None

    def _apply_retry(self, fn, args):
        max_retries = args[0] if args else 3
        delay = args[1] if len(args) > 1 else 0
        orig_call = fn._call
        def retry_wrapper(*call_args):
            last_err = None
            for attempt in range(int(max_retries) + 1):
                try:
                    result = orig_call(*call_args)
                    if attempt > 0:
                        trace('retry', fn.name, {'attempt': attempt, 'status': 'success'})
                    return result
                except Exception as e:
                    last_err = e
                    trace('retry', fn.name, {'attempt': attempt, 'status': 'failed', 'error': str(e)[:200]})
                    if attempt < int(max_retries):
                        if delay:
                            __import__('time').sleep(float(delay))
            raise last_err
        fn._call = retry_wrapper

    def _apply_fallback(self, fn, args):
        fallback_name = str(args[0]) if args else None
        orig_call = fn._call
        def fallback_wrapper(*call_args):
            try:
                return orig_call(*call_args)
            except Exception as e:
                trace('fallback', fn.name, {
                    'error': str(e)[:200],
                    'fallback_fn': fallback_name,
                })
                if fallback_name:
                    fb_fn = self.env.get(fallback_name)
                    if isinstance(fb_fn, ZapFunction):
                        return fb_fn._call(*call_args)
                    if callable(fb_fn):
                        return fb_fn(*call_args)
                return None
        fn._call = fallback_wrapper

    def _apply_distributed(self, fn, args):
        if self.distributed_pool is None:
            self.distributed_pool = ThreadPoolExecutor()
        orig_call = fn._call
        def distributed_wrapper(*call_args):
            trace('distributed_start', fn.name, {'arg_count': len(call_args)})
            future = self.distributed_pool.submit(orig_call, *call_args)
            future.add_done_callback(
                lambda f: trace('distributed_end', fn.name, {
                    'success': not f.exception(),
                    'error': str(f.exception())[:200] if f.exception() else None,
                })
            )
            return future
        fn._call = distributed_wrapper

    def _eval_class_def(self, stmt):
        methods = {}
        for method in stmt.methods:
            fn = ZapFunction(method.name, method.params, method.body,
                           self.env, method.return_type, method.is_async, is_method=True)
            methods[method.name] = fn
        base = None
        if stmt.base:
            base = self.env.get(stmt.base)
        obj = ZapObject(methods=methods, base=base)
        self.env.define(stmt.name, obj)
        if 'init' in methods:
            def constructor(*args):
                instance = ZapObject(base=obj)
                instance.fields['self'] = instance
                instance.methods = dict(obj.methods)
                init_fn = instance.methods.get('init')
                if init_fn:
                    call_env = Environment(init_fn.closure)
                    call_env.define('self', instance)
                    for i, param in enumerate(init_fn.params):
                        if i == 0 and param['name'] == 'self':
                            continue
                        val = args[i - 1] if i - 1 < len(args) else param.get('default')
                        call_env.define(param['name'], val)
                    prev = self.env
                    self.env = call_env
                    try:
                        self._eval_block(init_fn.body)
                    finally:
                        self.env = prev
                return instance
            self.env.define(stmt.name, ZapBuiltin(constructor, stmt.name))
        return None

    def _eval_import(self, stmt):
        if stmt.from_module:
            try:
                py_mod = __import__(stmt.from_module)
                for name in stmt.names:
                    attr = getattr(py_mod, name, None)
                    if attr is not None:
                        self.env.define(name, attr)
            except ImportError:
                raise ImportError(f"cannot import '{stmt.from_module}'")
        elif stmt.module:
            self._eval_zap_import(stmt)
        return None

    def _eval_zap_import(self, stmt):
        import os as _os
        module_path = stmt.module
        # Handle both "lib/strings.zap" and "lib.strings" paths
        if not module_path.endswith('.zap'):
            module_path = module_path.replace('.', '/') + '.zap'

        search_dirs = ['.']
        if self._current_file:
            search_dirs.insert(0, _os.path.dirname(self._current_file))

        resolved = None
        for d in search_dirs:
            candidate = _os.path.join(d, module_path) if d != '.' else module_path
            if _os.path.exists(candidate):
                resolved = candidate
                break

        if resolved is None:
            raise ImportError(f"cannot find module '{stmt.module}'")

        with open(resolved, 'r', encoding='utf-8') as f:
            text = f.read()

        from .lexer import Lexer
        from .parser import Parser
        lexer = Lexer(text, resolved)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        prog = parser.parse()

        prev_file = getattr(self, '_current_file', None)
        self._current_file = resolved
        try:
            self._eval_program(prog)
        finally:
            self._current_file = prev_file

    def _eval_match(self, stmt):
        value = self._eval_expr(stmt.value)
        for pattern, body in stmt.cases:
            if pattern == '_':
                return self._eval_block(body)
            pat_val = self._eval_expr(pattern)
            if value == pat_val:
                return self._eval_block(body)
        return None

    def _eval_intend(self, stmt):
        ctx = get_context()
        ctx.add_intent(stmt.text)
        save_context()
        return None

    def _eval_service(self, stmt):
        methods = {}
        for m in stmt.methods:
            fn = ZapFunction(m.name, m.params, m.body, self.env,
                            m.return_type, m.is_async, is_method=True)
            methods[m.name] = fn
        obj = ZapObject()
        obj.fields['__name__'] = stmt.name
        obj.fields['__kind__'] = 'service'
        obj.fields['__expose__'] = stmt.expose
        obj.fields['__version__'] = stmt.version
        obj.fields['__metadata__'] = stmt.metadata
        if stmt.permissions:
            obj.fields['__permissions__'] = stmt.permissions
        for name, fn in methods.items():
            obj.fields[name] = BoundMethod(fn, obj)
        self.env.define(stmt.name, obj)
        ctx = get_context()
        ctx.add_api(stmt.name, f"service with {len(methods)} methods",
                    endpoints=[m.name for m in stmt.methods])
        save_context()
        return obj

    def _eval_database(self, stmt):
        tables = {}
        for t in stmt.tables:
            schema_obj = ZapObject()
            schema_obj.fields['__name__'] = t.name
            schema_obj.fields['__kind__'] = 'schema'
            for f in t.fields:
                schema_obj.fields[f.name] = f.field_type
            tables[t.name] = schema_obj
        obj = ZapObject()
        obj.fields['__name__'] = stmt.name
        obj.fields['__kind__'] = 'database'
        obj.fields['__tables__'] = tables
        for name, table in tables.items():
            obj.fields[name] = table
        self.env.define(stmt.name, obj)
        return obj

    def _eval_api(self, stmt):
        handler_fn = None
        if stmt.handler:
            handler_fn = ZapFunction(stmt.handler.name, stmt.handler.params,
                                    stmt.handler.body, self.env,
                                    stmt.handler.return_type, stmt.handler.is_async)
        obj = ZapObject()
        obj.fields['__kind__'] = 'api'
        obj.fields['__method__'] = stmt.method
        obj.fields['__path__'] = stmt.path
        obj.fields['__returns__'] = stmt.returns
        if handler_fn:
            obj.fields['__handler__'] = handler_fn
        api_name = f"{stmt.method}_{stmt.path.replace('/', '_').replace('{', '').replace('}', '')}"
        self.env.define(api_name, obj)
        return obj

    def _eval_page(self, stmt):
        obj = ZapObject()
        obj.fields['__kind__'] = 'page'
        obj.fields['__name__'] = stmt.name
        obj.fields['__route__'] = stmt.route
        self.env.define(stmt.name, obj)
        return obj

    def _eval_schema(self, stmt):
        obj = ZapObject()
        obj.fields['__kind__'] = 'schema'
        obj.fields['__name__'] = stmt.name
        for f in stmt.fields:
            obj.fields[f.name] = f.field_type
        default_val = None
        for f in stmt.fields:
            for cons_name, cons_val in f.constraints:
                if cons_name == 'default':
                    obj.fields[f.name] = cons_val
        self.env.define(stmt.name, obj)
        return obj

    def _eval_model(self, stmt):
        obj = ZapObject()
        obj.fields['__kind__'] = 'model'
        obj.fields['__name__'] = stmt.name
        for f in stmt.fields:
            obj.fields[f.name] = f.field_type
        for m in stmt.methods:
            fn = ZapFunction(m.name, m.params, m.body, self.env,
                            m.return_type, m.is_async, is_method=True)
            obj.methods[m.name] = fn
        self.env.define(stmt.name, obj)
        def constructor(*args):
            instance = ZapObject(base=obj)
            instance.fields['self'] = instance
            instance.methods = dict(obj.methods)
            for f in stmt.fields:
                instance.fields[f.name] = None
            if 'init' in instance.methods:
                init_fn = instance.methods['init']
                call_env = Environment(init_fn.closure)
                call_env.define('self', instance)
                for i, param in enumerate(init_fn.params):
                    if i == 0 and param['name'] == 'self':
                        continue
                    val = args[i - 1] if i - 1 < len(args) else param.get('default')
                    call_env.define(param['name'], val)
                prev = self.env
                self.env = call_env
                try:
                    self._eval_block(init_fn.body)
                finally:
                    self.env = prev
            return instance
        self.env.define(stmt.name, constructor)
        return obj

    def _eval_permission(self, stmt):
        """Define a permission constant."""
        perm_obj = ZapObject()
        perm_obj.fields['__kind__'] = 'permission'
        perm_obj.fields['__name__'] = stmt.name
        perm_obj.fields['__description__'] = stmt.description
        self.env.define(stmt.name, perm_obj)
        return perm_obj

    def _eval_concurrent(self, stmt):
        """Execute branches concurrently, collect results."""
        from concurrent.futures import ThreadPoolExecutor
        pool = ThreadPoolExecutor(max_workers=len(stmt.branches))
        futures = []
        for branch in stmt.branches:
            def run_branch(b=branch):
                local_ev = Evaluator(is_main=False)
                local_ev.env = Environment(self.env)
                local_ev.global_env = self.global_env
                try:
                    return local_ev._eval_block(b)
                except Exception as e:
                    return e
            futures.append(pool.submit(run_branch))
        pool.shutdown(wait=True)
        results = []
        for f in futures:
            r = f.result()
            results.append(r)
        return results

    def _eval_check(self, stmt):
        """Evaluate compile-time assertions at runtime (fallback)."""
        results = []
        for a in stmt.assertions:
            if isinstance(a, ExpectStmt):
                val = self._eval_expr(a.condition)
                if not self._is_truthy(val):
                    msg = a.message or f"check failed: {a.condition}"
                    raise RuntimeError(msg)
                results.append(val)
            else:
                val = self._eval_expr(a)
                results.append(val)
        return results

    def _eval_invariant(self, stmt):
        """Evaluate invariant — raise if false."""
        val = self._eval_expr(stmt.condition)
        if not self._is_truthy(val):
            raise RuntimeError(f"invariant violated: {stmt.condition}")
        return val

    def _eval_expect(self, stmt):
        """Evaluate test assertion — raise if false."""
        val = self._eval_expr(stmt.condition)
        if not self._is_truthy(val):
            msg = stmt.message or f"expect failed: {stmt.condition}"
            raise RuntimeError(msg)
        return val

    def _eval_expr(self, expr):
        if isinstance(expr, Literal):
            return expr.value

        if isinstance(expr, Identifier):
            try:
                if '.' in expr.name:
                    return float(expr.name)
                return int(expr.name)
            except ValueError:
                pass
            if self.env.has(expr.name):
                return self.env.get(expr.name)
            raise NameError(f"'{expr.name}' is not defined")

        if isinstance(expr, BinOp):
            return self._eval_binop(expr)

        if isinstance(expr, UnaryOp):
            return self._eval_unary(expr)

        if isinstance(expr, Call):
            return self._eval_call(expr)

        if isinstance(expr, Index):
            return self._eval_index(expr)

        if isinstance(expr, Slice):
            return self._eval_slice(expr)

        if isinstance(expr, MemberAccess):
            return self._eval_member(expr)

        if isinstance(expr, ListLiteral):
            elements = [self._eval_expr(e) for e in expr.elements]
            return ZapList(elements)

        if isinstance(expr, DictLiteral):
            entries = {}
            for k, v in expr.entries:
                if isinstance(k, Identifier):
                    key = k.name
                else:
                    key = self._eval_expr(k)
                val = self._eval_expr(v)
                entries[key] = val
            return ZapDict(entries)

        if isinstance(expr, TensorLiteral):
            data = [self._eval_expr(e) for e in expr.data]
            is_nested = any(isinstance(d, list) for d in data)
            if is_nested:
                actual = []
                for e in expr.data:
                    val = self._eval_expr(e)
                    if isinstance(val, ZapList):
                        actual.append(val.elements)
                    elif isinstance(val, ZapTensor):
                        actual.append(val.data)
                    else:
                        actual.append(val)
                return ZapTensor(actual)
            return ZapTensor(data)

        if isinstance(expr, Lambda):
            return self._make_lambda(expr)

        raise RuntimeError(f"unknown expression: {type(expr).__name__}")

    def _eval_binop(self, expr):
        left = self._eval_expr(expr.left)
        op = expr.op

        if op == '|>':
            right_expr = expr.right
            if isinstance(right_expr, Call):
                callee = self._eval_expr(right_expr.callee)
                call_args = [self._eval_expr(a) for a in right_expr.args]
                args = [left] + call_args
                return self._call_fn(callee, args)
            right = self._eval_expr(right_expr)
            if callable(right):
                return right(left)
            if isinstance(right, ZapFunction) or isinstance(right, ZapBuiltin):
                return self._call_fn(right, [left])
            if isinstance(right, ZapObject) and 'call' in right.methods:
                return self._call_fn(right.methods['call'], [left])
            raise RuntimeError(f"cannot pipe into {type(right).__name__}")

        right = self._eval_expr(expr.right)

        if op == '+':
            if isinstance(left, ZapTensor) or isinstance(right, ZapTensor):
                return left + right
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            if isinstance(left, ZapList) and isinstance(right, ZapList):
                return ZapList(left.elements + right.elements)
            return left + right
        if op == '-':
            if isinstance(left, ZapTensor) or isinstance(right, ZapTensor):
                return left - right
            return left - right
        if op == '*':
            if isinstance(left, ZapTensor) or isinstance(right, ZapTensor):
                return left * right
            if isinstance(left, ZapList) and isinstance(right, int):
                return ZapList(left.elements * right)
            return left * right
        if op == '/':
            return left / right
        if op == '%':
            return left % right
        if op == '**':
            return left ** right
        if op == '@@':
            if isinstance(left, ZapTensor) and isinstance(right, ZapTensor):
                return left.matmul(right)
            raise RuntimeError("@@ requires tensors")
        if op == '==':
            if isinstance(left, ZapType) and hasattr(left, 'data'):
                return isinstance(right, ZapTensor) and left.data == right.data
            return left == right
        if op == '!=':
            return left != right
        if op == '<':
            return left < right
        if op == '>':
            return left > right
        if op == '<=':
            return left <= right
        if op == '>=':
            return left >= right
        if op == 'and':
            return self._is_truthy(left) and self._is_truthy(right)
        if op == 'or':
            return self._is_truthy(left) or self._is_truthy(right)
        raise RuntimeError(f"unknown operator: {op}")

    def _eval_unary(self, expr):
        operand = self._eval_expr(expr.operand)
        op = expr.op
        if op == '-':
            return -operand
        if op == '+':
            return +operand
        if op == 'not':
            return not self._is_truthy(operand)
        raise RuntimeError(f"unknown unary op: {op}")

    def _eval_call(self, expr):
        callee = self._eval_expr(expr.callee)
        callee_name = getattr(callee, 'name', str(callee))[:50]
        t0 = time.time()
        try:
            args = [self._eval_expr(a) for a in expr.args]
            result = self._call_fn(callee, args)
            trace('call_end', callee_name, {
                'callee': callee_name,
                'arg_count': len(args),
                'duration': round(time.time() - t0, 6),
            })
            return result
        except Exception as e:
            trace('error', callee_name, {
                'callee': callee_name,
                'error': str(e)[:200],
                'duration': round(time.time() - t0, 6),
            })
            raise

    def _call_fn(self, callee, args):
        if isinstance(callee, BoundMethod):
            fn = callee.fn
            self_obj = callee.self_obj
            return fn._call(*([self_obj] + list(args)))

        if isinstance(callee, ZapFunction):
            return callee._call(*args)

        if isinstance(callee, ZapBuiltin):
            return callee.fn(*args)

        if callable(callee):
            return callee(*args)

        if isinstance(callee, ZapObject) and 'call' in callee.methods:
            return self._call_fn(callee.methods['call'], args)

        raise RuntimeError(f"'{type(callee).__name__}' is not callable")

    def _eval_index(self, expr):
        obj = self._eval_expr(expr.obj)
        idx = self._eval_expr(expr.index)
        if isinstance(obj, ZapList):
            return obj.elements[idx]
        if isinstance(obj, ZapTensor):
            flat = obj._flatten(obj.data)
            return flat[idx]
        if isinstance(obj, ZapDict):
            return obj.entries[idx]
        if isinstance(obj, str):
            return obj[idx]
        if isinstance(obj, list):
            return obj[idx]
        raise RuntimeError(f"cannot index {type(obj).__name__}")

    def _eval_slice(self, expr):
        obj = self._eval_expr(expr.obj)
        start = self._eval_expr(expr.start) if expr.start else None
        stop = self._eval_expr(expr.stop) if expr.stop else None
        step = self._eval_expr(expr.step) if expr.step else None
        if isinstance(obj, ZapList):
            s = slice(start, stop, step)
            return ZapList(obj.elements[s])
        if isinstance(obj, str):
            return obj[start:stop:step]
        if isinstance(obj, ZapTensor):
            s = slice(start, stop, step)
            flat = obj._flatten(obj.data)
            return ZapTensor(flat[s], [len(flat[s])])
        if isinstance(obj, list):
            return obj[start:stop:step]
        raise RuntimeError(f"cannot slice {type(obj).__name__}")

    def _eval_member(self, expr):
        obj = self._eval_expr(expr.obj)
        name = expr.member
        if isinstance(obj, ZapObject):
            if name in obj.fields:
                return obj.fields[name]
            if name in obj.methods:
                fn = obj.methods[name]
                if fn.is_method:
                    return BoundMethod(fn, obj)
                return fn
            if obj.base and isinstance(obj.base, ZapObject):
                if name in obj.base.methods:
                    fn = obj.base.methods[name]
                    if fn.is_method:
                        return BoundMethod(fn, obj)
                    return fn
                if name in obj.base.fields:
                    return obj.base.fields[name]
            raise AttributeError(f"'{type(obj).__name__}' has no attribute '{name}'")
        if isinstance(obj, ZapDict):
            if name in obj.entries:
                return obj.entries[name]
            raise AttributeError(f"dict has no key '{name}'")
        if isinstance(obj, ZapTensor):
            if name in ('shape', 'data'):
                return getattr(obj, name)
            raise AttributeError(f"tensor has no attribute '{name}'")
        if isinstance(obj, ZapList):
            if name == 'len':
                return len(obj.elements)
        py_attr = getattr(obj, name, None)
        if py_attr is not None:
            return py_attr
        raise AttributeError(f"'{type(obj).__name__}' has no attribute '{name}'")

    def _make_lambda(self, expr):
        def lambda_fn(*args):
            env = Environment(self.env)
            for i, p in enumerate(expr.params):
                val = args[i] if i < len(args) else p.get('default')
                env.define(p['name'], val)
            prev = self.env
            self.env = env
            try:
                result = self._eval_expr(expr.body)
                if isinstance(result, ReturnSignal):
                    return result.value
                return result
            finally:
                self.env = prev
        return lambda_fn

    def _is_truthy(self, val):
        if val is None or val is False:
            return False
        if val == 0:
            return False
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, ZapList):
            return len(val.elements) > 0
        if isinstance(val, ZapDict):
            return len(val.entries) > 0
        if isinstance(val, str):
            return len(val) > 0
        return True

    def _iterable_to_list(self, obj):
        if isinstance(obj, ZapRange):
            return list(obj._iter())
        if isinstance(obj, ZapList):
            return obj.elements
        if isinstance(obj, (list, tuple)):
            return list(obj)
        if isinstance(obj, str):
            return list(obj)
        if isinstance(obj, ZapTensor):
            flat = obj._flatten(obj.data)
            return flat
        raise RuntimeError(f"'{type(obj).__name__}' is not iterable")

class ReturnSignal(Exception):
    def __init__(self, value=None):
        super().__init__()
        self.value = value
