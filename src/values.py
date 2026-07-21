import math
import random
from .environment import Environment

class ZapType:
    pass

class ZapObject(ZapType):
    def __init__(self, methods=None, fields=None, base=None):
        self.methods = methods or {}
        self.fields = fields or {}
        self.base = base

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
    def __init__(self, data, shape=None):
        self.data = data
        self.shape = shape or self._infer_shape(data)
        if self.shape and len(self.shape) > 1 and not isinstance(self.data[0], list):
            self.data = self._unflatten(self.data, list(self.shape))

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
            return [x for item in d for x in self._flatten(item)]
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
        'print': ZapBuiltin(lambda *args: print(*[str(a) for a in args]), 'print'),
        'len': ZapBuiltin(lambda x: _builtin_len(x), 'len'),
        'range': ZapBuiltin(lambda *a: _builtin_range(*a), 'range'),
        'int': ZapBuiltin(lambda x: int(x), 'int'),
        'float': ZapBuiltin(lambda x: float(x), 'float'),
        'str': ZapBuiltin(lambda x: str(x), 'str'),
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
        'say': ZapBuiltin(lambda *args: print(*[str(a) for a in args]), 'say'),
        'show': ZapBuiltin(lambda *args: print(*[str(a) for a in args]), 'show'),
        'ask': ZapBuiltin(lambda prompt='': input(str(prompt)), 'ask'),
        'now': ZapBuiltin(lambda: __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'now'),
        'wait': ZapBuiltin(lambda secs: __import__('time').sleep(secs), 'wait'),
        'clear': ZapBuiltin(lambda: __import__('os').system('cls' if __import__('os').name == 'nt' else 'clear'), 'clear'),
        'today': ZapBuiltin(lambda: __import__('datetime').date.today().strftime('%Y-%m-%d'), 'today'),
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

    # Dict helpers
    env.define('has_key', ZapBuiltin(lambda d, k: k in (d.entries if isinstance(d, ZapDict) else d), 'has_key'))

    # --- Short aliases (token optimization) ---
    short = {
        'el': 'element',           # element(tag, attrs, children)
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
    if Evaluator._current:
        return Evaluator._current.env.get(str(name))
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
                    __import__('time').sleep(float(delay))
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
    __import__('sys').exit(int(code))
def _stdlib_sleep(secs):
    __import__('time').sleep(float(secs))
    return True
def _stdlib_time():
    return __import__('time').time()

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
        seen = []
        for e in items.elements:
            if e not in seen:
                seen.append(e)
        return ZapList(seen)
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
    """Load JSON config from zap.json (or a custom path)."""
    import os, json
    if path is None:
        path = "zap.json"
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


def _py_to_zap(obj):
    if isinstance(obj, dict):
        return ZapDict({_py_to_zap(k): _py_to_zap(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return ZapList([_py_to_zap(e) for e in obj])
    if isinstance(obj, tuple):
        return ZapList([_py_to_zap(e) for e in obj])
    return obj

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
