# Zpx — The AI-Native Programming Language

> **One language for backend, frontend, database, and config — designed for the age of AI-written code.**

[![PyPI](https://img.shields.io/pypi/v/zpx-lang?label=zpx-lang&color=blue)](https://pypi.org/project/zpx-lang/)
[![Python](https://img.shields.io/pypi/pyversions/zpx-lang?color=blue)](https://pypi.org/project/zpx-lang/)
[![License: MIT](https://img.shields.io/github/license/M-2000-0/ZPX?color=blue)](LICENSE)
[![Tests](https://github.com/M-2000-0/ZPX/actions/workflows/test.yml/badge.svg)](https://github.com/M-2000-0/ZPX/actions)
[![Stars](https://img.shields.io/github/stars/M-2000-0/ZPX?style=social)](https://github.com/M-2000-0/ZPX/stargazers)

Zpx is a **self-hosting, token-efficient programming language** built for the world where most code is written by AI. It collapses six layers of a typical app stack — backend, frontend, database, config, contracts, and types — into **one syntax, one file, zero boilerplate**.

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

---

## Why Zpx?

By 2027, an estimated 80% of code will be AI-generated. Today's languages were designed for humans reading printed code (Python 1991, JavaScript 1995, Go 2009). Zpx is designed for the world where **AI writes most of the code** — and where every token costs time, money, and context.

### The problem it solves

| Layer | Typical Language | Syntax Overhead |
|-------|------------------|-----------------|
| Backend | Python | `def func():` |
| Frontend | JavaScript | `function func() {}` |
| Database | SQL | `SELECT * FROM ...` |
| Config | YAML | `key: value` |
| Styles | CSS | `body { ... }` |
| Types | TypeScript | `x: number` |

**Zpx replaces all of these with one syntax.** One file. No imports. No build step. No package.json.

---

## Key Features

| Feature | Details |
|---------|---------|
| **Self-Hosting** | Interpreter written in Zpx itself (`self_host/`) |
| **Token-Efficient** | Short keywords (`fn`, `ret`, `el`), no boilerplate |
| **Pattern Matching** | `match` with wildcards and guards |
| **Design by Contract** | `requires` / `ensures` / `invariant` |
| **Comprehensions** | List and dict comprehensions with filters |
| **Auto-Deploy DB** | `db_auto()` detects Vercel/Netlify/Render/Fly/Heroku/Replit |
| **Structured Concurrency** | `concurrent` blocks, `pmap`, `parallel` |
| **AI-Native Checks** | `check` / `expect` blocks, `service` contracts |
| **LSP Server** | `zpx lsp` — hover, goto-def, diagnostics, symbols |
| **Package Manager** | `zpx init`, `zpx add`, `zpx install`, `zpx.json` |
| **WASM Target** | Transpiles Zpx → JavaScript (`wasm/`) |
| **Time-Travel Debugging** | Checkpoints, rewind, query, diff |
| **VS Code Extension** | Syntax highlighting + snippets |
| **120+ Builtins** | HTTP, JSON, DB, crypto, files, math, no imports needed |

---

## Quick Start

```bash
# Install from PyPI
pip install zpx-lang

# Run your first program
echo 'print("Hello from Zpx!")' > hello.zpx
zpx run hello.zpx

# Try the examples
zpx run examples/hello.zpx
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

**REPL:**

```bash
zpx repl
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
let user = {name: "Alice", age: 30}  # dict
```

### Functions

```zpx
fn greet(name):
  ret "Hello, " + name + "!"

fn greet_with_default(name, greeting="Hi"):
  print(greeting + ", " + name)

# Implicit return (last expression)
fn double(x) x * 2
```

### Control Flow

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
```

### Comprehensions

```zpx
let nums = [1, 2, 3, 4, 5]
let doubled = [x * 2 for x in nums]
let evens = [x for x in nums if x % 2 == 0]
let squares = {x: x * x for x in nums}
```

### Built-ins (no imports needed)

```zpx
# HTTP
http_get("https://api.example.com/data")
http_post(url, json_body={key: "value"})

# JSON
json_parse('{"name": "Zpx"}')
json_stringify(data)

# Database (SQLite, auto-deploys on Vercel/Netlify/Render)
db_auto("my_app"):
  users:
    id: "TEXT PRIMARY KEY"
    name: "TEXT"

db_insert("users", {id: "1", name: "Alice"})

# Crypto
sha256("password")
b64encode(data)

# Files
write_file("out.txt", "content")
read_file("in.txt")

# Parallelism
pmap(fn, items)
parallel(fn1, fn2, fn3)
```

---

## Full-Stack in One File

### REST API

```zpx
schema User:
  id: int
  name: str
  email: str

let users = []

fn create_user(name, email):
  let user = {id: len(users) + 1, name: name, email: email}
  users.append(user)
  ret user

api GET "/users":
  ret users

api POST "/users":
  let body = json_parse(req.body)
  ret create_user(body.name, body.email)
```

### AI-Native Features

```zpx
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

# Compile-time checks
check:
  expect 1 + 1 == 2 "math works"
```

---

## Architecture

```
zpx run file.zpx
      │
      ▼
   Lexer ──────────► tokens
      │
      ▼
   Parser ─────────► AST
      │
      ▼
   Type Checker ───► validated AST (contracts, types)
      │
      ▼
   Evaluator ──────► result (time-travel debug enabled)
      │
      ▼
   Compiler ───────► .pyc bytecode cache (optional)
```

**Self-hosted interpreter** (`self_host/`): the parser, lexer, AST, environment, evaluator, and builtins are written in Zpx itself.

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

## Documentation

| Doc | Purpose |
|-----|---------|
| [Language Guide](docs/GUIDE.md) | How to write Zpx, AI coding guide, token optimization |
| [Language Spec](docs/SPEC.md) | Full syntax reference |
| [Contributing](docs/CONTRIBUTING.md) | How to get involved |
| [Showcase](docs/showcase.md) | Real-world example gallery |
| [Changelog](CHANGELOG.md) | Release history |

---

## Project Structure

```
ZPX/
├── src/                    # Python interpreter
│   ├── lexer.py            # Tokenizer
│   ├── parser.py           # Recursive descent parser
│   ├── evaluator.py        # Interpreter with time-travel debugging
│   ├── compiler.py         # Python bytecode compiler
│   ├── types.py            # Type checker with contracts
│   ├── cli.py              # Full CLI
│   └── lsp.py              # Language Server Protocol
├── self_host/              # Zpx interpreter written in Zpx
│   ├── lexer.zpx
│   ├── parser.zpx
│   ├── ast_nodes.zpx
│   ├── evaluator.zpx
│   └── zpx_interpreter.zpx
├── lib/                    # Standard library (.zpx)
├── examples/               # 20+ example programs
├── tests/                  # 213 passing tests
├── wasm/                   # Zpx → JS transpiler
├── vscode-extension/       # VS Code extension
├── docs/                   # Documentation
└── benchmarks/             # LLM code-gen benchmark harness
```

---

## Roadmap

### Done
- Self-hosted parser, lexer, AST, evaluator
- 120+ builtins with short aliases
- Pattern matching, comprehensions, contracts
- Auto-deploy DB + platform detection
- LSP, package manager, WASM target
- `in` / `not in` operators, ternary expressions, f-strings
- Dict iteration methods (`keys`, `values`, `items`)

### In Progress
- Optional chaining (`?.`)
- Destructuring (`let {a, b} = expr`)
- Web UI framework
- Mobile app support
- IDE plugins (Cursor, Windsurf, Zed)
- Incremental compilation

---

## Contributing

We're building the language that AI models actually want to write. Your help is welcome!

```bash
git clone https://github.com/M-2000-0/ZPX.git
cd ZPX
python -m pytest tests/ -q  # 213 tests pass
```

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines, and our [Code of Conduct](CODE_OF_CONDUCT.md).

**Ways to help:**
1. **Try Zpx** — use it and give feedback
2. **Fix bugs** — check [open issues](https://github.com/M-2000-0/ZPX/issues)
3. **Add features** — see the [roadmap](#roadmap)
4. **Improve docs** — typos, examples, guides
5. **Port builtins** — from Python to Zpx (helps self-hosting)

---

## Community

- **GitHub**: [github.com/M-2000-0/ZPX](https://github.com/M-2000-0/ZPX)
- **Issues**: [Report bugs](https://github.com/M-2000-0/ZPX/issues)
- **Discussions**: [Ask questions](https://github.com/M-2000-0/ZPX/discussions)

---

## License

[MIT](LICENSE) — free for commercial use.

---

## Philosophy

> **By 2027, 80% of code will be AI-generated.**
> Languages designed for humans become legacy.
> Zpx is designed for the world where AI writes most of the code.

**Zpx — Write less. Ship faster. Let AI do the rest.**

---

**Like this project?** ⭐ Star it on GitHub and share it with your favorite AI tools.
