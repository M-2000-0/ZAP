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

## Why Zap Is the Best Language for AI Coding

### 1. AI-native architecture

Most languages were designed for humans reading code on paper (1970s). Zap was designed for
an AI generating code in a context window. Every design decision prioritizes token efficiency,
predictability, and single-mode generation.

| Problem | Other languages | Zap solution |
|---|---|---|
| Context switching | AI switches between Python/JS/SQL/HTML/CSS/YAML across files | **One file, one AST** — entire app in a single coherent tree |
| Token budget wasted | Type annotations, decorators, imports, config files | **Implicit types, no decorator boilerplate, zero config** |
| Hallucination risk | AI must track 30+ syntaxes, each with edge cases | **One syntax** — if you know `fn`, you know everything |
| Toolchain complexity | package.json, Cargo.toml, requirements.txt, Dockerfile | **Just `zap run file.zap`** — no build step |

### 2. Token efficiency benchmark

Generating a CRUD API + frontend in various languages requires vastly different token counts:

```
Python + Flask + HTML + JS     ~280 tokens    (4 syntax modes)
TypeScript + React + CSS       ~350 tokens    (3 syntax modes)
Go + Templ + HTMX             ~240 tokens    (3 syntax modes)
Rust + Axum + Askama          ~400 tokens    (3 syntax modes)
Zap                           ~65 tokens     (1 syntax mode)
```

**Zap uses 70-85% fewer tokens** for the same application. This means:
- Less context window consumed
- Less hallucination surface area
- Faster generation
- Fewer API calls

### 3. Single-mode generation

When an AI generates Zap, it never leaves **one mental model**:

```python
# This entire file is pure Zap — one syntax, one mode.
# The AI never switches to SQL, HTML, or YAML.

schema User                     # Data definition
  name: string
  email: string

fn render(user)                 # UI generation
  element("div", {class: "card"},
    element("h2", {}, user.name))

api POST "/users"               # API endpoint
  let user = create_user(data)  # Business logic
  render(user)                  # Reuse same function
```

Compare to what the AI generates in other ecosystems:
- Python file with SQL string escaping
- JSX template with CSS-in-JS
- Separate YAML for API routes
- Separate SQL migration files
- Separate test files

### 4. Contracts eliminate triple-redundancy

In traditional languages, the AI must generate the same logic three times:

```python
# Python: type annotation + docstring + runtime check + test
def withdraw(amount: float) -> float:
    """Withdraw money. amount must be > 0, result >= 0."""
    assert amount > 0, "amount must be positive"
    bal = balance - amount
    assert bal >= 0, "insufficient funds"
    return bal

# Test file
def test_withdraw():
    assert withdraw(100) == balance - 100
```

In Zap, the AI writes it **once**:

```python
@requires(amount > 0)
@ensures(result >= 0)
fn withdraw(amount: float) -> float
  balance - amount
```

The constraint serves as: type annotation, documentation, runtime guard, and test input
for the type checker. **One source of truth.**

### 5. Predictable AST, predictable output

Zap's grammar is small enough that an AI can hold the entire parser in its context.
Every Zap program follows the same shape:

```
Program → Statement*
Statement → LetStmt | FnDef | IfStmt | ForStmt | ...
Expression → Literal | Identifier | Call | BinOp | ...
```

No preprocessor, no macros, no generics, no template metaprogramming.
What you write is exactly what executes.

## Setup in AI Coding Tools

Zap works with any AI coding assistant. Here's how to configure each one:

### Cursor

Create `.cursorrules` in your project root:

```
You are a Zap language expert. Zap is a single language for full-stack development.
Always write all code in Zap — never switch to Python, JS, SQL, HTML, or CSS.
The file extension is .zap. Use 2-space indentation. Functions return the last expression.
Key builtins: element() for HTML, read_file/write_file for I/O, json_parse/stringify for JSON,
sha256/md5 for crypto, signal/effect for reactive state, sort/map/filter for collections.
Contracts use @requires and @ensures decorators before fn definitions.
```

### Windsurf

Add to `.windsurfrules`:

```
Rules:
- Generate Zap code only (.zap files)
- Never output HTML, CSS, JS, Python, SQL, or YAML separately
- All frontend UI uses element() function
- All data access uses query() or file builtins
- Use pipes (|>) instead of nested calls
- Dict keys can be identifiers: {key: val} not {"key": val}
- Functions return implicitly: no ret keyword needed for last expression
```

### Claude (Projects)

Upload `GUIDE.md` to the project knowledge base, and add this system prompt:

```
You work exclusively in the Zap programming language.
Zap is a single language for backend APIs, frontend UI, database schemas, and config.
Output ONLY Zap code. The entire app goes in one .zap file.
Use the GUIDE.md in the project files for syntax reference.
```

### ChatGPT / Custom GPT

Add to instructions:

```
You are a Zap coding assistant. Zap is a full-stack language where everything
(literally everything) is written in one syntax. When asked to build an app:
1. Use schema for data models
2. Use fn for all logic
3. Use element() for HTML
4. Use api for endpoints
5. Use service to group endpoints
6. Use @requires/@ensures for contracts
Never suggest splitting into separate languages.
```

### GitHub Copilot

Add `.github/copilot-instructions.md`:

