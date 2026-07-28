# Zap Language Specification v0.1

## Comments

```
# This is a comment
# Comments run from # to end of line
```

## Variables

```zap
let x = 42            # Immutable binding
let name = "Zap"      # String
let flag = true       # Boolean
let empty = none      # Null value
```

## Data Types

### Primitives
- **Integers**: `42`, `-7`, `0`
- **Floats**: `3.14`, `-0.5`
- **Strings**: `"hello"`, `'world'`
- **Booleans**: `true`, `false`
- **None**: `none`

### Collections
```zap
let nums = [1, 2, 3]              # List
let pair = ["key", "value"]       # List (use as tuple)
let name_at = ["Alice": 90]       # Dict
```

## Operators

### Arithmetic
`+` `-` `*` `/` `%` (modulo) `**` (power)

### Comparison
`==` `!=` `<` `>` `<=` `>=`

### Logical
`and` `or` `not`

### Assignment
`=` `+=` `-=` `*=` `/=`

## Control Flow

### If/Else
```zap
if x > 0:
  print("positive")
el: if x == 0:
  print("zero")
el:
  print("negative")
```

### While Loop
```zap
let i = 0
while i < 10:
  print(i)
  i = i + 1
```

### For Loop
```zap
for item in [1, 2, 3]:
  print(item)

for i in range(5):
  print(i)
```

### Break and Continue
```zap
while true:
  let val = get_input()
  if val == "quit":
    break
  if val == "skip":
    continue
  process(val)
```

### Return
```zap
fn add(a, b):
  ret a + b
```

## Functions

```zap
fn greet(name):
  print("Hello, " + name)

fn greet_with_default(name, greeting="Hi"):
  print(greeting + ", " + name)

greet("World")
greet_with_default("Alice")
greet_with_default("Bob", "Hey")
```

## Classes

```zap
class Point:
  fn init(self, x, y):
    self.x = x
    self.y = y

  fn distance(self, other):
    let dx = self.x - other.x
    let dy = self.y - other.y
    ret sqrt(dx * dx + dy * dy)

  fn to_string(self):
    ret "(" + str(self.x) + ", " + str(self.y) + ")"

let p = Point(3, 4)
print(p.to_string())
```

### Inheritance
```zap
class Animal:
  fn init(self, name):
    self.name = name

  fn speak(self):
    ret "..."

class Dog(Animal):
  fn speak(self):
    ret self.name + " says Woof!"
```

## String Operations

```zap
let s = "Hello, World!"
len(s)              # 12
s[0]                # "H"
s[0:5]              # "Hello"
"hello".upper()     # "HELLO"
"HELLO".lower()     # "hello"
"hello world".split(" ")  # ["hello", "world"]
"a,b,c".split(",")       # ["a", "b", "c"]
["a", "b"].join(",")     # "a,b"
"hello".replace("l", "r")  # "herro"
```

## List Operations

```zap
let lst = [1, 2, 3]
lst.append(4)       # [1, 2, 3, 4]
lst.remove(0)       # removes element at index 0
len(lst)            # length
lst[0]              # first element
lst[-1]             # last element
```

## Dict Operations

```zap
let d = ["name": "Alice", "age": 30]
d["name"]           # "Alice"
d["email"] = "a@b.com"
d["email"]          # "a@b.com"
```

## Built-in Functions

### I/O
| Function | Description |
|----------|-------------|
| `print(...)` | Print to stdout |
| `say(...)` | Alias for print |
| `show(...)` | Alias for print |
| `ask(prompt)` | Read input from stdin |

### Type Conversion
| Function | Description |
|----------|-------------|
| `str(x)` | Convert to string |
| `int(x)` | Convert to integer |
| `float(x)` | Convert to float |
| `list(x)` | Convert to list |
| `type(x)` | Get type name string |
| `isinstance(obj, cls)` | Type check |

