# Zap — AI-Native Programming Language

> **One language. One syntax. Zero boilerplate.**  
> The first programming language designed for AI code generation.

[![PyPI](https://img.shields.io/pypi/v/zap-lang?label=zap-lang)](https://pypi.org/project/zap-lang/)
[![Python](https://img.shields.io/pypi/pyversions/zap-lang)](https://pypi.org/project/zap-lang/)
[![License](https://img.shields.io/github/license/M-2000-0/ZAP)](LICENSE)
[![Tests](https://github.com/M-2000-0/ZAP/actions/workflows/test.yml/badge.svg)](https://github.com/M-2000-0/ZAP/actions)

---

## Why Zap?

**Today's AI writes code in 6+ languages for one app:**

| Layer | Language | Syntax Overhead |
|-------|----------|-----------------|
| Backend | Python | `def func():` |
| Frontend | JavaScript | `function func() {}` |
| Database | SQL | `SELECT * FROM...` |
| Config | YAML | `key: value` |
| Styles | CSS | `body { ... }` |
| Types | TypeScript | `x: number` |

**Zap replaces all of them with one syntax:**

```zap
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

## Token Efficiency: Why LLMs Love Zap

Zap uses **30–60% fewer tokens** than Python/JS for equivalent code:

| Pattern | Zap | Python | JS |
|---------|-----|--------|-----|
| Function | `fn add(a,b) a+b` | `def add(a,b): return a+b` | `function add(a,b){return a+b}` |
| Print | `print("hi")` | `print("hi")` | `console.log("hi")` |
| If/else | `if x: a el: b` | `if x: a else: b` | `if(x){a}else{b}` |
| Loop | `for i in range(10):` | `for i in range(10):` | `for(let i=0;i<10;i++)` |
| Class method | `fn speak(self) ...` | `def speak(self): ...` | `speak(){...}` |

**Fewer tokens = faster generation + lower cost + fewer errors + more context.**

---

## Quick Start

```bash
# Install from PyPI
pip install zap-lang

# Run your first program
echo 'print("Hello from Zap!")' > hello.zap
zap run hello.zap

# Run built-in examples
zap run examples/hello.zap
zap run examples/blog.zap
zap run examples/rest_api.zap
```

**From source:**
```bash
git clone https://github.com/M-2000-0/ZAP.git
cd ZAP
python -m src run examples/hello.zap
```

---

## Language Tour

### Variables & Types
```zap
let x = 42              # int
let name = "Zap"        # str
let flag = true         # bool
let empty = none        # null
let nums = [1, 2, 3]    # list
let user = ["name": "Alice", "age": 30]  # dict
```

### Functions (short keywords: `fn`, `ret`)
```zap
fn greet(name):
  ret "Hello, " + name + "!"

fn greet_with_default(name, greeting="Hi"):
  print(greeting + ", " + name)

greet("World")                    # "Hello, World!"
greet_with_default("Alice")       # "Hi, Alice"
greet_with_default("Bob", "Hey")  # "Hey, Bob"
```

### Control Flow (`el` not `else`, `ret` not `return`)
```zap
fn classify(x):
  if x > 0: ret "positive"
  el: if x < 0: ret "negative"
  el: ret "zero"

let i = 0
while i < 5:
  print(i)
  i += 1

for item in [1, 2, 3]:
  print(item)
```

### Pattern Matching
```zap
match status:
  "active": print("User is active")
  "inactive": print("User is inactive")
  "banned": print("User is banned")
  _: print("Unknown status")
```

### Contracts (Design by Contract)
```zap
fn withdraw(amount: float):
  requires amount > 0
  requires balance >= amount
  ensures balance >= 0
  
  balance = balance - amount
```

### Classes & Inheritance
```zap
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
```zap
let nums = [1, 2, 3, 4, 5]
let doubled = [x * 2 for x in nums]
let evens = [x for x in nums if x % 2 == 0]
let squares = {x: x * x for x in nums}
```

### Built-ins (248+, no imports needed)
```zap
# HTTP
http_get("https://api.example.com/data")
http_post(url, json_body={"key": "value"})

# JSON
json_parse('{"name": "Zap"}')
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
```zap
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
```zap
let posts = [
  {title: "Hello Zap", body: "Welcome!"},
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
```zap
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
┌─────────────────────────────────────┐
│           zap run file.zap          │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Lexer (indentation-sensitive)      │
│  → tokens                           │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Parser (recursive descent)         │
│  → AST                              │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Type Checker (contracts, types)    │
│  → validated AST                    │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Evaluator (interpreter)            │
│  → result                           │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Compiler (optional)                │
│  → .pyc bytecode cache              │
└─────────────────────────────────────┘
```

**Self-hosting**: The interpreter is written in Zap (`self_host/`):
- `tokens.zap` — Token system
- `lexer.zap` — Lexer
- `parser.zap` — Parser
- `ast_nodes.zap` — AST definitions
- `env.zap` — Environment/scoping
- `evaluator.zap` — Full evaluator
- `builtins.zap` — Standard library

---

## CLI Reference

```bash
zap run <file|folder>      # Execute (auto-detects main.zap/index.zap/app.zap)
zap check <file>           # Parse + type-check
zap build <file>           # Check + run
zap compile <file>         # Transpile to Python bytecode
zap test [path]            # Run @test / expect blocks
zap repl                   # Interactive REPL
zap version                # Print version + grammar version
zap diag <text>            # Parse diagnostics → JSON
zap init [name]            # Scaffold new project
zap add <spec>             # Add dependency
zap install                # Install from zap.json
zap ai                     # AI subcommands (train, scan, wifi)
```

**Flags:** `--format=json` (machine-readable), `--no-color`

---

## Editor Support

**VS Code Extension** (`vscode-extension/`):
- Syntax highlighting
- Snippets (`fn`, `let`, `if`, `class`, `api`, `schema`, ...)
- Language configuration (brackets, comments, folding)

**LSP Server** (`zap lsp`):
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
ZAP/
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
├── self_host/              # Zap written in Zap (~95%)
│   ├── tokens.zap
│   ├── lexer.zap
│   ├── parser.zap
│   ├── ast_nodes.zap
│   ├── env.zap
│   ├── evaluator.zap
│   ├── builtins.zap
│   └── zap_interpreter.zap
├── lib/                    # Standard library
│   ├── std.zap
│   ├── db.zap
│   ├── http.zap
│   ├── strings.zap
│   └── collections.zap
├── examples/               # 20+ example programs
├── tests/                  # 165 passing tests
├── wasm/                   # Zap → JS transpiler
├── vscode-extension/       # VS Code extension
├── registry/               # Package registry
└── training/               # AI training data
```

---

## Roadmap

### ✅ Done (v0.2)
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

### 🔜 Coming Soon
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

```bash
git clone https://github.com/M-2000-0/ZAP.git
cd ZAP
python -m pytest tests/ -q  # 165 tests pass
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Community

- **GitHub**: [github.com/M-2000-0/ZAP](https://github.com/M-2000-0/ZAP)
- **Issues**: [Report bugs](https://github.com/M-2000-0/ZAP/issues)
- **Discussions**: [Ask questions](https://github.com/M-2000-0/ZAP/discussions)

---

## License

MIT — free for commercial use.

---

## Philosophy

> **By 2027, 80% of code will be AI-generated.**  
> Languages designed for humans become legacy.  
> Zap is designed for the world where AI writes most of the code.

**Zap — Write less. Ship faster. Let AI do the rest.**