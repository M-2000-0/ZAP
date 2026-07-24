import math
import random
import time as _time
import os as _os
import sys as _sys
import datetime as _datetime
import asyncio
import concurrent.futures
from .environment import Environment
from concurrent.futures import ThreadPoolExecutor

class ZapType:
    pass

class ZapObject(ZapType):
    def __init__(self, methods=None, fields=None, base=None):
        self.methods = methods or {}
        self.fields = fields or {}
        self.base = base


class ZapPromise(ZapType):
    """A Promise/Future for async/await support."""
    def __init__(self, coro=None):
        self._coro = coro
        self._result = None
        self._exception = None
        self._done = False
        self._callbacks = []
        self._loop = None
    
    def _schedule(self, loop):
        """Schedule the coroutine on the event loop."""
        if self._coro and not self._done:
            self._loop = loop
            # Use asyncio.ensure_future without loop parameter (deprecated in Python 3.10+)
            future = asyncio.ensure_future(self._coro)
            future.add_done_callback(self._on_done)
    
    def _on_done(self, future):
        try:
            self._result = future.result()
        except Exception as e:
            self._exception = e
        self._done = True
        for cb in self._callbacks:
            try:
                cb(self)
            except Exception:
                pass
        self._callbacks.clear()
    
    def then(self, callback):
        """Register a callback for when the promise resolves."""
        if self._done:
            try:
                callback(self)
            except Exception:
                pass
        else:
            self._callbacks.append(callback)
        return self
    
    def result(self):
        """Get the result, blocking if necessary."""
        if self._exception:
            raise self._exception
        return self._result
    
    def done(self):
        return self._done
    
    def __repr__(self):
        if self._done:
            if self._exception:
                return f"Promise(rejected={self._exception})"
            return f"Promise(resolved={self._result})"
        return "Promise(pending)"


class ZapFunction(ZapType):
    def __init__(self, name, params, body, closure, return_type=None, is_async=False,
                 is_method=False, decorators=None, contracts=None):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure
        self.return_type = return_type
        self.is_async = is_async
        self.is_method = is_method
        self.decorators = decorators or []
        self.contracts = contracts or []
        self._call = self._default_call

    def _default_call(self, *args):
        env = Environment(self.closure)
        for i, param in enumerate(self.params):
            if i < len(args):
                env.define(param['name'], args[i])
            elif param.get('default') is not None:
                env.define(param['name'], param['default'])
            else:
                env.define(param['name'], None)
        from .evaluator import Evaluator, ReturnSignal
        local_eval = Evaluator(is_main=False)
        local_eval.env = env
        local_eval.global_env = self.closure
        for contract in self.contracts:
            if contract.kind == 'requires':
                cond_env = Environment(env)
                for i, p in enumerate(self.params):
                    cond_env.define(p['name'], args[i] if i < len(args) else None)
                prev = local_eval.env
                local_eval.env = cond_env
                try:
                    ok = local_eval._eval_expr(contract.condition)
                finally:
                    local_eval.env = prev
                if not ok:
                    raise RuntimeError(f"@requires failed: {contract.condition}")
        
        # Handle async functions
        if self.is_async:
            async def _run_async():
                try:
                    result = local_eval._eval_block(self.body)
                    if isinstance(result, ReturnSignal):
                        result = result.value
                    for contract in self.contracts:
                        if contract.kind == 'ensures':
                            cond_env = Environment(local_eval.env)
                            cond_env.define('result', result)
                            prev = local_eval.env
                            local_eval.env = cond_env
                            try:
                                ok = local_eval._eval_expr(contract.condition)
                            finally:
                                local_eval.env = prev
                            if not ok:
                                raise RuntimeError(f"@ensures failed: {contract.condition}")
                    return result
                except ReturnSignal as rs:
                    return rs.value
            
            # Return a promise that wraps the async execution
            coro = _run_async()
            return ZapPromise(coro)
        
        # Sync execution
        try:
            result = local_eval._eval_block(self.body)
            if isinstance(result, ReturnSignal):
                result = result.value
            for contract in self.contracts:
                if contract.kind == 'ensures':
                    cond_env = Environment(local_eval.env)
                    cond_env.define('result', result)
                    prev = local_eval.env
                    local_eval.env = cond_env
                    try:
                        ok = local_eval._eval_expr(contract.condition)
                    finally:
                        local_eval.env = prev
                    if not ok:
                        raise RuntimeError(f"@ensures failed: {contract.condition}")
            return result
        finally:
            pass

    def __call__(self, *args):
        return self._call(*args)

class ZapBuiltin(ZapType):
    def __init__(self, fn, name=''):
        self.fn = fn
        self.name = name

class BoundMethod(ZapType):
    def __init__(self, fn, self_obj):
        self.fn = fn
        self.self_obj = self_obj

class ZapTensor(ZapType):
    __slots__ = ('data', 'shape', '_flat')
    def __init__(self, data, shape=None):
        self.data = data
        self.shape = shape or self._infer_shape(data)
        self._flat = None  # lazy flat cache
        if self.shape and len(self.shape) > 1 and not isinstance(data[0], list):
            self.data = self._unflatten(self._ensure_flat(data), list(self.shape))

    def _ensure_flat(self, data):
        if self._flat is not None:
            return self._flat
        self._flat = self._flatten(data)
        return self._flat

    def _infer_shape(self, data):
        if isinstance(data, list) and data:
            if isinstance(data[0], list):
                return [len(data)] + (self._infer_shape(data[0]) if data else [])
            return [len(data)]
        return []

    def __repr__(self):
        return f"tensor(shape={self.shape}, data={self.data})"

    def reshape(self, *dims):
        flat = self._flatten(self.data)
        total = 1
        for d in dims:
            total *= d
        if len(flat) != total:
            raise ValueError(f"cannot reshape tensor of {len(flat)} elements into {dims}")
        return ZapTensor(self._unflatten(flat, list(dims)), list(dims))

    def _flatten(self, d):
        if isinstance(d, list):
            result = []
            for item in d:
                if isinstance(item, list):
                    result.extend(self._flatten(item))
                else:
                    result.append(item)
            return result
        return [d]

    def _unflatten(self, flat, shape):
        if not shape:
            return flat[0] if flat else None
        if len(shape) == 1:
            return flat[:shape[0]]
        size = shape[0]
        rest = shape[1:]
        chunk = len(flat) // size
        return [self._unflatten(flat[i*chunk:(i+1)*chunk], rest) for i in range(size)]

    def matmul(self, other):
        if len(self.shape) != 2 or len(other.shape) != 2:
            raise ValueError("matmul requires 2D tensors")
        m, k1 = self.shape
        k2, n = other.shape
        if k1 != k2:
            raise ValueError(f"shape mismatch: {self.shape} vs {other.shape}")
        a = self.data
        b = other.data
        result = [[sum(a[i][k] * b[k][j] for k in range(k1)) for j in range(n)] for i in range(m)]
        return ZapTensor(result, [m, n])

    def _getitem(self, d, idx):
        if isinstance(idx, tuple):
            for i in idx:
                d = d[i]
            return d
        return d[idx]

    def __neg__(self):
        return self._map(lambda a: -a)

    def __pos__(self):
        return self._map(lambda a: +a)

    def __abs__(self):
        return self._map(lambda a: abs(a))

    def _map(self, op):
        flat = self._flatten(self.data)
        result = [op(x) for x in flat]
        return ZapTensor(self._unflatten(result, self.shape), list(self.shape))

    def __add__(self, other):
        return self._elementwise(other, lambda a, b: a + b)

    def __radd__(self, other):
        return self._elementwise(other, lambda a, b: a + b)

    def __sub__(self, other):
        return self._elementwise(other, lambda a, b: a - b)

    def __rsub__(self, other):
        return self._elementwise(other, lambda a, b: a - b)

    def __mul__(self, other):
        return self._elementwise(other, lambda a, b: a * b)

    def __rmul__(self, other):
        return self._elementwise(other, lambda a, b: a * b)

    def __truediv__(self, other):
        return self._elementwise(other, lambda a, b: a / b)

    def __rtruediv__(self, other):
        return self._elementwise(other, lambda a, b: a / b)

    def __pow__(self, other):
        return self._elementwise(other, lambda a, b: a ** b)

    def __rpow__(self, other):
        return self._elementwise(other, lambda a, b: a ** b)

    def _elementwise(self, other, op):
        if isinstance(other, ZapTensor):
            if self.shape != other.shape:
                raise ValueError(f"shape mismatch: {self.shape} vs {other.shape}")
            flat1 = self._flatten(self.data)
            flat2 = other._flatten(other.data)
            result = [op(a, b) for a, b in zip(flat1, flat2)]
            return ZapTensor(self._unflatten(result, self.shape), list(self.shape))
        flat = self._flatten(self.data)
        result = [op(x, other) for x in flat]
        return ZapTensor(self._unflatten(result, self.shape), list(self.shape))

class ZapList(ZapType):
    def __init__(self, elements):
        self.elements = list(elements)

    def append(self, item):
        self.elements.append(item)
        return self

    def __repr__(self):
        return f"[{', '.join(repr(e) for e in self.elements)}]"

class ZapDict(ZapType):
    def __init__(self, entries=None):
        self.entries = dict(entries or {})

    def __repr__(self):
        items = ', '.join(f"{k!r}: {v!r}" for k, v in self.entries.items())
        return f"{{{items}}}"

class ZapRange(ZapType):
    def __init__(self, start, stop, step=1):
        self.start = start
        self.stop = stop
        self.step = step

    def __iter__(self):
        return self._iter()

    def _iter(self):
        i = self.start
        if self.step > 0:
            while i < self.stop:
                yield i
                i += self.step
        else:
            while i > self.stop:
                yield i
                i += self.step

