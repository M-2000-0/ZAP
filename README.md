# Zpx — AI-Native Programming Language

> **One language. One syntax. Zero boilerplate.**  
> A programming language designed for AI code generation.

[![PyPI](https://img.shields.io/pypi/v/zpx-lang?label=zpx-lang&color=blue)](https://pypi.org/project/zpx-lang/)
[![Python](https://img.shields.io/pypi/pyversions/zpx-lang?color=blue)](https://pypi.org/project/zpx-lang/)
[![License](https://img.shields.io/github/license/M-2000-0/ZPX?color=blue)](LICENSE)
[![Tests](https://github.com/M-2000-0/ZPX/actions/workflows/test.yml/badge.svg)](https://github.com/M-2000-0/ZPX/actions)
[![GitHub stars](https://img.shields.io/github/stars/M-2000-0/ZPX?style=social)](https://github.com/M-2000-0/ZPX/stargazers)

---

## Why Zpx?

**By 2027, 80% of code will be AI-generated.**  
Languages designed for humans reading printed code (Python 1991, JavaScript 1995, Go 2009) become legacy. Zpx is designed for the world where AI writes most of the code.

### The Problem

Today's AI writes code in **6+ languages** for one app:

| Layer | Language | Syntax Overhead |
|-------|----------|-----------------|
| Backend | Python | `def func():` |
| Frontend | JavaScript | `function func() {}` |
| Database | SQL | `SELECT * FROM...` |
| Config | YAML | `key: value` |
| Styles | CSS | `body { ... }` |
| Types | TypeScript | `x: number` |

### The Solution

**Zpx replaces them with one syntax:**

```zpx
schema User:
  id: int
  name: str
  email: str

api GET "/users/{id}":
  let user = db_row("SELECT * FROM users WHERE id = ?", [id])
  ret user

fn render_user(user):
  element("article", {class: "card"}, [
    element("h2", {}, user.name),
    element("p", {}, user.email),
  ])
```

**One file. One language. Zero config. No build step.**

---

## Key Features (Implemented)

| Feature | Status | Details |
|---------|--------|---------|
| **Self-Hosting** | ✅ | ~95% of interpreter written in Zpx (`self_host/`) |
| **Parser + Interpreter** | ✅ | Recursive descent, 300K+ LOC in `src/` |
| **Type System** | ✅ | Compound types, unions, type aliases, inference |
| **Contracts** | ✅ | `@requires`, `@ensures`, `@invariant` (design by contract) |
| **Pattern Matching** | ✅ | `match` with wildcards, guards |
| **Auto-Deploy DB** | ✅ | `db_auto()` detects Vercel/Netlify/Render/Fly/Heroku/Replit |
| **LSP Server** | ✅ | `zpx lsp` — hover, goto-def, diagnostics, symbols |
| **Package Manager** | ✅ | `zpx init`, `zpx add`, `zpx install`, `zpx.json` |
| **WASM Transpiler** | ✅ | `wasm/` compiles Zpx → JavaScript |
| **Time-Travel Debug** | ✅ | Checkpoints, rewind, query, diff |
| **VS Code Extension** | ✅ | Syntax, snippets, language config |
| **Tests** | ✅ | 166 passing (`pytest tests/ -v`) |

---

## Quick Start

```bash
# Install from PyPI
pip install zpx-lang

# Run your first program
echo 'print("Hello from Zpx!")' > hello.zpx
zpx run hello.zpx

# Try examples
zpx run examples/hello.zpx
zpx run examples/blog.zpx
zpx run examples/rest_api.zpx
zpx run examples/data_pipeline.zpx
zpx run examples/ai_native.zpx
```

**From source:**

```bash
git clone https://github.com/M-2000-0/ZPX.git
cd ZPX
python -m src run examples/hello.zpx
```

---

## Language Tour

### Variables & Types

```zpx
let x = 42              # int
let name = "Zpx"        # str
let flag = true         # bool
let empty = none        # null
let nums = [1, 2, 3]    # list
let user = ["name": "Alice", "age": 30]  # dict
```

### Functions (short keywords: `fn`, `ret`)

```zpx
fn greet(name):
  ret "Hello, " + name + "!"

fn greet_with_default(name, greeting="Hi"):
  print(greeting + ", " + name)

# Implicit return (last expression)
fn double(x) x * 2
```

### Control Flow (`el` not `else`, `ret` not `return`)

```zpx
fn classify(x):
  if x > 0: ret "positive"
  el: if x < 0: ret "negative"
  el: ret "zero"

for item in [1, 2, 3]:
  print(item)
```

### Pattern Matching

```zpx
match status:
  "active": print("User is active")
  "inactive": print("User is inactive")
  "banned": print("User is banned")
  _: print("Unknown status")
```

### Contracts (Design by Contract)

```zpx
fn withdraw(amount: float):
  requires amount > 0
  requires balance >= amount
  ensures balance >= 0
  
  balance = balance - amount
```

### Classes & Inheritance

```zpx
class Animal:
  fn init(self, name):
    self.name = name
  
  fn speak(self):
    ret "..."

class Dog(Animal):
  fn speak(self):
    ret self.name + " says Woof!"

let d = Dog("Rex")
print(d.speak())  # "Rex says Woof!"
```

### Comprehensions

```zpx
let nums = [1, 2, 3, 4, 5]
let doubled = [x * 2 for x in nums]
let evens = [x for x in nums if x % 2 == 0]
let squares = {x: x * x for x in nums}
```

### Built-ins (248+, no imports needed)

```zpx
# HTTP
http_get("https://api.example.com/data")
http_post(url, json_body={"key": "value"})

# JSON
json_parse('{"name": "Zpx"}')
json_stringify(data)

# Database (SQLite, auto-deploys on Vercel/Netlify/Render)
db_auto("my_app"):
  users:
    id: "TEXT PRIMARY KEY"
    name: "TEXT"
    email: "TEXT UNIQUE"

db_insert("users", {id: "1", name: "Alice", email: "alice@example.com"})
let user = db_row("SELECT * FROM users WHERE id = ?", ["1"])

# Crypto
sha256("password")
b64encode(data)

# Files
write_file("out.txt", "content")
read_file("in.txt")

# Math
abs(-5), max(1, 5), min(1, 5), sqrt(16), round(3.14)

# Parallelism
pmap(fn, items)
parallel(fn1, fn2, fn3)
```

---

## Full-Stack Examples

### 1. REST API (single file, zero config)

```zpx
schema User:
  id: int
  name: str
  email: str

let users = []
let next_id = 1

fn create_user(name, email):
  let user = {id: next_id, name: name, email: email}
  users.append(user)
  next_id += 1
  ret user

api GET "/users":
  ret users

api GET "/users/{id}":
  for u in users:
    if u.id == id: ret u
  ret {error: "Not found"}

api POST "/users":
  let body = json_parse(req.body)
  ret create_user(body.name, body.email)
```

### 2. Blog with HTML Rendering

```zpx
let posts = [
  {title: "Hello Zpx", body: "Welcome!"},
  {title: "Full-Stack", body: "One language for everything."},
]

fn render_post(p):
  element("article", {class: "post"}, [
    element("h2", {}, p.title),
    element("p", {}, p.body),
  ])

fn page(title, posts):
  element("html", {}, [
    element("head", {}, [element("title", {}, title)]),
    element("body", {}, [
      element("h1", {}, title),
      map(posts, p => render_post(p)),
    ]),
  ])

print(html(page("My Blog", posts)))
```

### 3. AI-Native Features

```zpx
# Permissions
permission filesystem_read "read access to filesystem"
permission network_http "outbound HTTP"

# Service with metadata
service PaymentService:
  version "2.1.0"
  requires authenticated_user, valid_session
  guarantees transaction_atomic, audit_logged
  expose process_payment
  
  fn process_payment(amount: float) -> str:
    ret "processed: " + str(amount)

# Structured concurrency
concurrent:
  say("branch 1")
  let x = 1 + 2
  say("branch 2")
  let y = 3 + 4

# Compile-time checks
check:
  expect 1 + 1 == 2 "math works"
  expect "hello" != "world"

# Runtime assertions
expect divide(10, 2) == 5
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           zpx run file.zpx                          │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Lexer (indentation-sensitive)                      │
│  → tokens                                           │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Parser (recursive descent)                         │
│  → AST                                              │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Type Checker (contracts, types)                    │
│  → validated AST                                    │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Evaluator (interpreter with time-travel)           │
│  → result                                           │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Compiler (optional)                                │
│  → .pyc bytecode cache                              │
└─────────────────────────────────────────────────────┘
```

**Self-hosting**: The interpreter is written in Zpx (`self_host/`):
- `tokens.zpx` — Token system
- `lexer.zpx` — Lexer
- `parser.zpx` — Parser
- `ast_nodes.zpx` — AST definitions
- `env.zpx` — Environment/scoping
- `evaluator.zpx` — Full evaluator
- `builtins.zpx` — Standard library

---

## CLI Reference

```bash
zpx run <file|folder>      # Execute (auto-detects main.zpx/index.zpx/app.zpx)
zpx check <file>           # Parse + type-check
zpx build <file>           # Check + run
zpx compile <file>         # Transpile to Python bytecode
zpx test [path]            # Run @test / expect blocks
zpx repl                   # Interactive REPL
zpx version                # Print version + grammar version
zpx diag <text>            # Parse diagnostics → JSON
zpx init [name]            # Scaffold new project
zpx add <spec>             # Add dependency
zpx install                # Install from zpx.json
zpx ai                     # AI subcommands (train, scan, wifi)
```

**Flags:** `--format=json` (machine-readable), `--no-color`

---

## Editor Support

**VS Code Extension** (`vscode-extension/`):
- Syntax highlighting
- Snippets (`fn`, `let`, `if`, `class`, `api`, `schema`, ...)
- Language configuration (brackets, comments, folding)

**LSP Server** (`zpx lsp`):
- Hover documentation
- Go to definition
- Find references
- Document symbols
- Workspace symbols
- Semantic tokens
- Diagnostics (parse + type errors)

---

## Project Structure

```
ZPX/
├── src/                    # Python interpreter (~300K lines)
│   ├── lexer.py            # Tokenizer
│   ├── parser.py           # Recursive descent parser
│   ├── evaluator.py        # Interpreter with time-travel debugging
│   ├── compiler.py         # Python bytecode compiler
│   ├── types.py            # Type checker with contracts
│   ├── codegen.py          # Code generators
│   ├── cli.py              # Full CLI
│   ├── lsp.py              # Language Server Protocol
│   └── adapters/           # JS/Python transpilers
├── self_host/              # Zpx written in Zpx (~95%)
│   ├── tokens.zpx
│   ├── lexer.zpx
│   ├── parser.zpx
│   ├── ast_nodes.zpx
│   ├── env.zpx
│   ├── evaluator.zpx
│   ├── builtins.zpx
│   └── zpx_interpreter.zpx
├── lib/                    # Standard library
│   ├── std.zpx
│   ├── db.zpx
│   ├── http.zpx
│   ├── strings.zpx
│   └── collections.zpx
├── examples/               # 20+ example programs
├── tests/                  # 166 passing tests
├── wasm/                   # Zpx → JS transpiler
├── vscode-extension/       # VS Code extension
├── registry/               # Package registry
└── training/               # AI training data
```

---

## Roadmap

### Done (v0.2)
- Self-hosted parser, lexer, AST, evaluator
- 248+ builtins with short aliases
- Compound types (`list[T]`, `dict[K,V]`, `T|U`)
- Type aliases
- Contract system
- Pattern matching
- Comprehensions
- Auto-deploy DB
- Platform detection
- LSP, package manager, WASM target

### Coming Soon
- [ ] Optional chaining (`?.`)
- [ ] Destructuring (`let {a, b} = expr`)
- [ ] Web UI framework
- [ ] Mobile app support
- [ ] Package registry (publish/install)
- [ ] IDE plugins (Cursor, Windsurf, Zed)
- [ ] WebAssembly compilation
- [ ] Incremental compilation

---

## Contributing

We're building the language that AI models actually want to write. Your help is welcome!

```bash
git clone https://github.com/M-2000-0/ZPX.git
cd ZPX
python -m pytest tests/ -q  # 166 tests pass
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute
1. **Try Zpx** — Use it and give feedback
2. **Fix Bugs** — Check [open issues](https://github.com/M-2000-0/ZPX/issues)
3. **Add Features** — Check the [roadmap](#roadmap)
4. **Improve Docs** — Fix typos, add examples
5. **Add Examples** — Showcase the language
6. **Port Builtins** — Help port builtins from Python to Zpx

---

## Community

- **GitHub**: [github.com/M-2000-0/ZPX](https://github.com/M-2000-0/ZPX)
- **Issues**: [Report bugs](https://github.com/M-2000-0/ZPX/issues)
- **Discussions**: [Ask questions](https://github.com/M-2000-0/ZPX/discussions)

---

## License

MIT — free for commercial use.

---

## Philosophy

> **By 2027, 80% of code will be AI-generated.**  
> Languages designed for humans become legacy.  
> Zpx is designed for the world where AI writes most of the code.

**Zpx — Write less. Ship faster. Let AI do the rest.**

---

## Documentation

- [Language Guide (GUIDE.md)](GUIDE.md) — AI coding guide with token optimization rules
- [Language Specification (SPEC.md)](SPEC.md) — Full syntax reference
- [Contributing (CONTRIBUTING.md)](CONTRIBUTING.md) — How to contribute
- [Changelog (CHANGELOG.md)](CHANGELOG.md) — Release history

## Benchmarks

LLM code generation benchmarks are run weekly via GitHub Actions. See [benchmarks/](benchmarks/) for methodology and [latest results](https://github.com/M-2000-0/ZPX/actions/workflows/benchmark.yml).

---

## Show Your Support

If you find Zpx useful:
- ⭐ **Star** this repository
- 🍴 **Fork** and contribute
- 🐛 **Report** issues
- 📢 **Share** with other developers
- 📸 **Follow** me on Instagram: [@ptzbno](https://instagram.com/ptzbno)

---

Thanks for checking out Zpx!