# builtins.zap — All standard library builtins defined in Zap syntax
# These wrap the Python runtime builtins

import "tokens.zap"

# File I/O
fn read_file(path):
    ret __builtin_read_file(path)

fn write_file(path, content):
    __builtin_write_file(path, content)
    ret none

fn append_file(path, content):
    __builtin_append_file(path, content)
    ret none

fn remove(path):
    __builtin_remove(path)
    ret none

fn file_size(path):
    ret __builtin_file_size(path)

fn file_exists(path):
    ret __builtin_file_exists(path)

fn list_dir(path="."):
    ret __builtin_list_dir(path)

# JSON
fn json_parse(text):
    ret __builtin_json_parse(text)

fn json_stringify(value):
    ret __builtin_json_stringify(value)

fn json_load(path):
    ret __builtin_json_load(path)

fn json_save(path, data):
    __builtin_json_save(path, data)
    ret none

# HTTP
fn http_get(url, headers=none):
    ret __builtin_http_get(url, headers)

fn http_post(url, data=none, json_body=none):
    ret __builtin_http_post(url, data, json_body)

fn http_post_json(url, data):
    ret __builtin_http_post_json(url, data)

fn http_put(url, data=none):
    ret __builtin_http_put(url, data)

fn http_delete(url):
    ret __builtin_http_delete(url)

# String helpers
fn str_upper(s):
    ret s.upper() if isinstance(s, str) else str(s).upper()

fn str_lower(s):
    ret s.lower() if isinstance(s, str) else str(s).lower()

fn str_strip(s):
    ret s.strip() if isinstance(s, str) else str(s).strip()

fn str_replace(s, old, new):
    ret str(s).replace(str(old), str(new))

fn str_split(s, sep=" "):
    ret str(s).split(str(sep))

fn str_join(sep, items):
    if isinstance(items, ZapList):
        ret str(sep).join([str(x.value if isinstance(x, ZapValue) else x) for x in items.elements])
    ret str(sep).join([str(items)])

fn str_len(s):
    ret len(str(s))

fn str_contains(s, sub):
    ret str(sub) in str(s)

fn str_index(s, sub):
    ret str(s).index(str(sub)) if str(sub) in str(s) else -1

fn str_startswith(s, prefix):
    ret str(s).startswith(str(prefix))

fn str_endswith(s, suffix):
    ret str(s).endswith(str(suffix))

fn str_isblank(s):
    ret str(s).strip() == ""

fn str_to_slug(s):
    import re as _re
    ret _re.sub(r"[^a-z0-9]+", "-", str(s).lower().strip("-"))

# Number helpers
fn abs_val(x):
    ret abs(x.value if isinstance(x, ZapValue) else x)

fn round_val(x, digits=0):
    ret round(x.value if isinstance(x, ZapValue) else x, digits)

fn int_val(x):
    ret int(x.value if isinstance(x, ZapValue) else x)

fn float_val(x):
    ret float(x.value if isinstance(x, ZapValue) else x)

fn min_val(*args):
    values = [a.value if isinstance(a, ZapValue) else a for a in args]
    ret min(values)

fn max_val(*args):
    values = [a.value if isinstance(a, ZapValue) else a for a in args]
    ret max(values)

fn sum_val(*args):
    values = [a.value if isinstance(a, ZapValue) else a for a in args]
    ret sum(values)

fn pow_val(base, exp):
    ret base ** exp

fn sqrt_val(x):
    import math as _math
    ret _math.sqrt(x.value if isinstance(x, ZapValue) else x)

fn floor_val(x):
    import math as _math
    ret _math.floor(x.value if isinstance(x, ZapValue) else x)

fn ceil_val(x):
    import math as _math
    ret _math.ceil(x.value if isinstance(x, ZapValue) else x)

# List helpers
fn list_len(lst):
    if isinstance(lst, ZapList):
        ret len(lst.elements)
    ret 0

fn list_append(lst, item):
    if isinstance(lst, ZapList):
        lst.elements.append(item)
    ret lst

fn list_first(lst):
    if isinstance(lst, ZapList) and len(lst.elements) > 0:
        ret lst.elements[0]
    ret none

fn list_last(lst):
    if isinstance(lst, ZapList) and len(lst.elements) > 0:
        ret lst.elements[len(lst.elements) - 1]
    ret none

fn list_reverse(lst):
    if isinstance(lst, ZapList):
        ret ZapList(lst.elements[::-1])
    ret ZapList([])

fn list_sort(lst):
    if isinstance(lst, ZapList):
        ret ZapList(sorted(lst.elements))
    ret ZapList([])

fn list_unique(lst):
    if isinstance(lst, ZapList):
        seen = {}
        result = []
        for item in lst.elements:
            key = str(item.value if isinstance(item, ZapValue) else item)
            if key not in seen:
                seen[key] = true
                result.append(item)
        ret ZapList(result)
    ret ZapList([])

fn list_map(lst, fn):
    if isinstance(lst, ZapList):
        result = []
        for item in lst.elements:
            result.append(fn(item))
        ret ZapList(result)
    ret ZapList([])

fn list_filter(lst, fn):
    if isinstance(lst, ZapList):
        result = []
        for item in lst.elements:
            if is_truthy(fn(item)):
                result.append(item)
        ret ZapList(result)
    ret ZapList([])

fn list_flatten(lst):
    if isinstance(lst, ZapList):
        result = []
        for item in lst.elements:
            if isinstance(item, ZapList):
                for sub in item.elements:
                    result.append(sub)
            else:
                result.append(item)
        ret ZapList(result)
    ret ZapList([])