def make_zap_builtins():
    env = Environment()
    builtins = {
        'print': ZapBuiltin(lambda *args: print(*[_zap_to_str(a) for a in args]), 'print'),
        'len': ZapBuiltin(lambda x: _builtin_len(x), 'len'),
        'range': ZapBuiltin(lambda *a: _builtin_range(*a), 'range'),
        'int': ZapBuiltin(lambda x: int(x), 'int'),
        'float': ZapBuiltin(lambda x: float(x), 'float'),
        'str': ZapBuiltin(lambda x: _zap_to_str(x), 'str'),
        'list': ZapBuiltin(lambda x: _builtin_list(x), 'list'),
        'type': ZapBuiltin(lambda x: type(x).__name__, 'type'),
        'abs': ZapBuiltin(abs, 'abs'),
        'max': ZapBuiltin(_builtin_max, 'max'),
        'min': ZapBuiltin(_builtin_min, 'min'),
        'sum': ZapBuiltin(_builtin_sum, 'sum'),
        'round': ZapBuiltin(round, 'round'),
        'map': ZapBuiltin(_builtin_map, 'map'),
        'filter': ZapBuiltin(_builtin_filter, 'filter'),
        'tensor': ZapBuiltin(lambda data, shape=None: _builtin_tensor(data, shape), 'tensor'),
        'zeros': ZapBuiltin(lambda *shape: _builtin_zeros(list(shape)), 'zeros'),
        'ones': ZapBuiltin(lambda *shape: _builtin_ones(list(shape)), 'ones'),
        'reshape': ZapBuiltin(lambda t, *dims: t.reshape(*dims), 'reshape'),
        'random': ZapBuiltin(lambda: random.random(), 'random'),
        'randint': ZapBuiltin(random.randint, 'randint'),
        'exp': ZapBuiltin(_math_unary(math.exp), 'exp'),
        'log': ZapBuiltin(_math_unary(math.log), 'log'),
        'sin': ZapBuiltin(_math_unary(math.sin), 'sin'),
        'cos': ZapBuiltin(_math_unary(math.cos), 'cos'),
        'floor': ZapBuiltin(_math_unary(math.floor), 'floor'),
        'ceil': ZapBuiltin(_math_unary(math.ceil), 'ceil'),
        'sqrt': ZapBuiltin(_math_unary(math.sqrt), 'sqrt'),
        'say': ZapBuiltin(lambda *args: print(*[_zap_to_str(a) for a in args]), 'say'),
        'show': ZapBuiltin(lambda *args: print(*[_zap_to_str(a) for a in args]), 'show'),
        'ask': ZapBuiltin(lambda prompt='': input(str(prompt)), 'ask'),
        'now': ZapBuiltin(lambda: _datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'now'),
        'wait': ZapBuiltin(lambda secs: _time.sleep(secs), 'wait'),
        'clear': ZapBuiltin(lambda: _os.system('cls' if _os.name == 'nt' else 'clear'), 'clear'),
        'today': ZapBuiltin(lambda: _datetime.date.today().strftime('%Y-%m-%d'), 'today'),
        'get': ZapBuiltin(lambda name: _builtin_get(name), 'get'),
        'context_set': ZapBuiltin(lambda key, value: _builtin_context_set(key, value), 'context_set'),
        'context_get': ZapBuiltin(lambda key, default=None: _builtin_context_get(key, default), 'context_get'),
        'context_save': ZapBuiltin(lambda: _builtin_context_save(), 'context_save'),
        'context_intents': ZapBuiltin(lambda: _builtin_context_intents(), 'context_intents'),
        'context_add_convention': ZapBuiltin(lambda text: _builtin_context_add_convention(text), 'context_add_convention'),
        'context_add_decision': ZapBuiltin(lambda text: _builtin_context_add_decision(text), 'context_add_decision'),
        'pmap': ZapBuiltin(lambda fn, items: _builtin_pmap(fn, items), 'pmap'),
        'parallel': ZapBuiltin(lambda *fns: _builtin_parallel(*fns), 'parallel'),
        'retry': ZapBuiltin(lambda fn, retries=3, delay=0: _builtin_retry(fn, retries, delay), 'retry'),
    }
    for name, val in builtins.items():
        env.define(name, val)
    # String operations
    string_fns = {
        'upper': _stdlib_upper, 'lower': _stdlib_lower, 'strip': _stdlib_strip,
        'split': _stdlib_split, 'join': _stdlib_join, 'replace': _stdlib_replace,
        'startswith': _stdlib_startswith, 'endswith': _stdlib_endswith,
        'contains': _stdlib_contains, 'find': _stdlib_find,
        'reverse': _stdlib_reverse, 'trim': _stdlib_trim,
    }
    for name, fn in string_fns.items():
        env.define(name, ZapBuiltin(fn, name))
    env.define('format', ZapBuiltin(lambda t, d: _stdlib_format(t, **_zap_to_py(d) if isinstance(d, ZapDict) else {}), 'format'))

    # File I/O
    file_fns = {
        'read_file': _stdlib_read_file, 'write_file': _stdlib_write_file,
        'append_file': _stdlib_append_file, 'file_exists': _stdlib_file_exists,
        'list_dir': _stdlib_list_dir, 'mkdir': _stdlib_mkdir,
        'remove': _stdlib_remove, 'file_size': _stdlib_file_size,
    }
    for name, fn in file_fns.items():
        env.define(name, ZapBuiltin(fn, name))

    # JSON
    env.define('json_parse', ZapBuiltin(_stdlib_json_parse, 'json_parse'))
    env.define('json_stringify', ZapBuiltin(_stdlib_json_stringify, 'json_stringify'))

    # HTTP
    env.define('http_get', ZapBuiltin(_stdlib_http_get, 'http_get'))
    env.define('http_post', ZapBuiltin(_stdlib_http_post, 'http_post'))

    # Crypto / encoding
    crypto_fns = {
        'base64_encode': _stdlib_base64_encode, 'base64_decode': _stdlib_base64_decode,
        'sha256': _stdlib_sha256, 'md5': _stdlib_md5,
        'uuid': _stdlib_uuid, 'random_string': _stdlib_random_string,
    }
    for name, fn in crypto_fns.items():
        env.define(name, ZapBuiltin(fn, name))

    # OS / system
    os_fns = {
        'env_get': _stdlib_env_get, 'env_set': _stdlib_env_set,
        'exit': _stdlib_exit, 'sleep': _stdlib_sleep,
        'time': _stdlib_time,
    }
    for name, fn in os_fns.items():
        env.define(name, ZapBuiltin(fn, name))

    # Collections / iter tools
    coll_fns = {
        'sort': _stdlib_sort, 'reversed': _stdlib_reversed,
        'zip': _stdlib_zip, 'enumerate': _stdlib_enumerate,
        'flatten': _stdlib_flatten, 'chunk': _stdlib_chunk,
        'unique': _stdlib_unique, 'any': _stdlib_any, 'all': _stdlib_all,
    }
    for name, fn in coll_fns.items():
        env.define(name, ZapBuiltin(fn, name))

    # Frontend DSL
    env.define('element', ZapBuiltin(_stdlib_element, 'element'))
    env.define('html', ZapBuiltin(_stdlib_html_render, 'html'))
    env.define('render', ZapBuiltin(_stdlib_html_render, 'render'))
    env.define('html_escape', ZapBuiltin(_stdlib_html_escape, 'html_escape'))
    env.define('css', ZapBuiltin(lambda s: str(s), 'css'))
    env.define('signal', ZapBuiltin(_stdlib_signal, 'signal'))
    env.define('effect', ZapBuiltin(_stdlib_effect, 'effect'))

    # Zero-boilerplate: HTTP server, config, watch, subprocess
    env.define('http_server', ZapBuiltin(_stdlib_http_server, 'http_server'))
    env.define('config', ZapBuiltin(_stdlib_config, 'config'))
    env.define('watch', ZapBuiltin(_stdlib_watch, 'watch'))
    env.define('run', ZapBuiltin(_stdlib_run, 'run'))
    env.define('serve', ZapBuiltin(_stdlib_serve, 'serve'))

    # Parallel collections (zero-boilerplate parallelization)
    env.define('par_map', ZapBuiltin(_stdlib_par_map, 'par_map'))
    env.define('par_filter', ZapBuiltin(_stdlib_par_filter, 'par_filter'))
    env.define('par_for', ZapBuiltin(_stdlib_par_for, 'par_for'))

    # Database / SQLite
    env.define('db_open', ZapBuiltin(_stdlib_db_open, 'db_open'))
    env.define('db_query', ZapBuiltin(_stdlib_db_query, 'db_query'))
    env.define('db_query_one', ZapBuiltin(_stdlib_db_query_one, 'db_query_one'))
    env.define('db_exec', ZapBuiltin(_stdlib_db_exec, 'db_exec'))
    env.define('db_transaction', ZapBuiltin(_stdlib_db_transaction, 'db_transaction'))
    env.define('db_migrate', ZapBuiltin(_stdlib_db_migrate, 'db_migrate'))
    env.define('db_tables', ZapBuiltin(_stdlib_db_tables, 'db_tables'))
    env.define('db_schema', ZapBuiltin(_stdlib_db_schema, 'db_schema'))
    env.define('db_close', ZapBuiltin(_stdlib_db_close, 'db_close'))

    # === Zap AI: WiFi / Network ===
    env.define('wifi_scan', ZapBuiltin(_stdlib_wifi_scan, 'wifi_scan'))
    env.define('wifi_connect', ZapBuiltin(_stdlib_wifi_connect, 'wifi_connect'))
    env.define('wifi_status', ZapBuiltin(_stdlib_wifi_status, 'wifi_status'))

    # === Zap AI: Data Loading ===
    env.define('csv_load', ZapBuiltin(_stdlib_csv_load, 'csv_load'))
    env.define('csv_save', ZapBuiltin(_stdlib_csv_save, 'csv_save'))
    env.define('json_load', ZapBuiltin(_stdlib_json_load, 'json_load'))
    env.define('json_save', ZapBuiltin(_stdlib_json_save, 'json_save'))
    env.define('image_load', ZapBuiltin(_stdlib_image_load, 'image_load'))
    env.define('image_save', ZapBuiltin(_stdlib_image_save, 'image_save'))
    env.define('web_fetch', ZapBuiltin(_stdlib_web_fetch, 'web_fetch'))
    env.define('download', ZapBuiltin(_stdlib_download, 'download'))

    # === Zap AI: Neural Network Primitives ===
    env.define('dense', ZapBuiltin(_stdlib_dense, 'dense'))
    env.define('dense_from_weights', ZapBuiltin(_stdlib_dense_from_weights, 'dense_from_weights'))
    env.define('relu', ZapBuiltin(_stdlib_relu, 'relu'))
    env.define('sigmoid', ZapBuiltin(_stdlib_sigmoid, 'sigmoid'))
    env.define('softmax', ZapBuiltin(_stdlib_softmax, 'softmax'))
    env.define('tanh', ZapBuiltin(_stdlib_tanh, 'tanh'))
    env.define('leaky_relu', ZapBuiltin(_stdlib_leaky_relu, 'leaky_relu'))
    env.define('elu', ZapBuiltin(_stdlib_elu, 'elu'))

    # === Zap AI: Loss Functions ===
    env.define('mse_loss', ZapBuiltin(_stdlib_mse_loss, 'mse_loss'))
    env.define('cross_entropy_loss', ZapBuiltin(_stdlib_cross_entropy_loss, 'cross_entropy_loss'))
    env.define('mae_loss', ZapBuiltin(_stdlib_mae_loss, 'mae_loss'))
    env.define('bce_loss', ZapBuiltin(_stdlib_bce_loss, 'bce_loss'))

    # === Zap AI: Model Building & Training ===
    env.define('model', ZapBuiltin(_stdlib_model, 'model'))
    env.define('train', ZapBuiltin(_stdlib_train, 'train'))
    env.define('predict', ZapBuiltin(_stdlib_predict, 'predict'))
    env.define('save_model', ZapBuiltin(_stdlib_save_model, 'save_model'))
    env.define('load_model', ZapBuiltin(_stdlib_load_model, 'load_model'))
    env.define('model_summary', ZapBuiltin(_stdlib_model_summary, 'model_summary'))

    # === Zap AI: Data Utilities ===
    env.define('normalize', ZapBuiltin(_stdlib_normalize, 'normalize'))
    env.define('split_data', ZapBuiltin(_stdlib_split_data, 'split_data'))
    env.define('batch', ZapBuiltin(_stdlib_batch, 'batch'))
    env.define('one_hot', ZapBuiltin(_stdlib_one_hot, 'one_hot'))
    env.define('argmax', ZapBuiltin(_stdlib_argmax, 'argmax'))
    env.define('accuracy', ZapBuiltin(_stdlib_accuracy, 'accuracy'))
    env.define('seed', ZapBuiltin(_stdlib_seed, 'seed'))

    # === Auth Primitives ===
    env.define('jwt_encode', ZapBuiltin(_stdlib_jwt_encode, 'jwt_encode'))
    env.define('jwt_decode', ZapBuiltin(_stdlib_jwt_decode, 'jwt_decode'))
    env.define('jwt_verify', ZapBuiltin(_stdlib_jwt_verify, 'jwt_verify'))
    env.define('hash_password', ZapBuiltin(_stdlib_hash_password, 'hash_password'))
    env.define('verify_password', ZapBuiltin(_stdlib_verify_password, 'verify_password'))
    env.define('basic_auth_encode', ZapBuiltin(_stdlib_basic_auth_encode, 'basic_auth_encode'))
    env.define('basic_auth_decode', ZapBuiltin(_stdlib_basic_auth_decode, 'basic_auth_decode'))
    env.define('session_create', ZapBuiltin(_stdlib_session_create, 'session_create'))
    env.define('session_validate', ZapBuiltin(_stdlib_session_validate, 'session_validate'))

    # === Background Jobs — Queue, Cron ===
    env.define('queue_create', ZapBuiltin(_stdlib_queue_create, 'queue_create'))
    env.define('queue_add', ZapBuiltin(_stdlib_queue_add, 'queue_add'))
    env.define('queue_status', ZapBuiltin(_stdlib_queue_status, 'queue_status'))
    env.define('cron_create', ZapBuiltin(_stdlib_cron_create, 'cron_create'))
    env.define('cron_add', ZapBuiltin(_stdlib_cron_add, 'cron_add'))
    env.define('cron_stop', ZapBuiltin(_stdlib_cron_stop, 'cron_stop'))
    env.define('cron_list', ZapBuiltin(_stdlib_cron_list, 'cron_list'))

    # === AI Primitives — Prompt Templates, LLM, RAG ===
    env.define('prompt', ZapBuiltin(_stdlib_prompt_template, 'prompt'))
    env.define('llm', ZapBuiltin(_stdlib_llm_complete, 'llm'))
    env.define('llm_chat', ZapBuiltin(_stdlib_llm_chat, 'llm_chat'))
    env.define('embedding', ZapBuiltin(_stdlib_embedding, 'embedding'))
    env.define('cosine_sim', ZapBuiltin(_stdlib_cosine_similarity, 'cosine_sim'))
    env.define('rag_store', ZapBuiltin(_stdlib_rag_store, 'rag_store'))
    env.define('rag_search', ZapBuiltin(_stdlib_rag_search, 'rag_search'))

    # Dict helpers
    env.define('has_key', ZapBuiltin(lambda d, k: k in (d.entries if isinstance(d, ZapDict) else d), 'has_key'))

    # --- Short aliases (token optimization) ---
    short = {
        # Note: 'el' is intentionally omitted - it is a reserved keyword (KW_EL)
        'rd': 'read_file',         # rd("file.txt")
        'wr': 'write_file',        # wr("file.txt", content)
        'ap': 'append_file',       # ap("file.txt", content)
        'ls': 'list_dir',          # ls(".")
        'mv': 'remove',            # mv("file.txt")
        'sz': 'file_size',         # sz("file.txt")
        'ex': 'file_exists',       # ex("file.txt")
        'jp': 'json_parse',        # jp(str)
        'js': 'json_stringify',    # js(val)
        'hget': 'http_get',          # hget("https://...")
        'hpost': 'http_post',        # hpost("https://...", data)
        'sha': 'sha256',           # sha("hello")
        'b64e': 'base64_encode',   # b64e("hello")
        'b64d': 'base64_decode',   # b64d("aGVsbG8=")
        'uid': 'uuid',             # uid()
        'rstr': 'random_string',   # rstr(10)
        'enc': 'env_get',          # enc("PATH")
        'ens': 'env_set',          # ens("KEY", "val")
        'has': 'contains',         # has("hello", "el")
        'sw': 'startswith',        # sw("hi", "h")
        'ew': 'endswith',          # ew("hi", "i")
        'trim': 'strip',           # trim("  hi  ")
        'rev': 'reverse',          # rev("abc")
        # Zap AI short aliases
        'csv': 'csv_load',         # csv("data.csv")
        'jload': 'json_load',      # jload("data.json")
        'jsave': 'json_save',      # jsave("out.json", data)
        'wf': 'web_fetch',         # wf("https://...")
        'dl': 'download',          # dl("https://...", "file")
        'wl': 'wifi_scan',         # wl()
        'wc': 'wifi_connect',      # wc("ssid", "pass")
        'ws': 'wifi_status',       # ws()
        'dn': 'dense',             # dn(784, 128)
        'rl': 'relu',              # rl(x)
        'sg': 'sigmoid',           # sg(x)
        'sm': 'softmax',           # sm(x)
        'th': 'tanh',              # th(x)
        'mse': 'mse_loss',         # mse(pred, target)
        'ce': 'cross_entropy_loss', # ce(pred, target)
        'mae': 'mae_loss',         # mae(pred, target)
        'tr': 'train',             # tr(model, x, y, epochs=100)
        'pr': 'predict',           # pr(model, input)
        'smry': 'model_summary',   # smry(model)
        'nm': 'normalize',         # nm(data)
        'sd': 'split_data',        # sd(x, y, ratio=0.8)
        'bt': 'batch',             # bt(data, 32)
        'oh': 'one_hot',           # oh(indices, num_classes)
        'am': 'argmax',            # am(tensor)
        'acc': 'accuracy',         # acc(pred, targets)
        'sml': 'save_model',       # sml(model, "file.json")
        'lml': 'load_model',       # lml("file.json")
        # Auth short aliases
        'jenc': 'jwt_encode',      # jenc(payload, secret)
        'jdec': 'jwt_decode',      # jdec(token, secret)
        'jver': 'jwt_verify',      # jver(token, secret)
        'hpw': 'hash_password',    # hpw("pass123")
        'vpw': 'verify_password',  # vpw("pass123", "salt:hash")
        'bae': 'basic_auth_encode', # bae("user", "pass")
        'bad': 'basic_auth_decode', # bad("dXNlcjpwYXNz")
        'scrt': 'session_create',  # scrt(user_id)
        'sval': 'session_validate', # sval(session)
        # Background job short aliases
        'qcr': 'queue_create',     # qcr("jobs")
        'qad': 'queue_add',        # qad(queue, fn)
        'qst': 'queue_status',     # qst(queue)
        'ccr': 'cron_create',      # ccr("scheduler")
        'cad': 'cron_add',         # cad(cron, fn, interval)
        'cst': 'cron_stop',        # cst(cron)
        'clq': 'cron_list',        # clq(cron)
        # General short aliases
        'rng': 'range',           # rng(10)
        'en': 'enumerate',        # enumerate(items)
        'srt': 'sort',            # srt(xs)
        'rnd': 'random',          # rnd()
        'cfg': 'config',          # cfg("key")
        'lch': 'llm_chat',         # lch(messages)
        'emb': 'embedding',        # emb("hello world")
        'csim': 'cosine_sim',      # csim(vec_a, vec_b)
        'rgs': 'rag_store',        # rgs(docs, "collection")
        'rgq': 'rag_search',       #rgq("query", "collection")
    }
    for short_name, long_name in short.items():
        original = env.store.get(long_name)
        if original:
            env.define(short_name, original)

    env.define('True', True)
    env.define('False', False)
    return env