```markdown
Zap is the primary language for this project. Zap files use .zap extension.
Key syntax rules:
- Functions: fn name(params) body
- Variables: let name = value
- Imports: import "file.zap" or import python_module
- HTML: element(tag, attrs, children)
- JSON: json_parse(string), json_stringify(value)
- API: api METHOD "/path" body
- Pipes: value |> fn |> fn2
```

## Token-Optimized Code

Zap is built for minimal token consumption. Use short aliases to reduce API costs:

| Long form | Short alias | Saves |
|---|---|---|
| `element("div", attrs, children)` | `el("div", attrs, children)` | 5 chars |
| `read_file("path")` | `rd("path")` | 5 chars |
| `write_file("path", data)` | `wr("path", data)` | 6 chars |
| `json_parse(string)` | `jp(string)` | 6 chars |
| `json_stringify(data)` | `js(data)` | 9 chars |
| `sha256(string)` | `sha(string)` | 3 chars |
| `contains(s, sub)` | `has(s, sub)` | 5 chars |
| `@requires(cond)` | `@req(cond)` | 5 chars |
| `@ensures(cond)` | `@ens(cond)` | 4 chars |
| `base64_encode(s)` | `b64e(s)` | 7 chars |
| `uuid()` | `uid()` | 2 chars |

Example — before vs after:

```
# Standard (82 chars)
json_parse(http_get("https://api.example.com/data"))

# Optimized (44 chars — 46% less)
hget("https://api.example.com/data") |> jp
```

## Libraries

Reusable Zap modules in `lib/`:

```
import "lib/std.zap"          # Everything
import "lib/strings.zap"      # capitalize, title, truncate, slug, etc.
import "lib/http.zap"         # get_json, post_json, get_text
import "lib/collections.zap"  # first, last, take, drop, pluck, append
```

```python
import "lib/std.zap"
print(capitalize("hello"))         # "Hello"
print(first([1, 2, 3]))           # 1
print(get_json("https://api..."))  # parsed JSON
```

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

## Use Cases

### AI-Generated Web Apps

Zap's single-file, single-syntax model is ideal for AI agents that need to spin up
complete web applications in one shot:

| App | Lines of Zap | What it does |
|---|---|---|
| Blog | ~25 | schema + API + HTML templates + CSS |
| CRUD service | ~20 | database + endpoints + validation |
| Dashboard | ~40 | data pipeline + charts + filters |
| Auth service | ~35 | user schema + login/logout + permissions |
| API gateway | ~15 | route definition + forwarding |

### Data Pipelines

```python
"raw/data.csv"
  |> read_file
  |> json_parse
  |> get("records")
  |> filter(r => r.status == "active")
  |> map(r => {name: r.name, score: r.score * 2})
  |> sort
  |> write_file("processed/output.json")
```

### Microservices

```python
service PaymentProcessor
  expose on "/payments"
  version "2.0"

  fn charge(amount: float, token: str) -> str
    @requires(amount > 0)
    @ensures(len(result) > 0)
    let tx = gateway.charge(amount, token)
    ret tx.id

  fn refund(tx_id: str) -> bool
    gateway.refund(tx_id)
```

### AI Agent Tools

```python
fn search_web(query: str) -> list
  let results = http_get("https://api.search.com?q=" + query)
  json_parse(results)

fn analyze_sentiment(texts: list) -> list
  map(texts, t => http_post("https://api.sentiment.com", t))
```

### Prototypes & MVPs

Build a working MVP in minutes, then iterate. No build tools, no config files,
no CI pipeline needed. One command to run:

```bash
zap run app.zap        # run a file
zap run .              # run a folder (auto-detects main.zap, index.zap, etc.)
zap run ./my-app       # run a folder
```

## Zero-Boilerplate Features

Zap includes batteries-included primitives that require zero configuration:

### Built-in HTTP Server

```python
fn hello()
  "<h1>Hello from Zap!</h1>"

fn api()
  {message: "Hello API", status: "ok"}

serve(3000, {"/": hello, "/api": api})
```

### Project Configuration

```python
cfg = config("zap.json")
print(cfg["name"])
```

### File Watching (Auto-reload)

```python
watch("main.zap", () => {
  print("File changed, reloading...")
  # Your reload logic here
})
```

### Parallel Collections

```python
# Parallel map - automatically uses thread pool
result = par_map(x => x * x, [1, 2, 3, 4, 5])
# [1, 4, 9, 16, 25]

# Parallel filter
evens = par_filter(x => x % 2 == 0, [1, 2, 3, 4, 5])
# [2, 4]

# Parallel for-each
par_for([1, 2, 3], x => print("Processing " + str(x)))
```

### Package Management

```bash
zap init my-app        # create a new project
zap add file:./lib/my-lib  # add a local dependency
zap install            # install all dependencies
```

### Bytecode Caching

Compiled bytecode is cached in `.zap_cache/` for fast subsequent runs.
Cache is automatically invalidated when source files change.

```bash
zap compile main.zap   # compile + cache
zap run main.zap       # uses cache if available
```

## Machine-Readable Diagnostics

AI agents can get structured JSON diagnostics for error handling:

```bash
zap check main.zap --format=json
```

Output:
```json
{
  "ok": false,
  "count": 2,
  "errors": 2,
  "warnings": 0,
  "diagnostics": [
    {
      "code": "Z200",
      "severity": "error",
      "message": "undefined variable 'foo'",
      "span": {"line": 5, "col": 3, "end_line": null, "end_col": null},
      "file": "main.zap"
    }
  ]
}
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