fn list_reduce(lst, fn, initial=none):
    if isinstance(lst, ZapList):
        acc = initial
        for item in lst.elements:
            if acc == none:
                acc = item
            else:
                acc = fn(acc, item)
        ret acc
    ret none

# Dict helpers
fn dict_len(d):
    if isinstance(d, ZapDict):
        ret len(d.entries)
    ret 0

fn dict_keys(d):
    if isinstance(d, ZapDict):
        ret ZapList([ZapValue(k) for k in d.entries.keys()])
    ret ZapList([])

fn dict_values(d):
    if isinstance(d, ZapDict):
        ret ZapList([ZapValue(v) for v in d.entries.values()])
    ret ZapList([])

fn dict_get(d, key, default=none):
    if isinstance(d, ZapDict):
        val = d.entries.get(str(key))
        ret ZapValue(val) if val != none else default
    ret default

fn dict_has(d, key):
    if isinstance(d, ZapDict):
        ret str(key) in d.entries
    ret false

fn dict_merge(a, b):
    if isinstance(a, ZapDict) and isinstance(b, ZapDict):
        result = {}
        for k in a.entries:
            result[k] = a.entries[k]
        for k in b.entries:
            result[k] = b.entries[k]
        ret ZapDict(result)
    ret ZapDict({})

# Crypto
fn sha256(text):
    import hashlib as _hashlib
    ret _hashlib.sha256(str(text).encode()).hexdigest()

fn b64encode(text):
    import base64 as _base64
    ret _base64.b64encode(str(text).encode()).decode()

fn b64decode(text):
    import base64 as _base64
    ret _base64.b64decode(str(text)).decode()

fn random_uuid():
    import uuid as _uuid
    ret str(_uuid.uuid4())

fn random_str(length=16):
    import string as _string, random as _random
    chars = _string.ascii_letters + _string.digits
    ret "".join([_random.choice(chars) for _ in range(length)])

# Environment
fn env_get(key):
    import os as _os
    ret _os.environ.get(key)

fn env_set(key, value):
    import os as _os
    _os.environ[key] = str(value)
    ret none

fn env_has(key):
    import os as _os
    ret key in _os.environ

fn env_list():
    import os as _os
    ret ZapList([ZapValue(k + "=" + v) for k, v in _os.environ.items()])

# Concurrency
fn sleep(secs):
    import time as _time
    _time.sleep(float(secs))
    ret none

# System
fn exit(code=0):
    import sys as _sys
    _sys.exit(int(code))

# Platform detection
fn platform():
    import sys as _sys
    ret _sys.platform

# Math
fn random_val(min=0, max=1):
    import random as _random
    ret _random.uniform(float(min), float(max))

fn random_int(min=0, max=100):
    import random as _random
    ret _random.randint(int(min), int(max))

fn random_choice(lst):
    import random as _random
    if isinstance(lst, ZapList):
        ret _random.choice(lst.elements)
    ret none

fn random_shuffle(lst):
    import random as _random
    if isinstance(lst, ZapList):
        result = lst.elements[:]
        _random.shuffle(result)
        ret ZapList(result)
    ret ZapList([])

fn seed_random(seed=none):
    import random as _random
    if seed != none:
        _random.seed(int(seed.value if isinstance(seed, ZapValue) else seed))
    else:
        _random.seed()
    ret none

# Date/Time
fn now():
    import datetime as _datetime
    ret str(_datetime.datetime.now())

fn timestamp():
    import time as _time
    ret _time.time()

fn datetime_add(date_str, days):
    import datetime as _datetime
    dt = _datetime.datetime.fromisoformat(str(date_str))
    ret (dt + _datetime.timedelta(days=int(days))).isoformat()

# Range
fn range_val(start=0, stop=0, step=1):
    if stop == 0 and step == 1:
        stop = start
        start = 0
    ret ZapRange(start, stop, step)

# Iteration helpers
fn enumerate(items, start=0):
    if isinstance(items, ZapList):
        result = []
        i = int(start)
        for item in items.elements:
            result.append(ZapDict({"index": i, "value": item}))
            i = i + 1
        ret ZapList(result)
    ret ZapList([])

fn zip_lists(*lists):
    if len(lists) == 0:
        ret ZapList([])
    min_len = len(lists[0].elements) if isinstance(lists[0], ZapList) else 0
    for lst in lists:
        if isinstance(lst, ZapList):
            min_len = min(min_len, len(lst.elements))
    result = []
    for i in range(min_len):
        entry = []
        for lst in lists:
            entry.append(lst.elements[i] if isinstance(lst, ZapList) else lst)
        result.append(ZapList(entry))
    ret ZapList(result)

fn reverse_iter(items):
    if isinstance(items, ZapList):
        ret ZapList(items.elements[::-1])
    ret ZapList([])

fn enumerate_list(items, start=0):
    return enumerate(items, start)

# Type helpers
fn type_name(value):
    if isinstance(value, ZapValue):
        ret value.type_name if hasattr(value, "type_name") else "value"
    ret type(value).__name__

fn is_number(value):
    ret isinstance(value, int) or isinstance(value, float)

fn is_string(value):
    ret isinstance(value, str)

fn is_list(value):
    ret isinstance(value, ZapList)

fn is_dict(value):
    ret isinstance(value, ZapDict)

fn is_bool(value):
    ret isinstance(value, bool)

fn is_none(value):
    ret value == none

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