def _tensor_iter(t):
    flat = t._flatten(t.data)
    return iter(flat)

def _builtin_sum(x):
    if isinstance(x, ZapTensor):
        return sum(_tensor_iter(x))
    if isinstance(x, ZapList):
        return sum(x.elements)
    return sum(x)

def _builtin_max(*args):
    if len(args) == 1:
        x = args[0]
        if isinstance(x, ZapTensor):
            return max(_tensor_iter(x))
        if isinstance(x, ZapList):
            return max(x.elements)
        return max(x)
    return max(*args)

def _builtin_min(*args):
    if len(args) == 1:
        x = args[0]
        if isinstance(x, ZapTensor):
            return min(_tensor_iter(x))
        if isinstance(x, ZapList):
            return min(x.elements)
        return min(x)
    return min(*args)

def _builtin_list(x):
    if isinstance(x, ZapList):
        return x
    if isinstance(x, ZapRange):
        return ZapList(list(x._iter()))
    if isinstance(x, ZapTensor):
        return ZapList(x._flatten(x.data))
    return ZapList(list(x))

def _builtin_map(xs, fn):
    if isinstance(xs, ZapList):
        return ZapList([fn(x) for x in xs.elements])
    if isinstance(xs, ZapTensor):
        flat = xs._flatten(xs.data)
        return ZapList([fn(x) for x in flat])
    return ZapList([fn(x) for x in xs])

def _builtin_filter(xs, fn):
    if isinstance(xs, ZapList):
        return ZapList([x for x in xs.elements if fn(x)])
    if isinstance(xs, ZapTensor):
        flat = xs._flatten(xs.data)
        return ZapList([x for x in flat if fn(x)])
    return ZapList([x for x in xs if fn(x)])

def _builtin_get(name):
    from .evaluator import Evaluator
    current = Evaluator._get_current()
    if current:
        return current.env.get(str(name))
    return None

def _builtin_len(x):
    if hasattr(x, 'elements'):
        return len(x.elements)
    if hasattr(x, 'entries'):
        return len(x.entries)
    if hasattr(x, 'data'):
        return len(x.data)
    if hasattr(x, '__len__'):
        return len(x)
    if hasattr(x, 'shape'):
        return x.shape[0] if x.shape else 0
    raise TypeError(f"object of type '{type(x).__name__}' has no len()")

def _builtin_range(*args):
    if len(args) == 1:
        return ZapRange(0, args[0])
    if len(args) == 2:
        return ZapRange(args[0], args[1])
    if len(args) == 3:
        return ZapRange(args[0], args[1], args[2])
    raise TypeError("range takes 1-3 arguments")

def _unwrap(obj):
    if isinstance(obj, ZapList):
        return [_unwrap(e) for e in obj.elements]
    if isinstance(obj, ZapTensor):
        return obj.data
    return obj

def _math_unary(fn):
    def wrapped(x):
        if isinstance(x, ZapTensor):
            return x._map(fn)
        return fn(x)
    return wrapped

def _builtin_tensor(data, shape=None):
    if isinstance(data, ZapTensor):
        return data
    data = _unwrap(data)
    if shape is not None:
        shape = _unwrap(shape)
    if isinstance(data, (int, float)):
        return ZapTensor([data], shape or [1])
    return ZapTensor(data, shape)

def _builtin_zeros(shape):
    shape = _unwrap(shape)
    if len(shape) == 1:
        return ZapTensor([0] * shape[0], list(shape))
    sub = _builtin_zeros(shape[1:])
    return ZapTensor([sub.data] * shape[0], list(shape))

def _builtin_ones(shape):
    shape = _unwrap(shape)
    if len(shape) == 1:
        return ZapTensor([1] * shape[0], list(shape))
    sub = _builtin_ones(shape[1:])
    return ZapTensor([sub.data] * shape[0], list(shape))

def _builtin_context_set(key, value):
    from .context import get_context, save_context
    ctx = get_context()
    ctx.set(str(key), value)
    save_context()
    return value

def _builtin_context_get(key, default=None):
    from .context import get_context
    ctx = get_context()
    return ctx.get(str(key), default)

def _builtin_context_save():
    from .context import save_context
    save_context()
    return True

def _builtin_context_intents():
    from .context import get_context
    ctx = get_context()
    return ZapList(ctx.data.get('intents', []))

