import time
import threading
from concurrent.futures import ThreadPoolExecutor
from .ast_nodes import *
from .environment import Environment
from .values import _zap_to_str
from .values import *
from .context import get_context, save_context
from .tracer import trace, get_tracer

class Evaluator:
    _thread_local = threading.local()
    _module_cache = {}

    @classmethod
    def _get_current(cls):
        return getattr(cls._thread_local, 'current', None)

    @classmethod
    def _set_current(cls, value):
        cls._thread_local.current = value

    @classmethod
    def _get_current_file(cls):
        return getattr(cls._thread_local, 'current_file', None)

    @classmethod
    def _set_current_file(cls, value):
        cls._thread_local.current_file = value

    def __init__(self, is_main=True, current_file=None):
        self.global_env = make_zap_builtins()
        self.env = self.global_env
        self.distributed_pool = None
        self._current_file = current_file
        self._source_lines = {}  # file -> list of lines
        if is_main:
            Evaluator._set_current(self)
        # Always set the current file for context-aware builtins
        if current_file:
            Evaluator._set_current_file(current_file)

    def _load_source_lines(self, filepath):
        """Cache source lines for a file to show context in errors."""
        if filepath not in self._source_lines:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._source_lines[filepath] = f.readlines()
            except:
                self._source_lines[filepath] = []
        return self._source_lines[filepath]

    def _format_error_with_context(self, exc, node=None):
        """Format an error message with source context when available."""
        msg = f"{type(exc).__name__}: {exc}"
        if node and hasattr(node, 'line') and node.line and self._current_file:
            lines = self._load_source_lines(self._current_file)
            if 0 < node.line <= len(lines):
                line_text = lines[node.line - 1].rstrip('\n').rstrip('\r')
                arrow = ' ' * (node.col) + '^'
                msg = f"{type(exc).__name__}: {exc}\n  --> {self._current_file}:{node.line}:{node.col}\n{node.line}: | {line_text}\n    : | {arrow}"
        elif self._current_file:
            msg = f"{type(exc).__name__}: {exc}\n  --> {self._current_file}"
        return msg

    @classmethod
    def get_current_file(cls):
        """Get the current file being evaluated, if any."""
        return cls._get_current_file()

    def evaluate(self, node):
        if isinstance(node, Program):
            return self._eval_program(node)
        raise RuntimeError(f"cannot evaluate {type(node).__name__} at top level")

    def _eval_program(self, node):
        result = None
        for stmt in node.stmts:
            try:
                result = self._eval_stmt(stmt)
            except ReturnSignal as rs:
                return rs.value
            except Exception as e:
                trace('error', '<program>', {'error': str(e)[:200], 'stmt': type(stmt).__name__})
                raise RuntimeError(self._format_error_with_context(e, stmt)) from None
        return result

    def _eval_stmt(self, stmt):
        st = type(stmt)

        if st is ExprStmt:
            return self._eval_expr(stmt.expr)
        if st is LetStmt:
            return self._eval_let(stmt)
        if st is AssignStmt:
            return self._eval_assign(stmt)
        if st is AugAssignStmt:
            return self._eval_aug_assign(stmt)
        if st is RetStmt:
            val = self._eval_expr(stmt.value) if stmt.value else None
            raise ReturnSignal(val)
        if st is BreakStmt:
            raise BreakSignal()
        if st is ContinueStmt:
            raise ContinueSignal()
        if st is IfStmt:
            return self._eval_if(stmt)
        if st is ForStmt:
            return self._eval_for(stmt)
        if st is WhileStmt:
            return self._eval_while(stmt)
        if st is Block:
            return self._eval_block(stmt)
        if st is FnDef:
            return self._eval_fn_def(stmt)
        if st is ClassDef:
            return self._eval_class_def(stmt)
        if st is ImportStmt:
            return self._eval_import(stmt)
        if st is MatchStmt:
            return self._eval_match(stmt)
        if st is IntendStmt:
            return self._eval_intend(stmt)
        if st is ServiceDecl:
            return self._eval_service(stmt)
        if st is DatabaseDecl:
            return self._eval_database(stmt)
        if st is ApiEndpoint:
            return self._eval_api(stmt)
        if st is PageDecl:
            return self._eval_page(stmt)
        if st is SchemaDecl:
            return self._eval_schema(stmt)
        if st is ModelDecl:
            return self._eval_model(stmt)
        if st is PermissionDecl:
            return self._eval_permission(stmt)
        if st is ConcurrentBlock:
            return self._eval_concurrent(stmt)
        if st is CheckBlock:
            return self._eval_check(stmt)
        if st is InvariantStmt:
            return self._eval_invariant(stmt)
        if st is ExpectStmt:
            return self._eval_expect(stmt)
        if st is ContractClause:
            return None
        raise RuntimeError(f"unknown statement: {st.__name__}")

    def _eval_block(self, block):
        env = Environment(self.env)
        prev = self.env
        self.env = env
        result = None
        try:
            for stmt in block.stmts:
                try:
                    result = self._eval_stmt(stmt)
                except ReturnSignal as rs:
                    return rs
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
            try:
                r = self._eval_block(stmt.body)
                if isinstance(r, ReturnSignal):
                    return r
                if r is not None:
                    result = r
            except ContinueSignal:
                continue
            except BreakSignal:
                break
        return result

    def _eval_while(self, stmt):
        result = None
        while self._is_truthy(self._eval_expr(stmt.condition)):
            try:
                r = self._eval_block(stmt.body)
                if isinstance(r, ReturnSignal):
                    return r
                if r is not None:
                    result = r
            except ContinueSignal:
                continue
            except BreakSignal:
                break
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
                            time.sleep(float(delay))
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
            # Store constructor on the class object, don't overwrite it
            obj.fields['__init__'] = ZapBuiltin(constructor, stmt.name + '.__init__')
            # Also make the class callable for ergonomics
            obj.fields['__call__'] = ZapBuiltin(constructor, stmt.name)
        return None

    def _eval_import(self, stmt):
        if stmt.from_module:
            self._eval_from_import(stmt)
        elif stmt.module:
            self._eval_zap_import(stmt)
        return None

    def _eval_from_import(self, stmt):
        """Handle 'import from X: Y, Z' - try Zap module first, fall back to Python."""
        import os as _os
        module_name = stmt.from_module
        module_path = module_name + '.zap'
        search_dirs = ['.']
        if self._current_file:
            search_dirs.insert(0, _os.path.dirname(self._current_file))
        resolved = None
        for d in search_dirs:
            candidate = _os.path.join(d, module_path) if d != '.' else module_path
            if _os.path.exists(candidate):
                resolved = candidate
                break
        if resolved is not None:
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
        else:
            try:
                py_mod = __import__(module_name)
                for name in stmt.names:
                    attr = getattr(py_mod, name, None)
                    if attr is not None:
                        self.env.define(name, attr)
            except ImportError:
                raise ImportError(f"cannot import '{module_name}'")

    def _eval_zap_import(self, stmt):
        import os as _os
        module_path = stmt.module
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

        # Use cached module if already imported
        if resolved in self._module_cache:
            return None

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
            self._module_cache[resolved] = True
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
        obj.fields['__version__'] = stmt.version.value if stmt.version else None
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
        # Store constructor on the model object, don't overwrite it
        obj.fields['__init__'] = ZapBuiltin(constructor, stmt.name + '.__init__')
        obj.fields['__call__'] = ZapBuiltin(constructor, stmt.name)
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
        import os as _os
        max_workers = min(len(stmt.branches), _os.cpu_count() * 4)
        pool = ThreadPoolExecutor(max_workers=max_workers)
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
        expr_type = type(expr)

        if expr_type is Literal:
            val = expr.value
            # Handle interpolated strings
            if isinstance(val, tuple) and len(val) == 2 and val[0] == 'interp':
                return self._eval_interp_string(val[1])
            return val

        if expr_type is Identifier:
            name = expr.name
            # Easter egg: patricio triggers the hidden mode
            if name == 'patricio':
                from .cli import _easter_egg_patricio
                _easter_egg_patricio()
                return "patricio mode activated"
            # Fast path: try int/float conversion first (common case)
            c = name[0] if name else ''
            if c.isdigit() or (c == '-' and len(name) > 1):
                try:
                    return int(name)
                except ValueError:
                    try:
                        return float(name)
                    except ValueError:
                        pass
            if self.env.has(name):
                return self.env.get(name)
            raise NameError(f"'{name}' is not defined")

        if expr_type is BinOp:
            return self._eval_binop(expr)

        if expr_type is UnaryOp:
            return self._eval_unary(expr)

        if expr_type is Call:
            return self._eval_call(expr)

        if expr_type is Index:
            return self._eval_index(expr)

        if expr_type is Slice:
            return self._eval_slice(expr)

        if expr_type is MemberAccess:
            return self._eval_member(expr)

        if expr_type is ListLiteral:
            elements = [self._eval_expr(e) for e in expr.elements]
            return ZapList(elements)

        if expr_type is DictLiteral:
            entries = {}
            for k, v in expr.entries:
                if type(k) is Identifier:
                    key = k.name
                else:
                    key = self._eval_expr(k)
                entries[key] = self._eval_expr(v)
            return ZapDict(entries)

        if expr_type is ListComprehension:
            def _eval_comprehension(child, bindings, idx, expr, condition):
                var, iterable = bindings[idx]
                iterable_val = child._eval_expr(iterable)
                result = []
                for item in child._iterable_to_list(iterable_val):
                    grandchild = Evaluator(is_main=False)
                    grandchild.env = Environment(child.env)
                    grandchild.global_env = child.global_env
                    grandchild._current_file = child._current_file
                    grandchild.env.define(var, item)
                    if idx + 1 < len(bindings):
                        result.extend(_eval_comprehension(grandchild, bindings, idx + 1, expr, condition))
                    else:
                        if condition is not None:
                            cond = grandchild._eval_expr(condition)
                            if not grandchild._is_truthy(cond):
                                continue
                        result.append(grandchild._eval_expr(expr))
                return result
            return ZapList(_eval_comprehension(self, expr.bindings, 0, expr.expr, expr.condition))

        if expr_type is DictComprehension:
            def _eval_dict_comprehension(child, bindings, idx, key_expr, value_expr, condition):
                var, iterable = bindings[idx]
                iterable_val = child._eval_expr(iterable)
                result = {}
                for item in child._iterable_to_list(iterable_val):
                    grandchild = Evaluator(is_main=False)
                    grandchild.env = Environment(child.env)
                    grandchild.global_env = child.global_env
                    grandchild._current_file = child._current_file
                    grandchild.env.define(var, item)
                    if idx + 1 < len(bindings):
                        result.update(_eval_dict_comprehension(grandchild, bindings, idx + 1, key_expr, value_expr, condition))
                    else:
                        if condition is not None:
                            cond = grandchild._eval_expr(condition)
                            if not grandchild._is_truthy(cond):
                                continue
                        key = grandchild._eval_expr(key_expr)
                        value = grandchild._eval_expr(value_expr)
                        result[key] = value
                return result
            return ZapDict(_eval_dict_comprehension(self, expr.bindings, 0, expr.key_expr, expr.value_expr, expr.condition))

        if expr_type is TensorLiteral:
            data = [self._eval_expr(e) for e in expr.data]
            is_nested = any(isinstance(d, list) for d in data)
            if is_nested:
                actual = []
                for e in expr.data:
                    val = self._eval_expr(e)
                    if type(val) is ZapList:
                        actual.append(val.elements)
                    elif type(val) is ZapTensor:
                        actual.append(val.data)
                    else:
                        actual.append(val)
                return ZapTensor(actual)
            return ZapTensor(data)

        if expr_type is Lambda:
            return self._make_lambda(expr)

        raise RuntimeError(f"unknown expression: {expr_type.__name__}")

    def _eval_interp_string(self, s):
        """Evaluate string interpolation: replace ${expr} with evaluated results."""
        import re
        def replace_expr(match):
            expr_str = match.group(1)
            # Parse and evaluate the expression
            from .lexer import Lexer
            from .parser import Parser
            try:
                tokens = Lexer(expr_str, '<interp>').tokenize()
                parser = Parser(tokens)
                prog = parser.parse()
                # Evaluate in current scope
                result = None
                for stmt in prog.stmts:
                    if hasattr(stmt, 'expr'):
                        result = self._eval_expr(stmt.expr)
                    else:
                        result = self._eval_stmt(stmt)
                return str(result) if result is not None else ''
            except Exception:
                return match.group(0)  # Return original on error
        return re.sub(r'\$\{([^}]+)\}', replace_expr, s)

    def _eval_binop(self, expr):
        left = self._eval_expr(expr.left)
        op = expr.op

        # Short-circuit: evaluate right only when needed
        if op == 'and':
            return left if not self._is_truthy(left) else self._eval_expr(expr.right)
        if op == 'or':
            return left if self._is_truthy(left) else self._eval_expr(expr.right)

        if op == '|>':
            right_expr = expr.right
            if type(right_expr) is Call:
                callee = self._eval_expr(right_expr.callee)
                args = [left] + [self._eval_expr(a) for a in right_expr.args]
                return self._call_fn(callee, args)
            right = self._eval_expr(right_expr)
            if callable(right):
                return right(left)
            if type(right) in (ZapFunction, ZapBuiltin):
                return self._call_fn(right, [left])
            if type(right) is ZapObject and 'call' in right.methods:
                return self._call_fn(right.methods['call'], [left])
            raise RuntimeError(f"cannot pipe into {type(right).__name__}")

        right = self._eval_expr(expr.right)

        # Fast path for common numeric operations
        left_type = type(left)
        right_type = type(right)

        if op == '+':
            if left_type is ZapTensor or right_type is ZapTensor:
                return left + right
            if left_type is str or right_type is str:
                return _zap_to_str(left) + _zap_to_str(right)
            if left_type is ZapList and right_type is ZapList:
                return ZapList(left.elements + right.elements)
            return left + right
        if op == '-':
            return left - right
        if op == '*':
            if left_type is ZapTensor or right_type is ZapTensor:
                return left * right
            if left_type is ZapList and right_type is int:
                return ZapList(left.elements * right)
            return left * right
        if op == '/':
            return left / right
        if op == '%':
            return left % right
        if op == '**':
            return left ** right
        if op == '@@':
            if left_type is ZapTensor and right_type is ZapTensor:
                return left.matmul(right)
            raise RuntimeError("@@ requires tensors")
        if op == '==':
            if type(left) is ZapType and hasattr(left, 'data'):
                return type(right) is ZapTensor and left.data == right.data
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

    def _compile_and_call(self, callee_name, args):
        """Compile and cache frequently called functions for performance."""
        cache_key = (callee_name, len(args))
        
        if not hasattr(self, '_jit_cache'):
            self._jit_cache = {}
            self._jit_env = Environment(self.env)
        
        if cache_key not in self._jit_cache:
            bytecode = self._optimize_function_call(callee_name, args)
            self._jit_cache[cache_key] = bytecode
            
        return self._execute_bytecode(
            self._jit_cache[cache_key],
            args,
            self._jit_env
        )
    
    def _optimize_function_call(self, callee_name, args):
        """Generate optimized bytecode for a function call."""
        bytecode = []
        
        # Fast path for common builtins
        if callee_name in ('print', 'len', 'str', 'int', 'float', 'range'):
            bytecode.extend([
                ('LOAD_BUILTIN', callee_name),
                ('PUSH_ARGS', len(args))
            ])
        else:
            # Generic function call
            bytecode.extend([
                ('LOAD_GLOBAL', callee_name),
                ('PUSH_ARGS', len(args))
            ])
        
        bytecode.extend([
            ('CALL',),
            ('RETURN',)
        ])
        
        return bytecode
    
    def _execute_bytecode(self, bytecode, args, env):
        """Execute optimized bytecode for faster function calls."""
        # Simplified bytecode execution loop
        stack = []
        
        for instr in bytecode:
            op = instr[0]
            
            if op == 'LOAD_BUILTIN':
                # Load built-in function
                name = instr[1]
                builtin_fn = env.get(name)
                stack.append(builtin_fn)
                
            elif op == 'LOAD_GLOBAL':
                name = instr[1]
                fn = env.get(name)
                stack.append(fn)
                
            elif op == 'PUSH_ARGS':
                # Push all args onto stack
                for i, arg in enumerate(args):
                    stack.append(arg)
                    
            elif op == 'CALL':
                # Pop function and args, call it
                fn = stack.pop()
                arg_count = instr[1]
                call_args = stack[-arg_count:]
                del stack[-arg_count:]
                
                try:
                    result = fn(*call_args)
                    stack.append(result)
                except Exception:
                    # Fallback to normal call
                    if callable(fn):
                        result = fn(*args)
                        stack.append(result)
                    
            elif op == 'RETURN':
                # Return top of stack
                return stack.pop() if stack else None
        
        return stack.pop() if stack else None

    def _eval_call(self, expr):
        callee = self._eval_expr(expr.callee)
        callee_name = getattr(callee, 'name', str(callee))[:50]
        t0 = time.time()
        
        # Fast path optimization for common built-in functions
        if callee_name in ('print', 'len', 'str', 'int', 'float', 'range') and hasattr(callee, 'fn'):
            try:
                args = [self._eval_expr(a) for a in expr.args]
                result = callee.fn(*args)
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
                raise RuntimeError(self._format_error_with_context(e, expr)) from None
        
        # Normal evaluation
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
            raise RuntimeError(self._format_error_with_context(e, expr)) from None

    def _call_fn(self, callee, args):
        callee_type = type(callee)

        if callee_type is BoundMethod:
            fn = callee.fn
            self_obj = callee.self_obj
            return fn._call(*([self_obj] + list(args)))

        if callee_type is ZapFunction:
            return callee._call(*args)

        if callee_type is ZapBuiltin:
            return callee.fn(*args)

        if callable(callee):
            return callee(*args)

        if callee_type is ZapObject and 'call' in callee.methods:
            return self._call_fn(callee.methods['call'], args)

        if callee_type is ZapObject and '__call__' in callee.fields:
            call_fn = callee.fields['__call__']
            if type(call_fn) is ZapBuiltin:
                return call_fn.fn(*args)
            return call_fn(*args)

        raise RuntimeError(f"'{callee_type.__name__}' is not callable")

    def _eval_index(self, expr):
        obj = self._eval_expr(expr.obj)
        idx = self._eval_expr(expr.index)
        obj_type = type(obj)
        if obj_type is ZapList:
            return obj.elements[idx]
        if obj_type is ZapTensor:
            return obj._getitem(obj.data, idx)
        if obj_type is ZapDict:
            return obj.entries[idx]
        if obj_type is str:
            return obj[idx]
        if obj_type is list:
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
        obj_type = type(obj)

        if obj_type is ZapObject:
            if name in obj.fields:
                return obj.fields[name]
            if name in obj.methods:
                fn = obj.methods[name]
                if fn.is_method:
                    return BoundMethod(fn, obj)
                return fn
            if obj.base and type(obj.base) is ZapObject:
                if name in obj.base.methods:
                    fn = obj.base.methods[name]
                    if fn.is_method:
                        return BoundMethod(fn, obj)
                    return fn
                if name in obj.base.fields:
                    return obj.base.fields[name]
            raise AttributeError(f"'{obj_type.__name__}' has no attribute '{name}'")

        if obj_type is ZapDict:
            if name in obj.entries:
                return obj.entries[name]
            raise AttributeError(f"dict has no key '{name}'")

        if obj_type is ZapTensor:
            if name in ('shape', 'data'):
                return getattr(obj, name)
            raise AttributeError(f"tensor has no attribute '{name}'")

        if obj_type is ZapList:
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
                if type(result) is ReturnSignal:
                    return result.value
                return result
            finally:
                self.env = prev
        return lambda_fn

    def _is_truthy(self, val):
        from .values import _is_truthy_std
        return _is_truthy_std(val)

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

class BreakSignal(Exception):
    pass

class ContinueSignal(Exception):
    pass
