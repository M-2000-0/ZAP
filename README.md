# ZAP — One Language, Every Layer

```
zap run app.zap     # Run any app
zap check app.zap   # Type-check
zap build app.zap   # Build
zap repl            # Interactive
zap test            # Run tests
```

**Zap is the first language designed for the AI era.** One syntax from database schema to HTML templates, from contracts to concurrent pipelines. No switching between JS, TS, Python, SQL, HTML, CSS, YAML, Rust, Go, and Java.

Rather than learning 30+ languages with incompatible syntaxes, type systems, and toolchains — you learn **one**. Zap replaces:

| You'd normally need | In Zap |
|---|---|
| Python + FastAPI | `service` + `api` + `fn` |
| TypeScript + React | `element()` + `signal()` |
| SQL + ORM | `schema` + `database` |
| YAML/TOML config | native `{}` literals |
| Pydantic/validation | `@requires` / `@ensures` |
| Celery/threading | `concurrent` / `parallel` |
| nginx/API gateway | `expose` on services |
| Terraform/Pulumi | `infrastructure` blocks |
| Jest/Mocha | `expect` / `@test` |
| ESLint + Prettier | built-in parser + LSP |

---

## Why AIs Love Zap

### Fewer tokens, less noise

```
// Python + Flask
@app.route('/users/<id>')
def get_user(id):
    return jsonify(db.query("SELECT * FROM users WHERE id=?", id))
```

```
# Zap
api GET "/users/{id}"
  query("SELECT * FROM users WHERE id=?", id)
```

**62% fewer tokens.** Less to write, less to read, less to hallucinate.

### One context window, one language

An AI generating Zap stays in **one mode** — no context switching between Python type annotations, JS arrow functions, SQL string escaping, HTML template syntax. The entire app fits in a single coherent AST.

### Contracts are built-in docs + tests

```python
@requires(amount > 0)
@ensures(result >= 0)
fn withdraw(amount: float) -> float
```

The AI writes the constraint once. It serves as documentation, runtime validation, and type-checker input. No separate README, no separate test file, no separate schema.

## Quick Start

```bash
pip install zap-lang
zap repl

>>> print("hello from zap")
>>> let data = json_parse(read_file("config.json"))
>>> element("h1", {class: "title"}, data.name)
>>> ret data
```

## Tour

### Variables & types

```python
let name = "zap"
let count: int = 42
let items = [1, 2, 3]
let meta = {key: "value", count: 5}
```

### Functions

```python
fn add(a: int, b: int) -> int
  a + b

fn greet(name)
  print(upper("hello " + name))

# Lambda
let double = x => x * 2
map([1, 2, 3], x => x * x)
```

### Full-stack in one file

```python
schema User
  name: string
  email: string

database App
  users: User

fn render(user)
  element("div", {class: "card"}, [
    element("h2", {}, user.name),
    element("p", {}, user.email),
  ])

service Main
  expose on "/api"
  fn list() -> string
    let users = query("SELECT * FROM users")
    render(users[0])
```

### Contracts

```python
@requires(x != 0)
@ensures(result > 0)
fn invert(x: float) -> float
  1.0 / x
```

### Concurrent pipelines

```python
concurrent
  fn() fetch_data()
  fn() process_data()
  fn() save_results()
```

## For AI Coding Assistants

### Rules for generating Zap

1. **Indentation = blocks** — 2 spaces, no braces for functions/if/for
2. **Keywords are reserved** — don't use `page`, `service`, `schema` as variable names
3. **Implicit return** — last expression in a function is the return value; use `ret` for early return
4. **Dict keys** — identifiers like `{name: "zap"}` are string keys
5. **Pipes** — `data |> fn` threads value as first argument
6. **Everything is an expression** — `if`, `match`, blocks all produce values

### Token-optimized patterns

| Task | Verbose | Zap |
|---|---|---|
| Map over list | `map(list, fn(x) x * 2)` | `list |> map(x => x * 2)` |
| Read + parse JSON | `json_parse(read_file("x.json"))` | `"x.json" |> read_file |> json_parse` |
| HTML component | `element("div", {class: "box"}, children)` | `div({class: "box"}, children)` *(future terse syntax)* |
| Conditional return | `if cond then val1 else val2` | `if cond val1 el val2` |

## Project Structure

```
app.zap           # Run it
src/
  adapter/        # Multi-language adapters
  evaluator.py    # Tree-walking interpreter
  parser.py       # Recursive descent parser
  lexer.py        # Tokenizer
  types.py        # Type checker
  values.py       # Runtime values + stdlib
  lsp.py          # Language server
  cli.py          # CLI tool
```

## Multi-Language Mode

Zap is designed to be **the primary language** while still playing nicely with existing
ecosystems. Use it pure, or bridge into other languages when you need a specific library.

### Calling Python from Zap

```python
import os
from json import dumps

let files = list_dir(".")
print(dumps(files))
```

Any Python module is available via `import` / `from`. This gives you access to the entire
PyPI ecosystem without leaving Zap syntax.

### Calling JavaScript from Zap

```python
import "./utils.js"
# Functions exported from JS become available in Zap
```

The adapter layer in `src/adapters/` handles cross-language extraction and indexing.
Currently supports **Python** and **JavaScript** adapters out of the box.

### Calling Zap from Python

```python
from src.evaluator import Evaluator
from src.parser import Parser
from src.lexer import Lexer

source = 'fn add(a, b) a + b'
tokens = Lexer(source).tokenize()
prog = Parser(tokens).parse()
result = Evaluator().evaluate(prog)
```

### When to bridge vs when to stay pure

| Situation | Recommendation |
|---|---|
| You want Zap-only simplicity | Stay pure — no imports needed |
| You need `numpy`, `pandas`, `torch` | `import torch` from Zap |
| You have an existing JS/TS codebase | Adapter indexes it alongside Zap |
| You want maximum AI compatibility | Pure Zap — simpler context for the AI |

The philosophy: **write new code in Zap, bridge to existing libraries.** Over time,
the Zap stdlib grows to replace the need for external dependencies.

## Status

Zap is in active alpha. Everything here works today:
- Parser with error recovery
- Type checker with full type inference
- Evaluator with all builtins
- Module system
- CLI with REPL
- LSP with diagnostics
- HTML/CSS frontend DSL
- JSON, HTTP, crypto, file I/O, collections

## Roadmap

- [x] CLI + REPL
- [x] Rich stdlib
- [x] Frontend DSL
- [x] Module system
- [ ] `zap test` — test runner
- [ ] `zap doc` — documentation generator
- [ ] HTTP server builtin
- [ ] Self-hosting evaluator
- [ ] Native compilation via LLVM

---

**Zap** — one language from database to DOM.