def _builtin_context_add_convention(text):
    from .context import get_context, save_context
    ctx = get_context()
    ctx.add_convention(str(text))
    save_context()
    return True

def _builtin_context_add_decision(text):
    from .context import get_context, save_context
    ctx = get_context()
    ctx.add_decision(str(text))
    save_context()
    return True

def _builtin_pmap(fn, items):
    from concurrent.futures import ThreadPoolExecutor
    if isinstance(items, ZapList):
        items = items.elements
    with ThreadPoolExecutor() as pool:
        futures = [pool.submit(fn, item) for item in items]
        results = [f.result() for f in futures]
    return ZapList(results)

def _builtin_parallel(*fns):
    from concurrent.futures import ThreadPoolExecutor, wait
    with ThreadPoolExecutor() as pool:
        futures = [pool.submit(fn) for fn in fns]
        wait(futures)
        results = [f.result() for f in futures]
    return ZapList(results)

def _builtin_retry(fn, retries=3, delay=0):
    def wrapper(*args):
        last_err = None
        for attempt in range(int(retries) + 1):
            try:
                return fn(*args)
            except Exception as e:
                last_err = e
                if attempt < int(retries) and delay:
                    _time.sleep(float(delay))
        raise last_err
    return ZapBuiltin(wrapper, 'retry_wrapper')


# ---------------------------------------------------------------------------
# Rich stdlib — string, file, JSON, HTTP, crypto, collections
# ---------------------------------------------------------------------------

def _stdlib_upper(s): return str(s).upper()
def _stdlib_lower(s): return str(s).lower()
def _stdlib_strip(s): return str(s).strip()
def _stdlib_split(s, sep=None, maxsplit=-1):
    if sep is None: return ZapList(str(s).split())
    return ZapList(str(s).split(str(sep), maxsplit if maxsplit >= 0 else -1))
def _stdlib_join(sep, items):
    if isinstance(items, ZapList): items = [str(x) for x in items.elements]
    return str(sep).join(str(x) for x in items)
def _stdlib_replace(s, old, new): return str(s).replace(str(old), str(new))
def _stdlib_startswith(s, prefix): return str(s).startswith(str(prefix))
def _stdlib_endswith(s, suffix): return str(s).endswith(str(suffix))
def _stdlib_contains(s, sub): return str(sub) in str(s)
def _stdlib_find(s, sub): return str(s).find(str(sub))
def _stdlib_reverse(s): return str(s)[::-1]
def _stdlib_format(template, **kwargs):
    t = str(template)
    for k, v in kwargs.items():
        t = t.replace('{' + k + '}', str(v))
    return t
def _stdlib_trim(s): return str(s).strip()

def _stdlib_read_file(path):
    with open(str(path), 'r', encoding='utf-8') as f:
        return f.read()
def _stdlib_write_file(path, content):
    with open(str(path), 'w', encoding='utf-8') as f:
        f.write(str(content))
    return True
def _stdlib_append_file(path, content):
    with open(str(path), 'a', encoding='utf-8') as f:
        f.write(str(content))
    return True
def _stdlib_file_exists(path):
    return __import__('os').path.exists(str(path))
def _stdlib_list_dir(path):
    return ZapList(__import__('os').listdir(str(path)))
def _stdlib_mkdir(path):
    __import__('os').makedirs(str(path), exist_ok=True)
    return True
def _stdlib_remove(path):
    __import__('os').remove(str(path))
    return True
def _stdlib_file_size(path):
    return __import__('os').path.getsize(str(path))

def _stdlib_json_parse(s):
    return _py_to_zap(__import__('json').loads(str(s)))
def _stdlib_json_stringify(obj, indent=2):
    return __import__('json').dumps(_zap_to_py(obj), indent=int(indent))

def _stdlib_http_get(url):
    try:
        import urllib.request
        resp = urllib.request.urlopen(str(url), timeout=10)
        return resp.read().decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"HTTP GET failed: {e}")
def _stdlib_http_post(url, data=None, content_type='application/json'):
    try:
        import urllib.request
        import json
        body = json.dumps(_zap_to_py(data)).encode('utf-8') if data is not None else None
        req = urllib.request.Request(str(url), data=body,
                                      headers={'Content-Type': str(content_type)},
                                      method='POST')
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.read().decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"HTTP POST failed: {e}")

def _stdlib_base64_encode(s):
    import base64
    return base64.b64encode(str(s).encode('utf-8')).decode('ascii')
def _stdlib_base64_decode(s):
    import base64
    return base64.b64decode(str(s)).decode('utf-8')
def _stdlib_sha256(s):
    import hashlib
    return hashlib.sha256(str(s).encode('utf-8')).hexdigest()
def _stdlib_md5(s):
    import hashlib
    return hashlib.md5(str(s).encode('utf-8')).hexdigest()
def _stdlib_uuid():
    import uuid
    return str(uuid.uuid4())
def _stdlib_random_string(length=8):
    import random, string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(int(length)))
def _stdlib_env_get(key, default=None):
    return __import__('os').environ.get(str(key), default)
def _stdlib_env_set(key, value):
    __import__('os').environ[str(key)] = str(value)
    return True
def _stdlib_exit(code=0):
    _sys.exit(int(code))
def _stdlib_sleep(secs):
    _time.sleep(float(secs))
    return True
def _stdlib_time():
    return _time.time()

def _stdlib_sort(items, key=None, reverse=False):
    if isinstance(items, ZapList):
        lst = list(items.elements)
        if callable(key):
            lst.sort(key=key, reverse=bool(reverse))
        else:
            lst.sort(reverse=bool(reverse))
        return ZapList(lst)
    raise TypeError("sort requires a list")
def _stdlib_reversed(items):
    if isinstance(items, ZapList):
        return ZapList(reversed(items.elements))
    raise TypeError("reversed requires a list")
def _stdlib_zip(*lists):
    import itertools
    lists = [l.elements if isinstance(l, ZapList) else l for l in lists]
    return ZapList([ZapList(group) for group in zip(*lists)])
def _stdlib_enumerate(items, start=0):
    if isinstance(items, ZapList):
        return ZapList([(i, v) for i, v in enumerate(items.elements, int(start))])
    raise TypeError("enumerate requires a list")
def _stdlib_flatten(items):
    def _flat(x):
        if isinstance(x, ZapList):
            for e in x.elements:
                yield from _flat(e)
        else:
            yield x
    return ZapList(list(_flat(items)))
def _stdlib_chunk(items, size):
    if isinstance(items, ZapList):
        lst = items.elements
        sz = int(size)
        return ZapList([ZapList(lst[i:i+sz]) for i in range(0, len(lst), sz)])
    raise TypeError("chunk requires a list")
def _stdlib_unique(items):
    if isinstance(items, ZapList):
        seen = set()
        result = []
        for e in items.elements:
            try:
                if e not in seen:
                    seen.add(e)
                    result.append(e)
            except TypeError:
                # Unhashable element - fall back to O(n^2) linear scan
                if e not in result:
                    result.append(e)
        return ZapList(result)
    raise TypeError("unique requires a list")
def _stdlib_any(items):
    if isinstance(items, ZapList):
        return any(_is_truthy_std(e) for e in items.elements)
    raise TypeError("any requires a list")
def _stdlib_all(items):
    if isinstance(items, ZapList):
        return all(_is_truthy_std(e) for e in items.elements)
    raise TypeError("all requires a list")

def _is_truthy_std(val):
    if val is None or val is False:
        return False
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, str):
        return len(val) > 0
    if isinstance(val, ZapList):
        return len(val.elements) > 0
    if isinstance(val, ZapDict):
        return len(val.entries) > 0
    return True

# ---------------------------------------------------------------------------
# Frontend DSL — HTML, CSS, reactive signals, rendering
# ---------------------------------------------------------------------------

_ESCAPE_TABLE = str.maketrans({
    '&': '&amp;', '<': '&lt;', '>': '&gt;',
    '"': '&quot;', "'": '&#x27;',
})

def _html_escape(s):
    return str(s).translate(_ESCAPE_TABLE)

_VOID_ELEMENTS = frozenset({
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr',
})

def _flat_children(children):
    result = []
    for c in children:
        if isinstance(c, ZapList):
            result.extend(c.elements)
        else:
            result.append(c)
    return result

def _ensure_list(v):
    if isinstance(v, ZapList):
        return v.elements
    if isinstance(v, list):
        return v
    return [v]

def _stdlib_element(tag, attrs=None, children=None):
    tag = str(tag)
    attrs_str = ""
    if attrs is not None:
        if isinstance(attrs, ZapDict):
            d = attrs.entries
        elif isinstance(attrs, dict):
            d = attrs
        else:
            d = {}
        parts = []
        for k, v in d.items():
            k = str(k)
            if v is True:
                parts.append(f'{k}')
            elif v is False or v is None:
                continue
            else:
                parts.append(f'{k}="{_html_escape(str(v))}"')
        if parts:
            attrs_str = ' ' + ' '.join(parts)

    inner = ""
    if children is not None:
        flat = _flat_children(_ensure_list(children))
        for c in flat:
            inner += str(c)

    if tag in _VOID_ELEMENTS:
        return f'<{tag}{attrs_str}>'
    return f'<{tag}{attrs_str}>{inner}</{tag}>'

def _stdlib_html_render(content):
    return str(content)

def _stdlib_html_escape(s):
    return _html_escape(s)

# Reactive signals (simple pub/sub)
_SIGNAL_COUNTER = [0]
_SIGNAL_REGISTRY = {}

class _ZapSignal:
    def __init__(self, value):
        self._value = value
        self._subs = []
        self._id = _SIGNAL_COUNTER[0]
        _SIGNAL_COUNTER[0] += 1
        _SIGNAL_REGISTRY[self._id] = self

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        for fn in self._subs:
            try:
                fn(value)
            except Exception:
                pass

    def sub(self, fn):
        self._subs.append(fn)

    def __repr__(self):
        return f"Signal({self._value!r})"

def _stdlib_signal(initial=None):
    return _ZapSignal(initial)

def _stdlib_effect(signal, fn):
    if isinstance(signal, _ZapSignal):
        signal.sub(fn)
        fn(signal.get())
    return True


def _stdlib_config(path=None):
    """Load JSON config from zap.json (or a custom path).
    If no path is provided, looks for zap.json in the current file's directory.
    If a relative path is provided, resolves it relative to the current file's directory."""
    import os, json
    from .evaluator import Evaluator
    
    # If no path provided, default to zap.json
    if path is None:
        path = "zap.json"
    
    # Resolve relative paths relative to the current file's directory
    if not os.path.isabs(str(path)):
        current_file = Evaluator.get_current_file()
        if current_file:
            base_dir = os.path.dirname(os.path.abspath(current_file))
            path = os.path.join(base_dir, str(path))
    
    if not os.path.exists(str(path)):
        return ZapDict({})
    with open(str(path), "r", encoding="utf-8") as f:
        data = json.load(f)
    return _py_to_zap(data)