### Math
| Function | Description |
|----------|-------------|
| `abs(x)` | Absolute value |
| `max(a, b)` | Maximum |
| `min(a, b)` | Minimum |
| `sum(lst)` | Sum of list |
| `round(x)` | Round to integer |
| `sqrt(x)` | Square root |
| `exp(x)` | e^x |
| `log(x)` | Natural log |
| `sin(x)` | Sine |
| `cos(x)` | Cosine |
| `floor(x)` | Floor |
| `ceil(x)` | Ceiling |

### Collections
| Function | Description |
|----------|-------------|
| `len(x)` | Length of string/list |
| `range(n)` | Generate [0..n-1] |
| `range(start, end)` | Generate [start..end-1] |
| `map(list, fn)` | Map function over list |
| `filter(list, fn)` | Filter list by predicate |
| `append(list, item)` | Append (standalone form) |

### Random
| Function | Description |
|----------|-------------|
| `random()` | Random float [0, 1) |
| `randint(a, b)` | Random integer [a, b] |

### Time
| Function | Description |
|----------|-------------|
| `now()` | Current datetime string |
| `today()` | Current date string |
| `wait(secs)` | Sleep for seconds |

### Error Handling
| Function | Description |
|----------|-------------|
| `raise(msg)` | Raise a Zap error |
| `exit()` | Exit the program |

### JSON/IO
| Function | Description |
|----------|-------------|
| `json_parse(s)` | Parse JSON string |
| `json_stringify(x)` | To JSON string |
| `json_load(path)` | Load JSON file |
| `json_save(path, data)` | Save JSON file |
| `csv_load(path)` | Load CSV file |
| `csv_save(path, data)` | Save CSV file |

### HTTP
| Function | Description |
|----------|-------------|
| `http_get(url)` | HTTP GET request |
| `http_post(url, data)` | HTTP POST request |

### HTML/Web
| Function | Description |
|----------|-------------|
| `element(tag, attrs, children)` | Create HTML element |
| `html(...)` | Render HTML |
| `render(...)` | Render HTML |
| `web_fetch(url)` | Fetch URL content |

### Database
| Function | Description |
|----------|-------------|
| `db_open(path)` | Open SQLite database |
| `db_query(db, sql)` | Execute query |
| `db_query_one(db, sql)` | Execute query, return one |
| `db_exec(db, sql)` | Execute statement |
| `db_close(db)` | Close database |

### Parallelism
| Function | Description |
|----------|-------------|
| `pmap(fn, items)` | Parallel map |
| `parallel(*fns)` | Run functions in parallel |
| `par_map(fn, items)` | Parallel map |
| `par_filter(fn, items)` | Parallel filter |
| `retry(fn, retries, delay)` | Retry on failure |

### Tensor/ML
| Function | Description |
|----------|-------------|
| `tensor(data, shape)` | Create tensor |
| `zeros(*shape)` | Zero tensor |
| `ones(*shape)` | Ones tensor |
| `reshape(t, *dims)` | Reshape tensor |
| `dense(input, output)` | Dense layer |

## Reserved Keywords

These words are reserved and cannot be used as identifiers:

```
fn class if el: for in while ret break continue
let mut and or not true false none
import from as expose
match test doc check expect
type enum version channel schema
api service database concurrent
self
```

## Syntax Rules

1. **Indentation**: Use 2 spaces for block indentation
2. **Comments**: Lines starting with `#`
3. **No braces**: Blocks use `:` and indentation
4. **No semicolons**: Statements end at line break
5. **`el:` not `else`**: Else uses `el:` (same indent as `if`)
6. **`el: if` not `elif`**: Else-if is `el:` then `if` on the next line (same indent)
7. **`ret` not `return`**: Return keyword is `ret`
8. **`fn` not `function`**: Function keyword is `fn`
9. **`and`/`or`/`not`**: Not `&&`/`||`/`!`
10. **`self` not `this`**: Instance reference is `self`
11. **`none` not `null`**: Null value is `none`
12. **No `*args`**: Use explicit params with defaults
13. **No `in` outside `for`**: `in` only valid in `for` loops
14. **Dict membership**: Use `d[key] == none` to test key existence