def _stdlib_watch(path, fn):
    """Watch a file or directory for changes. Calls fn on each change.
    Uses polling (every 0.5s) for cross-platform compatibility."""
    import os, time, threading
    path = str(path)
    last_mtime = 0
    if os.path.isdir(path):
        files = []
        for root, _, fs in os.walk(path):
            for f in fs:
                if f.endswith(".zap"):
                    files.append(os.path.join(root, f))
        def _get_mtimes():
            return {f: os.path.getmtime(f) for f in files if os.path.exists(f)}
    else:
        files = [path]
        def _get_mtimes():
            return {path: os.path.getmtime(path) if os.path.exists(path) else 0}

    def _loop():
        nonlocal last_mtime
        while True:
            try:
                mtimes = _get_mtimes()
                current = max(mtimes.values()) if mtimes else 0
                if current > last_mtime:
                    last_mtime = current
                    fn()
            except Exception:
                pass
            time.sleep(0.5)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return True


def _stdlib_run(cmd, args=None):
    """Run a subprocess and return its stdout."""
    import subprocess
    cmd = str(cmd)
    if args is not None:
        if isinstance(args, ZapList):
            args = [_zap_to_py(a) for a in args.elements]
        cmd = [cmd] + list(args)
    else:
        cmd = cmd.split()
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def _stdlib_http_server(port=3000, handler=None, routes=None):
    """Start a zero-boilerplate HTTP server.
    If routes is provided (dict of path -> fn), serves those routes.
    Otherwise serves a simple default page."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading, json as _json

    routes_map = {}
    if routes is not None:
        if isinstance(routes, ZapDict):
            for k, v in routes.entries.items():
                routes_map[_zap_to_py(k)] = v

    class _Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, content_type="text/html"):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body.encode() if isinstance(body, str) else body)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in routes_map:
                try:
                    result = routes_map[path]()
                    if isinstance(result, ZapDict):
                        self._send(200, _json.dumps(_zap_to_py(result)), "application/json")
                    else:
                        self._send(200, str(result))
                except Exception as e:
                    self._send(500, str(e))
            else:
                self._send(404, "Not Found")

        def do_POST(self):
            path = self.path.split("?")[0]
            if path in routes_map:
                try:
                    result = routes_map[path]()
                    if isinstance(result, ZapDict):
                        self._send(200, _json.dumps(_zap_to_py(result)), "application/json")
                    else:
                        self._send(200, str(result))
                except Exception as e:
                    self._send(500, str(e))
            else:
                self._send(404, "Not Found")

        def log_message(self, *args):
            pass  # Suppress logging

    server = HTTPServer(("0.0.0.0", int(port)), _Handler)
    print(f"  Zap server listening on :{port}")
    server.serve_forever()
    return True


def _stdlib_serve(port=3000, routes=None):
    """Alias for http_server - zero-boilerplate web server."""
    return _stdlib_http_server(port, routes=routes)


def _stdlib_par_map(fn, items, workers=None):
    """Parallel map - applies fn to each item in items using a thread pool.
    Returns a ZapList with the results in order."""
    import concurrent.futures
    if isinstance(items, ZapList):
        items = list(items.elements)
    else:
        items = list(items)
    workers = workers or min(len(items), 4) or 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(fn, items))
    return ZapList(results)


def _stdlib_par_filter(fn, items, workers=None):
    """Parallel filter - keeps items where fn(item) is truthy."""
    import concurrent.futures
    if isinstance(items, ZapList):
        items = list(items.elements)
    else:
        items = list(items)
    workers = workers or min(len(items), 4) or 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = [item for item, keep in zip(items, pool.map(fn, items)) if keep]
    return ZapList(results)


def _stdlib_par_for(items, fn, workers=None):
    """Parallel for-each - calls fn(item) for each item in parallel.
    Returns True when all items are processed."""
    import concurrent.futures
    if isinstance(items, ZapList):
        items = list(items.elements)
    else:
        items = list(items)
    workers = workers or min(len(items), 4) or 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fn, items))
    return True


# Database / SQLite builtins
_DB_CONNECTIONS = {}  # name -> sqlite3.Connection

def _get_conn(name="default"):
    """Get or create a database connection."""
    import sqlite3
    if name not in _DB_CONNECTIONS:
        _DB_CONNECTIONS[name] = sqlite3.connect(name + ".db", check_same_thread=False)
        _DB_CONNECTIONS[name].row_factory = sqlite3.Row
    return _DB_CONNECTIONS[name]


def _stdlib_db_open(name="default", path=None):
    """Open a database connection. If path is given, uses that file; otherwise uses name.db."""
    import sqlite3
    if path:
        conn = sqlite3.connect(str(path), check_same_thread=False)
    else:
        conn = sqlite3.connect(str(name) + ".db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _DB_CONNECTIONS[str(name)] = conn
    return True


def _stdlib_db_close(name="default"):
    """Close a database connection."""
    if str(name) in _DB_CONNECTIONS:
        _DB_CONNECTIONS[str(name)].close()
        del _DB_CONNECTIONS[str(name)]
    return True


def _stdlib_db_exec(name, sql, params=None):
    """Execute a SQL statement (INSERT, UPDATE, DELETE, CREATE, etc.). Returns rows affected."""
    conn = _get_conn(name)
    cursor = conn.cursor()
    try:
        if params:
            if isinstance(params, ZapList):
                params = [_zap_to_py(p) for p in params.elements]
            elif isinstance(params, ZapDict):
                params = _zap_to_py(params)
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"SQL error: {e}")


def _stdlib_db_query(name, sql, params=None):
    """Execute a SELECT query and return results as list of dicts."""
    conn = _get_conn(name)
    cursor = conn.cursor()
    try:
        if params:
            if isinstance(params, ZapList):
                params = [_zap_to_py(p) for p in params.elements]
            elif isinstance(params, ZapDict):
                params = _zap_to_py(params)
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        rows = cursor.fetchall()
        return ZapList([ZapDict({k: row[k] for k in row.keys()}) for row in rows])
    except Exception as e:
        raise RuntimeError(f"SQL error: {e}")


def _stdlib_db_query_one(name, sql, params=None):
    """Execute a SELECT query and return a single row as dict, or None."""
    conn = _get_conn(name)
    cursor = conn.cursor()
    try:
        if params:
            if isinstance(params, ZapList):
                params = [_zap_to_py(p) for p in params.elements]
            elif isinstance(params, ZapDict):
                params = _zap_to_py(params)
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        row = cursor.fetchone()
        if row:
            return ZapDict({k: row[k] for k in row.keys()})
        return None
    except Exception as e:
        raise RuntimeError(f"SQL error: {e}")


def _stdlib_db_transaction(name, fn):
    """Run a function inside a transaction. Commits on success, rolls back on exception."""
    conn = _get_conn(name)
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN")
        result = fn()
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise


def _stdlib_db_migrate(name, migrations):
    """Run migrations. migrations is a list of SQL strings or dicts with 'up'/'down' keys."""
    conn = _get_conn(name)
    cursor = conn.cursor()
    # Create migrations table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _zap_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    # Get already applied migrations
    cursor.execute("SELECT name FROM _zap_migrations")
    applied = {row[0] for row in cursor.fetchall()}
    
    for i, migration in enumerate(migrations):
        if isinstance(migration, ZapDict):
            mig_name = str(migration.entries.get('name', f"migration_{i}"))
            up_sql = str(migration.entries.get('up', ''))
            down_sql = str(migration.entries.get('down', ''))
        else:
            mig_name = f"migration_{i}"
            up_sql = str(migration)
            down_sql = ""
        
        if mig_name in applied:
            continue
            
        try:
            cursor.execute("BEGIN")
            for stmt in up_sql.split(';'):
                stmt = stmt.strip()
                if stmt:
                    cursor.execute(stmt)
            cursor.execute("INSERT INTO _zap_migrations (name) VALUES (?)", (mig_name,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Migration {mig_name} failed: {e}")
    
    return True


def _stdlib_db_tables(name):
    """List all tables in the database."""
    conn = _get_conn(name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '_%'")
    return ZapList([row[0] for row in cursor.fetchall()])


def _stdlib_db_schema(name, table):
    """Get schema info for a table."""
    import re as _re
    if not _re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', str(table)):
        raise ValueError(f"invalid table name: {table}")
    conn = _get_conn(name)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info(`{table}`)")
    cols = cursor.fetchall()
    return ZapList([ZapDict({k: row[k] for k in row.keys()}) for row in cols])


def _py_to_zap(obj):
    if isinstance(obj, dict):
        return ZapDict({_py_to_zap(k): _py_to_zap(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return ZapList([_py_to_zap(e) for e in obj])
    if isinstance(obj, tuple):
        return ZapList([_py_to_zap(e) for e in obj])
    return obj

def _zap_to_str(obj):
    if isinstance(obj, ZapObject):
        if 'repr' in obj.methods:
            fn = obj.methods['repr']
            if isinstance(fn, ZapFunction):
                try:
                    result = fn(obj)
                    if result is not None:
                        return str(result)
                except Exception:
                    pass
        if obj.fields:
            parts = []
            for k, v in list(obj.fields.items())[:5]:
                if k != 'self':
                    try:
                        parts.append(f"{k}={_zap_to_str(v)}")
                    except Exception:
                        parts.append(f"{k}=...")
            if parts:
                return "{" + ", ".join(parts) + "}"
        return "Object"
    if isinstance(obj, ZapDict):
        items = []
        for k, v in list(obj.entries.items())[:5]:
            items.append(f"{_zap_to_str(k)}: {_zap_to_str(v)}")
        return "{" + ", ".join(items) + "}"
    if isinstance(obj, ZapList):
        items = [_zap_to_str(e) for e in obj.elements[:10]]
        return "[" + ", ".join(items) + "]"
    return str(obj)

def _zap_to_py(obj):
    if isinstance(obj, ZapDict):
        return {_zap_to_py(k): _zap_to_py(v) for k, v in obj.entries.items()}
    if isinstance(obj, ZapList):
        return [_zap_to_py(e) for e in obj.elements]
    if isinstance(obj, ZapTensor):
        return obj.data
    if isinstance(obj, ZapRange):
        return list(obj._iter())
    return obj


# ===========================================================================
# Zap AI — WiFi, Data Loading, Neural Networks, Training
# ===========================================================================

# ---------------------------------------------------------------------------
# WiFi / Network connectivity
# ---------------------------------------------------------------------------

def _stdlib_wifi_scan():
    """Scan for available WiFi networks. Returns list of dicts with ssid, signal, security."""
    import subprocess, re
    try:
        if __import__('os').name == 'nt':
            result = subprocess.run(['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
                                    capture_output=True, text=True, timeout=10)
            networks = []
            current = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                if 'SSID' in line and 'BSSID' not in line:
                    if current:
                        networks.append(current)
                    current = {'ssid': line.split(':', 1)[1].strip(), 'signal': '0%', 'security': 'Open'}
                elif 'Signal' in line:
                    current['signal'] = line.split(':', 1)[1].strip()
                elif 'Authentication' in line:
                    current['security'] = line.split(':', 1)[1].strip()
            if current:
                networks.append(current)
            return ZapList([ZapDict({k: v for k, v in n.items()}) for n in networks])
        else:
            result = subprocess.run(['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list'],
                                    capture_output=True, text=True, timeout=10)
            networks = []
            for line in result.stdout.strip().split('\n'):
                parts = line.split(':')
                if len(parts) >= 3:
                    networks.append({'ssid': parts[0], 'signal': parts[1] + '%', 'security': parts[2]})
            return ZapList([ZapDict({k: v for k, v in n.items()}) for n in networks])
    except Exception as e:
        return ZapList([])

def _stdlib_wifi_connect(ssid, password=None):
    """Connect to a WiFi network."""
    import subprocess
    try:
        if __import__('os').name == 'nt':
            cmd = ['netsh', 'wlan', 'connect', f'name={ssid}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return 'success' in result.stdout.lower() or 'connected' in result.stdout.lower()
        else:
            cmd = ['nmcli', 'dev', 'wifi', 'connect', str(ssid)]
            if password:
                cmd.extend(['password', str(password)])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return result.returncode == 0
    except Exception:
        return False

def _stdlib_wifi_status():
    """Get current WiFi connection status."""
    import subprocess
    try:
        if __import__('os').name == 'nt':
            result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'],
                                    capture_output=True, text=True, timeout=10)
            info = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                if 'SSID' in line and 'BSSID' not in line:
                    info['ssid'] = line.split(':', 1)[1].strip()
                elif 'State' in line:
                    info['state'] = line.split(':', 1)[1].strip()
                elif 'Signal' in line:
                    info['signal'] = line.split(':', 1)[1].strip()
                elif 'Speed' in line:
                    info['speed'] = line.split(':', 1)[1].strip()
            return ZapDict(info) if info else ZapDict({'state': 'disconnected'})
        else:
            result = subprocess.run(['nmcli', '-t', '-f', 'ACTIVE,SSID,SIGNAL', 'dev', 'wifi', 'list'],
                                    capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split('\n'):
                parts = line.split(':')
                if len(parts) >= 3 and parts[0] == 'yes':
                    return ZapDict({'ssid': parts[1], 'signal': parts[2] + '%', 'state': 'connected'})
            return ZapDict({'state': 'disconnected'})
    except Exception:
        return ZapDict({'state': 'unknown'})


# ---------------------------------------------------------------------------
# Data loading — CSV, JSON, Image
# ---------------------------------------------------------------------------

def _stdlib_csv_load(path, delimiter=',', has_header=True):
    """Load a CSV file into a list of dicts (if has_header) or list of lists."""
    import csv
    rows = []
    with open(str(path), 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=str(delimiter))
        if has_header:
            headers = next(reader)
            for row in reader:
                rows.append(dict(zip(headers, row)))
        else:
            for row in reader:
                rows.append(row)
    return ZapList([ZapDict({k: v for k, v in r.items()}) if isinstance(r, dict) else ZapList(r) for r in rows])

def _stdlib_csv_save(path, data, delimiter=','):
    """Save data to CSV. data is list of dicts or list of lists."""
    import csv
    if isinstance(data, ZapList):
        data = data.elements
    if not data:
        return False
    with open(str(path), 'w', newline='', encoding='utf-8') as f:
        if isinstance(data[0], ZapDict):
            headers = list(data[0].entries.keys())
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=str(delimiter))
            writer.writeheader()
            for row in data:
                writer.writerow({k: _zap_to_py(v) for k, v in row.entries.items()})
        else:
            writer = csv.writer(f, delimiter=str(delimiter))
            for row in data:
                if isinstance(row, ZapList):
                    writer.writerow(row.elements)
                else:
                    writer.writerow(row)
    return True

def _stdlib_json_load(path):
    """Load JSON file and return Zap value."""
    import json
    with open(str(path), 'r', encoding='utf-8') as f:
        return _py_to_zap(json.load(f))

def _stdlib_json_save(path, data):
    """Save data as JSON file."""
    import json
    with open(str(path), 'w', encoding='utf-8') as f:
        json.dump(_zap_to_py(data), f, indent=2)
    return True

def _stdlib_image_load(path):
    """Load an image file. Returns dict with width, height, pixels (list of [r,g,b])."""
    try:
        from PIL import Image
        img = Image.open(str(path)).convert('RGB')
        pixels = list(img.getdata())
        return ZapDict({
            'width': img.width, 'height': img.height,
            'pixels': ZapList([ZapList(list(p)) for p in pixels])
        })
    except ImportError:
        raise RuntimeError("Pillow not installed. Run: pip install Pillow")

def _stdlib_image_save(path, width, height, pixels):
    """Save an image from pixel data. pixels is list of [r,g,b] tuples."""
    try:
        from PIL import Image
        if isinstance(pixels, ZapList):
            pixels = [tuple(p.elements) if isinstance(p, ZapList) else tuple(p) for p in pixels.elements]
        img = Image.new('RGB', (int(width), int(height)))
        img.putdata(pixels)
        img.save(str(path))
        return True
    except ImportError:
        raise RuntimeError("Pillow not installed. Run: pip install Pillow")

def _stdlib_web_fetch(url, as_json=False):
    """Fetch data from a URL. Returns string or parsed JSON."""
    import urllib.request
    resp = urllib.request.urlopen(str(url), timeout=30)
    data = resp.read().decode('utf-8')
    if as_json:
        import json
        return _py_to_zap(json.loads(data))
    return data

def _stdlib_download(url, path):
    """Download a file from URL to local path."""
    import urllib.request
    urllib.request.urlretrieve(str(url), str(path))
    return True


# ---------------------------------------------------------------------------
# Neural Network Primitives
# ---------------------------------------------------------------------------

class ZapNeuralLayer:
    """A single neural network layer (dense/linear)."""
    def __init__(self, weights, biases, activation='linear'):
        self.weights = weights  # ZapTensor
        self.biases = biases    # ZapTensor
        self.activation = activation
        self._cache = {}  # for backprop

    def __repr__(self):
        return f"Layer(weights={self.weights.shape}, activation={self.activation})"

class ZapModel:
    """A neural network model composed of layers."""
    def __init__(self, layers=None, loss='mse', optimizer='sgd', lr=0.01):
        self.layers = layers or []
        self.loss = loss
        self.optimizer = optimizer
        self.lr = lr
        self.training_history = []

    def __repr__(self):
        return f"Model(layers={len(self.layers)}, loss={self.loss})"

def _stdlib_dense(in_size, out_size, activation='relu'):
    """Create a dense (fully connected) layer with random weights."""
    import random
    weights = [[random.gauss(0, (2.0 / in_size) ** 0.5) for _ in range(out_size)] for _ in range(in_size)]
    biases = [0.0] * out_size
    return ZapNeuralLayer(ZapTensor(weights, [in_size, out_size]), ZapTensor(biases, [out_size]), activation)

def _stdlib_dense_from_weights(weights, biases, activation='relu'):
    """Create a dense layer from existing weights and biases."""
    if isinstance(weights, ZapTensor):
        w = weights
    else:
        w = ZapTensor(_unwrap(weights))
    if isinstance(biases, ZapTensor):
        b = biases
    else:
        b = ZapTensor(_unwrap(biases))
    return ZapNeuralLayer(w, b, activation)

# Activation functions
def _stdlib_relu(x):
    if isinstance(x, ZapTensor):
        return x._map(lambda v: max(0, v))
    return max(0, x)

def _stdlib_sigmoid(x):
    import math
    if isinstance(x, ZapTensor):
        return x._map(lambda v: 1.0 / (1.0 + math.exp(-max(-500, min(500, v)))))
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, x))))

def _stdlib_softmax(x):
    import math
    if isinstance(x, ZapTensor):
        flat = x._flatten(x.data)
        max_val = max(flat)
        exps = [math.exp(v - max_val) for v in flat]
        total = sum(exps)
        result = [v / total for v in exps]
        return ZapTensor(x._unflatten(result, x.shape), list(x.shape))
    return x

def _stdlib_tanh(x):
    import math
    if isinstance(x, ZapTensor):
        return x._map(lambda v: math.tanh(v))
    return math.tanh(x)

def _stdlib_leaky_relu(x, alpha=0.01):
    if isinstance(x, ZapTensor):
        return x._map(lambda v: v if v > 0 else alpha * v)
    return x if x > 0 else alpha * x

def _stdlib_elu(x, alpha=1.0):
    import math
    if isinstance(x, ZapTensor):
        return x._map(lambda v: v if v > 0 else alpha * (math.exp(v) - 1))
    return x if x > 0 else alpha * (math.exp(x) - 1)

# Loss functions
def _stdlib_mse_loss(predicted, target):
    """Mean Squared Error loss."""
    if isinstance(predicted, ZapTensor) and isinstance(target, ZapTensor):
        p = predicted._flatten(predicted.data)
        t = target._flatten(target.data)
        n = len(p)
        return sum((a - b) ** 2 for a, b in zip(p, t)) / n
    return (predicted - target) ** 2

def _stdlib_cross_entropy_loss(predicted, target):
    """Cross-entropy loss for classification."""
    import math
    if isinstance(predicted, ZapTensor) and isinstance(target, ZapTensor):
        p = predicted._flatten(predicted.data)
        t = target._flatten(target.data)
        n = len(p)
        eps = 1e-7
        return -sum(t[i] * math.log(max(eps, p[i])) for i in range(n)) / n
    eps = 1e-7
    return -(target * math.log(max(eps, predicted)) + (1 - target) * math.log(max(eps, 1 - predicted)))

def _stdlib_mae_loss(predicted, target):
    """Mean Absolute Error loss."""
    if isinstance(predicted, ZapTensor) and isinstance(target, ZapTensor):
        p = predicted._flatten(predicted.data)
        t = target._flatten(target.data)
        n = len(p)
        return sum(abs(a - b) for a, b in zip(p, t)) / n
    return abs(predicted - target)

def _stdlib_bce_loss(predicted, target):
    """Binary Cross-Entropy loss."""
    import math
    eps = 1e-7
    if isinstance(predicted, ZapTensor) and isinstance(target, ZapTensor):
        p = predicted._flatten(predicted.data)
        t = target._flatten(target.data)
        n = len(p)
        return -sum(t[i] * math.log(max(eps, p[i])) + (1 - t[i]) * math.log(max(eps, 1 - p[i])) for i in range(n)) / n
    return -(target * math.log(max(eps, predicted)) + (1 - target) * math.log(max(eps, 1 - predicted)))


# ---------------------------------------------------------------------------
# Model building, training, prediction, save/load
# ---------------------------------------------------------------------------

def _stdlib_model(loss='mse', lr=0.01):
    """Create a neural network model."""
    model = ZapModel(loss=loss, lr=lr)
    return model

def _forward_pass(model, input_data):
    """Forward pass through all layers."""
    x = input_data
    for layer in model.layers:
        if isinstance(x, ZapTensor) and isinstance(layer.weights, ZapTensor):
            x = x.matmul(layer.weights)
            if isinstance(layer.biases, ZapTensor):
                bias = layer.biases
                if isinstance(x, ZapTensor):
                    flat_x = x._flatten(x.data)
                    flat_b = bias._flatten(bias.data)
                    n = len(flat_x)
                    result = [flat_x[i] + flat_b[i % len(flat_b)] for i in range(n)]
                    x = ZapTensor(x._unflatten(result, x.shape), list(x.shape))
        # Apply activation
        if layer.activation == 'relu':
            x = _stdlib_relu(x)
        elif layer.activation == 'sigmoid':
            x = _stdlib_sigmoid(x)
        elif layer.activation == 'softmax':
            x = _stdlib_softmax(x)
        elif layer.activation == 'tanh':
            x = _stdlib_tanh(x)
        elif layer.activation == 'linear':
            pass
    return x

def _stdlib_train(model, x_data, y_data, epochs=100, batch_size=32, verbose=True):
    """Train a model using simple gradient descent (numerical approximation).
    Returns the trained model with training history."""
    if not isinstance(model, ZapModel):
        raise RuntimeError("train requires a Model")
    lr = model.lr

    for epoch in range(int(epochs)):
        epoch_loss = 0
        n_samples = 1

        if isinstance(x_data, ZapTensor) and isinstance(y_data, ZapTensor):
            x_flat = x_data._flatten(x_data.data)
            y_flat = y_data._flatten(y_data.data)
            n_samples = len(x_flat)
        elif isinstance(x_data, ZapList):
            n_samples = len(x_data.elements)

        # Simple SGD: perturb weights slightly and measure loss change
        for layer in model.layers:
            if isinstance(layer.weights, ZapTensor):
                w_flat = layer.weights._flatten(layer.weights.data)
                grad = []
                for i in range(len(w_flat)):
                    old = w_flat[i]
                    # Numerical gradient
                    w_flat[i] = old + lr * 0.01
                    layer.weights = ZapTensor(
                        layer.weights._unflatten(w_flat, layer.weights.shape),
                        list(layer.weights.shape))
                    pred_plus = _forward_pass(model, x_data)
                    loss_plus = _stdlib_mse_loss(pred_plus, y_data) if model.loss == 'mse' else _stdlib_cross_entropy_loss(pred_plus, y_data)

                    w_flat[i] = old - lr * 0.01
                    layer.weights = ZapTensor(
                        layer.weights._unflatten(w_flat, layer.weights.shape),
                        list(layer.weights.shape))
                    pred_minus = _forward_pass(model, x_data)
                    loss_minus = _stdlib_mse_loss(pred_minus, y_data) if model.loss == 'mse' else _stdlib_cross_entropy_loss(pred_minus, y_data)

                    g = (loss_plus - loss_minus) / (2 * lr * 0.01)
                    grad.append(g)
                    w_flat[i] = old

                # Update weights
                new_w = [w_flat[i] - lr * grad[i] for i in range(len(w_flat))]
                layer.weights = ZapTensor(
                    layer.weights._unflatten(new_w, layer.weights.shape),
                    list(layer.weights.shape))

                # Update biases
                if isinstance(layer.biases, ZapTensor):
                    b_flat = layer.biases._flatten(layer.biases.data)
                    new_b = [b - lr * 0.001 for b in b_flat]
                    layer.biases = ZapTensor(
                        layer.biases._unflatten(new_b, layer.biases.shape),
                        list(layer.biases.shape))

        # Compute epoch loss
        pred = _forward_pass(model, x_data)
        if model.loss == 'mse':
            epoch_loss = _stdlib_mse_loss(pred, y_data)
        elif model.loss == 'cross_entropy':
            epoch_loss = _stdlib_cross_entropy_loss(pred, y_data)
        else:
            epoch_loss = _stdlib_mse_loss(pred, y_data)

        model.training_history.append({'epoch': epoch + 1, 'loss': epoch_loss})

        if verbose and (epoch % max(1, int(epochs) // 10) == 0 or epoch == int(epochs) - 1):
            print(f"  epoch {epoch + 1}/{epochs} — loss: {epoch_loss:.6f}")

    return model

def _stdlib_predict(model, input_data):
    """Run prediction through the model."""
    if not isinstance(model, ZapModel):
        raise RuntimeError("predict requires a Model")
    return _forward_pass(model, input_data)

def _stdlib_save_model(model, path):
    """Save a trained model to a file (JSON)."""
    import json
    if not isinstance(model, ZapModel):
        raise RuntimeError("save_model requires a Model")
    data = {
        'loss': model.loss,
        'optimizer': model.optimizer,
        'lr': model.lr,
        'layers': []
    }
    for layer in model.layers:
        data['layers'].append({
            'weights': layer.weights.data if isinstance(layer.weights, ZapTensor) else layer.weights,
            'biases': layer.biases.data if isinstance(layer.biases, ZapTensor) else layer.biases,
            'activation': layer.activation,
            'weights_shape': layer.weights.shape if isinstance(layer.weights, ZapTensor) else [],
            'biases_shape': layer.biases.shape if isinstance(layer.biases, ZapTensor) else [],
        })
    with open(str(path), 'w') as f:
        json.dump(data, f)
    return True

def _stdlib_load_model(path):
    """Load a model from a file."""
    import json
    with open(str(path), 'r') as f:
        data = json.load(f)
    model = ZapModel(loss=data.get('loss', 'mse'), lr=data.get('lr', 0.01))
    for layer_data in data.get('layers', []):
        w = ZapTensor(layer_data['weights'], layer_data.get('weights_shape', []))
        b = ZapTensor(layer_data['biases'], layer_data.get('biases_shape', []))
        model.layers.append(ZapNeuralLayer(w, b, layer_data.get('activation', 'linear')))
    return model

def _stdlib_model_summary(model):
    """Get a summary of the model architecture."""
    if not isinstance(model, ZapModel):
        raise RuntimeError("model_summary requires a Model")
    lines = []
    lines.append(f"Model: {len(model.layers)} layers")
    lines.append(f"Loss: {model.loss}")
    lines.append(f"Learning rate: {model.lr}")
    total_params = 0
    for i, layer in enumerate(model.layers):
        w_count = 1
        if isinstance(layer.weights, ZapTensor):
            for s in layer.weights.shape:
                w_count *= s
        b_count = 1
        if isinstance(layer.biases, ZapTensor):
            for s in layer.biases.shape:
                b_count *= s
        total_params += w_count + b_count
        w_shape = layer.weights.shape if isinstance(layer.weights, ZapTensor) else '?'
        lines.append(f"  Layer {i}: Dense({w_shape}, activation={layer.activation}) — {w_count + b_count} params")
    lines.append(f"Total parameters: {total_params}")
    if model.training_history:
        last = model.training_history[-1]
        lines.append(f"Last loss: {last['loss']:.6f} (epoch {last['epoch']})")
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Data utilities — normalize, split, batch, encode/decode
# ---------------------------------------------------------------------------

def _stdlib_normalize(data, method='minmax'):
    """Normalize tensor/list data. method: 'minmax' or 'zscore'."""
    if isinstance(data, ZapTensor):
        flat = data._flatten(data.data)
    elif isinstance(data, ZapList):
        flat = list(data.elements)
    else:
        return data

    if method == 'minmax':
        mn, mx = min(flat), max(flat)
        rng = mx - mn if mx != mn else 1
        normed = [(x - mn) / rng for x in flat]
    elif method == 'zscore':
        mn = sum(flat) / len(flat)
        std = (sum((x - mn) ** 2 for x in flat) / len(flat)) ** 0.5
        std = std if std != 0 else 1
        normed = [(x - mn) / std for x in flat]
    else:
        normed = flat

    if isinstance(data, ZapTensor):
        return ZapTensor(data._unflatten(normed, data.shape), list(data.shape))
    return ZapList(normed)

def _stdlib_split_data(x, y, ratio=0.8):
    """Split data into train/test sets. ratio is fraction for training."""
    if isinstance(x, ZapTensor):
        x_flat = x._flatten(x.data)
    elif isinstance(x, ZapList):
        x_flat = list(x.elements)
    else:
        x_flat = list(x)
    if isinstance(y, ZapTensor):
        y_flat = y._flatten(y.data)
    elif isinstance(y, ZapList):
        y_flat = list(y.elements)
    else:
        y_flat = list(y)

    n = int(len(x_flat) * float(ratio))
    x_train = ZapList(x_flat[:n])
    x_test = ZapList(x_flat[n:])
    y_train = ZapList(y_flat[:n])
    y_test = ZapList(y_flat[n:])
    return ZapList([x_train, x_test, y_train, y_test])

def _stdlib_batch(data, batch_size):
    """Split data into batches of given size."""
    if isinstance(data, ZapList):
        items = list(data.elements)
    else:
        items = list(data)
    bs = int(batch_size)
    batches = [ZapList(items[i:i+bs]) for i in range(0, len(items), bs)]
    return ZapList(batches)

def _stdlib_one_hot(indices, num_classes):
    """Convert integer indices to one-hot encoded tensors."""
    if isinstance(indices, ZapList):
        indices = indices.elements
    result = []
    for idx in indices:
        row = [0.0] * int(num_classes)
        row[int(idx)] = 1.0
        result.append(row)
    return ZapTensor(result, [len(result), int(num_classes)])

def _stdlib_argmax(data):
    """Return the index of the maximum value."""
    if isinstance(data, ZapTensor):
        flat = data._flatten(data.data)
    elif isinstance(data, ZapList):
        flat = list(data.elements)
    else:
        flat = list(data)
    return flat.index(max(flat))

def _stdlib_accuracy(predicted, targets):
    """Compute classification accuracy."""
    if isinstance(predicted, ZapTensor):
        p_flat = predicted._flatten(predicted.data)
    elif isinstance(predicted, ZapList):
        p_flat = list(predicted.elements)
    else:
        p_flat = list(predicted)
    if isinstance(targets, ZapTensor):
        t_flat = targets._flatten(targets.data)
    elif isinstance(targets, ZapList):
        t_flat = list(targets.elements)
    else:
        t_flat = list(targets)

    correct = sum(1 for p, t in zip(p_flat, t_flat) if p == t)
    return correct / len(p_flat) if p_flat else 0

def _stdlib_seed(seed):
    """Set random seed for reproducibility."""
    import random
    random.seed(int(seed))
    try:
        import numpy as np
        np.random.seed(int(seed))
    except ImportError:
        pass
    return True


# ===========================================================================
# Auth Primitives — JWT, password hashing, basic auth
# ===========================================================================

def _stdlib_jwt_encode(payload, secret, algorithm='HS256'):
    """Encode a JWT token. payload is a dict, secret is a string."""
    import hmac, hashlib, base64, json, time
    header = {'alg': str(algorithm), 'typ': 'JWT'}
    def b64url(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b'=').decode()
    def b64url_raw(data):
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()
    header_enc = b64url(header)
    payload_py = _zap_to_py(payload) if isinstance(payload, ZapDict) else payload
    if isinstance(payload_py, dict):
        payload_py['iat'] = int(time.time())
    payload_enc = b64url(payload_py)
    signing_input = f"{header_enc}.{payload_enc}"
    if algorithm == 'HS256':
        sig = hmac.new(str(secret).encode(), signing_input.encode(), hashlib.sha256).digest()
    elif algorithm == 'HS384':
        sig = hmac.new(str(secret).encode(), signing_input.encode(), hashlib.sha384).digest()
    elif algorithm == 'HS512':
        sig = hmac.new(str(secret).encode(), signing_input.encode(), hashlib.sha512).digest()
    else:
        raise RuntimeError(f"unsupported JWT algorithm: {algorithm}")
    sig_enc = b64url_raw(sig)
    return f"{header_enc}.{payload_enc}.{sig_enc}"

def _stdlib_jwt_decode(token, secret, verify=True):
    """Decode a JWT token. Returns the payload dict."""
    import hmac, hashlib, base64, json, time
    parts = str(token).split('.')
    if len(parts) != 3:
        raise RuntimeError("invalid JWT token")
    header_enc, payload_enc, sig_enc = parts
    def b64url_decode(s):
        padding = 4 - len(s) % 4
        if padding != 4:
            s += '=' * padding
        return base64.urlsafe_b64decode(s)
    if verify:
        signing_input = f"{header_enc}.{payload_enc}"
        header = json.loads(b64url_decode(header_enc))
        algorithm = header.get('alg', 'HS256')
        if algorithm == 'HS256':
            expected = hmac.new(str(secret).encode(), signing_input.encode(), hashlib.sha256).digest()
        elif algorithm == 'HS384':
            expected = hmac.new(str(secret).encode(), signing_input.encode(), hashlib.sha384).digest()
        elif algorithm == 'HS512':
            expected = hmac.new(str(secret).encode(), signing_input.encode(), hashlib.sha512).digest()
        else:
            raise RuntimeError(f"unsupported JWT algorithm: {algorithm}")
        actual = b64url_decode(sig_enc)
        if not hmac.compare_digest(expected, actual):
            raise RuntimeError("JWT signature verification failed")
    payload = json.loads(b64url_decode(payload_enc))
    if 'exp' in payload and time.time() > payload['exp']:
        raise RuntimeError("JWT token expired")
    return _py_to_zap(payload)

def _stdlib_jwt_verify(token, secret):
    """Verify a JWT token signature. Returns true if valid."""
    try:
        _stdlib_jwt_decode(token, secret, verify=True)
        return True
    except Exception:
        return False

def _stdlib_hash_password(password, algorithm='sha256'):
    """Hash a password with salt. Returns 'salt:hash' string."""
    import hashlib
    import os
    salt = os.urandom(16).hex()
    h = hashlib.new(str(algorithm))
    h.update((salt + str(password)).encode())
    return f"{salt}:{h.hexdigest()}"

def _stdlib_verify_password(password, stored):
    """Verify a password against a stored 'salt:hash'."""
    import hashlib
    parts = str(stored).split(':')
    if len(parts) != 2:
        return False
    salt, expected_hash = parts
    h = hashlib.new('sha256')
    h.update((salt + str(password)).encode())
    return h.hexdigest() == expected_hash

def _stdlib_basic_auth_encode(username, password):
    """Encode username:password for Basic Auth header."""
    import base64
    creds = f"{str(username)}:{str(password)}"
    return base64.b64encode(creds.encode()).decode()

def _stdlib_basic_auth_decode(encoded):
    """Decode a Basic Auth header value. Returns {username, password}."""
    import base64
    decoded = base64.b64decode(str(encoded)).decode()
    parts = decoded.split(':', 1)
    return ZapDict({'username': parts[0], 'password': parts[1] if len(parts) > 1 else ''})

def _stdlib_session_create(user_id, data=None):
    """Create a session dict for a user."""
    import uuid, time
    session = {
        'session_id': str(uuid.uuid4()),
        'user_id': user_id,
        'created_at': int(time.time()),
        'expires_at': int(time.time()) + 3600,
    }
    if data is not None:
        if isinstance(data, ZapDict):
            for k, v in data.entries.items():
                session[k] = v
    return ZapDict(session)

def _stdlib_session_validate(session, max_age=3600):
    """Check if a session is valid (not expired)."""
    import time
    if isinstance(session, ZapDict):
        expires = session.entries.get('expires_at', 0)
        return time.time() < expires
    return False


# ===========================================================================
# Background Jobs — Cron, Queues, Workers
# ===========================================================================

class ZapQueue:
    """Thread-safe job queue."""
    def __init__(self, name='default'):
        import threading
        self.name = name
        self.jobs = []
        self.results = {}
        self.lock = threading.Lock()
        self._counter = 0

    def add(self, fn, *args):
        import threading
        job_id = self._counter
        self._counter += 1
        with self.lock:
            self.jobs.append({'id': job_id, 'fn': fn, 'args': args, 'status': 'pending'})
        self.results[job_id] = {'status': 'pending', 'result': None, 'error': None}

        def run():
            try:
                result = fn(*args)
                self.results[job_id] = {'status': 'done', 'result': result, 'error': None}
            except Exception as e:
                self.results[job_id] = {'status': 'failed', 'result': None, 'error': str(e)}

        t = threading.Thread(target=run, daemon=True)
        t.start()
        return job_id

    def status(self, job_id):
        return self.results.get(int(job_id), {'status': 'unknown'})

    def pending_count(self):
        with self.lock:
            return sum(1 for j in self.jobs if j['status'] == 'pending')

class ZapCron:
    """Simple cron-like scheduler."""
    def __init__(self):
        import threading
        self.jobs = []
        self.running = False
        self.thread = None

    def add(self, fn, interval_seconds, name='cron_job'):
        import threading, time
        job = {'fn': fn, 'interval': float(interval_seconds), 'name': name, 'last_run': 0}
        self.jobs.append(job)

        if not self.running:
            self.running = True
            def loop():
                while self.running:
                    now = time.time()
                    for j in self.jobs:
                        if now - j['last_run'] >= j['interval']:
                            j['last_run'] = now
                            try:
                                j['fn']()
                            except Exception:
                                pass
                    time.sleep(0.1)

            self.thread = threading.Thread(target=loop, daemon=True)
            self.thread.start()
        return True

    def stop(self):
        self.running = False
        return True

    def list_jobs(self):
        return ZapList([ZapDict({'name': j['name'], 'interval': j['interval']}) for j in self.jobs])

_CRON_INSTANCES = {}
_QUEUE_INSTANCES = {}

def _stdlib_queue_create(name='default'):
    """Create a job queue."""
    q = ZapQueue(name)
    _QUEUE_INSTANCES[name] = q
    return q

def _stdlib_queue_add(q, fn):
    """Add a job to a queue."""
    if isinstance(q, ZapQueue):
        job_id = q.add(fn)
        return job_id
    raise RuntimeError("queue_add requires a queue")

def _stdlib_queue_status(q):
    """Get queue status."""
    if isinstance(q, ZapQueue):
        return ZapDict({
            'name': q.name,
            'pending': q.pending_count(),
            'total': len(q.jobs),
        })
    return ZapDict({})

def _stdlib_cron_create(name='default'):
    """Create a cron scheduler."""
    c = ZapCron()
    _CRON_INSTANCES[name] = c
    return c

def _stdlib_cron_add(c, fn, interval):
    """Add a recurring job to a cron scheduler."""
    if isinstance(c, ZapCron):
        c.add(fn, interval)
        return True
    raise RuntimeError("cron_add requires a cron scheduler")

def _stdlib_cron_stop(c):
    """Stop a cron scheduler."""
    if isinstance(c, ZapCron):
        c.stop()
        return True
    return False

def _stdlib_cron_list(c):
    """List cron jobs."""
    if isinstance(c, ZapCron):
        return c.list_jobs()
    return ZapList([])


# ===========================================================================
# AI Primitives — Prompt Templates, LLM Integration, RAG
# ===========================================================================

def _stdlib_prompt_template(template, **kwargs):
    """Render a prompt template with variables. Uses {variable} syntax."""
    t = str(template)
    for k, v in kwargs.items():
        t = t.replace('{' + str(k) + '}', str(v))
    return t

def _stdlib_llm_complete(prompt, model='gpt-3.5-turbo', api_key=None, max_tokens=1000, temperature=0.7):
    """Call an OpenAI-compatible LLM API. Returns the response text."""
    import urllib.request, json, os
    key = str(api_key) if api_key else os.environ.get('OPENAI_API_KEY', '')
    if not key:
        raise RuntimeError("No API key. Set OPENAI_API_KEY or pass api_key.")
    
    url = 'https://api.openai.com/v1/chat/completions'
    body = json.dumps({
        'model': str(model),
        'messages': [{'role': 'user', 'content': str(prompt)}],
        'max_tokens': int(max_tokens),
        'temperature': float(temperature),
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',
    })
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read().decode())
        return data['choices'][0]['message']['content']
    except Exception as e:
        raise RuntimeError(f"LLM API error: {e}")

def _stdlib_llm_chat(messages, model='gpt-3.5-turbo', api_key=None, max_tokens=1000, temperature=0.7):
    """Call an LLM with a chat message list. messages is list of {role, content} dicts."""
    import urllib.request, json, os
    key = str(api_key) if api_key else os.environ.get('OPENAI_API_KEY', '')
    if not key:
        raise RuntimeError("No API key. Set OPENAI_API_KEY or pass api_key.")
    
    if isinstance(messages, ZapList):
        msgs = [_zap_to_py(m) for m in messages.elements]
    else:
        msgs = messages
    
    url = 'https://api.openai.com/v1/chat/completions'
    body = json.dumps({
        'model': str(model),
        'messages': msgs,
        'max_tokens': int(max_tokens),
        'temperature': float(temperature),
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',
    })
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read().decode())
        return _py_to_zap(data['choices'][0]['message'])
    except Exception as e:
        raise RuntimeError(f"LLM API error: {e}")

def _stdlib_embedding(text, model='text-embedding-ada-002', api_key=None):
    """Get an embedding vector for text."""
    import urllib.request, json, os
    key = str(api_key) if api_key else os.environ.get('OPENAI_API_KEY', '')
    if not key:
        raise RuntimeError("No API key. Set OPENAI_API_KEY or pass api_key.")
    
    url = 'https://api.openai.com/v1/embeddings'
    body = json.dumps({
        'model': str(model),
        'input': str(text),
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',
    })
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
        return ZapTensor(data['data'][0]['embedding'])
    except Exception as e:
        raise RuntimeError(f"Embedding API error: {e}")

def _stdlib_cosine_similarity(a, b):
    """Compute cosine similarity between two tensors/vectors."""
    if isinstance(a, ZapTensor) and isinstance(b, ZapTensor):
        flat_a = a._flatten(a.data)
        flat_b = b._flatten(b.data)
    elif isinstance(a, ZapList):
        flat_a = list(a.elements)
        flat_b = list(b.elements) if isinstance(b, ZapList) else list(b)
    else:
        flat_a = list(a)
        flat_b = list(b)
    
    n = min(len(flat_a), len(flat_b))
    dot = sum(flat_a[i] * flat_b[i] for i in range(n))
    mag_a = sum(x**2 for x in flat_a[:n]) ** 0.5
    mag_b = sum(x**2 for x in flat_b[:n]) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

def _stdlib_rag_store(documents, collection_name='default'):
    """Store documents for RAG. Returns the collection with embeddings."""
    # Simple in-memory RAG store
    if not hasattr(_stdlib_rag_store, '_collections'):
        _stdlib_rag_store._collections = {}
    
    if collection_name not in _stdlib_rag_store._collections:
        _stdlib_rag_store._collections[collection_name] = []
    
    store = _stdlib_rag_store._collections[collection_name]
    if isinstance(documents, ZapList):
        docs = documents.elements
    else:
        docs = [documents]
    
    for doc in docs:
        if isinstance(doc, ZapDict):
            text = doc.entries.get('text', str(doc))
            metadata = doc.entries
        else:
            text = str(doc)
            metadata = {'text': text}
        store.append({'text': text, 'metadata': metadata})
    
    return ZapList([ZapDict(d) for d in store])

def _stdlib_rag_search(query, collection_name='default', top_k=3):
    """Search a RAG collection for relevant documents."""
    if not hasattr(_stdlib_rag_store, '_collections'):
        return ZapList([])
    
    store = _stdlib_rag_store._collections.get(collection_name, [])
    if not store:
        return ZapList([])
    
    # Simple keyword-based search (no API needed)
    query_lower = str(query).lower()
    scored = []
    for doc in store:
        text = doc['text'].lower()
        # Simple TF scoring
        score = sum(1 for word in query_lower.split() if word in text)
        scored.append((score, doc))
    
    scored.sort(key=lambda x: -x[0])
    results = [{'text': d['text'], 'metadata': d['metadata'], 'score': s} for s, d in scored[:int(top_k)]]
    return ZapList([ZapDict(r) for r in results])
