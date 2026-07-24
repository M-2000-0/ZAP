# Zap — AI-Native Full-Stack Language

Zap is a programming language designed for **AI code generation** with minimal tokens and one syntax for backend, frontend, database, config, and contracts. Build AI models with **Zap AI**, deploy apps with **live databases**, and achieve **self-hosting** (Zap written in Zap).

## 🚀 Quick Start

```bash
# Install and run
pip install zap-lang
zap run examples/hello.zap

# Or use the CLI
python main.py run examples/hello.zap
```

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **AI-Optimized Syntax** | Short keywords (`fn`, `ret`, `el`), expression form functions, pipe operator |
| **Self-Hosting** | Zap interpreter written in Zap — `self_host/` contains the full self-hosted stack |
| **Live Database** | `lib/db.zap` — auto-detects DATABASE_URL, supports Vercel/Netlify/Render/Fly/Heroku/Replit |
| **Deployment Helpers** | `lib/deploy.zap` — `detect_platform()`, `live_url()`, `is_live()` |
| **AI Primitives** | Neural networks, embeddings, RAG, prompt templates, LLM completion, cosine similarity |
| **Token Efficiency** | ~30% less tokens than Python/JS for equivalent code |
| **Zero-Boilerplate Stdlib** | 248+ builtins (HTTP, JSON, SQLite, crypto, auth, queue, cron) |
| **Contract System** | `@requires`/`@ensures` pre/post conditions, `expect` test assertions |
| **Compilation + Cache** | Bytecode compilation with manifest-based caching |
| **LSP Support** | Semantic tokens, diagnostics integration |
| **Package Manager** | `zap add <spec>`, `zap install`, lockfile + integrity hashes |

## 💡 Syntax Examples

### Function Definition (Expression Form)
```zap
fn add(a, b) a + b
```

### Class with Methods
```zap
class Animal:
  fn init(self, name)
    self.name = name

  fn speak(self)
    print(self.name, "says hello!")
```

### Match with Else (Optimized)
```zap
match status:
  "active": print("active")
  "inactive": print("inactive")
el:
  print("other")
```

### Database with Auto-Deploy
```zap
import "lib/db.zap"

db_auto("app_db"):
  users:
    id: "TEXT PRIMARY KEY"
    name: "TEXT"
    email: "TEXT"

db_insert("users", {id: "1", name: "Alice", email: "alice@example.com"})
let user = db_row("SELECT * FROM users WHERE id = ?", ["1"])
```

### Type Annotations with Compound Types
```zap
fn find_user(users: list[dict[str, any]], id: int) -> dict[str, any]:
  for u in users:
    if u["id"] == id:
      ret u
  ret none
```

### Type Aliases
```zap
type User = dict[str, any]
type ID = int

fn get_user(id: ID) -> User | none:
  ...
```

### Test Groups & Documentation
```zap
test "arithmetic":
  expect 1 + 1 == 2
  expect 2 * 3 == 6

doc "Calculates the factorial of n"
doc param n: "Non-negative integer"
doc returns: "n! as int"
fn factorial(n):
  if n <= 1: ret 1
  ret n * factorial(n - 1)
```

### Error Handling
```zap
try:
  let result = divide(a, b)
catch err:
  print("Error: " + err)

throw MyError("something went wrong")
```

### Deployment Detection
```zap
import "lib/deploy.zap"

fn main():
  print("Platform: " + detect_platform())
  print("Live URL: " + live_url())
  print("Is live: " + str(is_live()))
```

### Optional Colon & `in` Syntax
```zap
# Colons optional — all three forms work:
if x > 0:
  print("positive")

if x > 0
  print("positive")

for i range(10)
  print(i)
```

## 📦 Libraries

| Library | Purpose |
|---------|---------|
| `lib/db.zap` | High-level DB with auto-deploy schema, insert/update/delete/select helpers |
| `lib/deploy.zap` | Platform detection (Vercel/Netlify/Render/Fly/Heroku/Replit/K8s) |
| `lib/strings.zap` | String utilities |
| `lib/http.zap` | HTTP client |
| `lib/collections.zap` | List/dict helpers |
| `lib/std.zap` | Common utilities re-export |
| `lib/zap_ai.zap` | AI/ML pipeline, neural network primitives |

## 🔧 CLI Commands

```bash
zap run <file|folder>     # Run Zap file or auto-detect entrypoint
zap init <name>            # Scaffold a new Zap project
zap add <spec>             # Add a dependency
zap install                # Install dependencies from lockfile
zap run --format=json <file>  # Machine-readable diagnostics
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -q

# Self-hosting tests
python test_self_hosting.py
```

## 🤖 AI Code Generation

Zap is designed so AI models generate correct code with minimal prompt tokens:

- **10-token function** (expression form)
- **2-token import** vs 4+ in other languages
- **3-character keywords** (`fn`, `ret`, `el`, `and`, `or`)
- **Structured contracts** (`@requires`, `@ensures`) for AI reliability
- **Named test groups** (`test "name":`) for AI-generated test suites
- **Compound type annotations** (`list[int]`, `dict[str, any]`) so AI knows types

## 📊 Token Efficiency

| Pattern | Zap Tokens | Python Tokens | JS Tokens |
|---------|-----------|---------------|-----------|
| Function def | 10 | 12 | 14 |
| Print statement | 3 (`? "hi"`) | 4 | 5 |
| Class method | 8 | 10 | 12 |
| Import | 2 | 2 | 4 |
| For loop header | 10 | 10 | 14 |

## 🏗️ Architecture

```
Zap Source (.zap)
    ↓ Lexer (src/lexer.py)
    ↓ Parser (src/parser.py) → AST (src/ast_nodes.py)
    ↓ Evaluator (src/evaluator.py) / Compiler (src/compiler.py)
    ↓ Runtime (src/values.py) — 248+ builtins
```

**Self-hosted stack** (`self_host/`):
- `tokens.zap` — Token system written in Zap
- `lexer.zap` — Lexer written in Zap
- `parser.zap` — Parser written in Zap
- `ast_nodes.zap` — AST definitions written in Zap
- `env.zap` — Environment class written in Zap
- `interpreter.zap` — Full self-hosted interpreter

## 🔮 Roadmap

- [x] Self-hosted interpreter (Zap→Zap)
- [x] Auto-deploy database support (lib/db.zap)
- [x] Deployment platform detection (lib/deploy.zap)
- [x] Compound type annotations (list[T], dict[K,V], T\|U)
- [x] Type aliases (`type User = dict[str, any]`)
- [x] New keywords: `test`, `doc`, `try`/`catch`/`throw`, `enum`
- [x] Optional colons and optional `in` in for loops
- [x] 248+ builtins with short aliases
- [ ] Optional chaining (`?.`) — in progress
- [ ] Destructuring (`let { a, b } = expr`) — planned
- [ ] Optional type inference improvements — planned

## 📄 License

MIT

## 🔗 Links

- **Repository**: https://github.com/M-2000-0/ZAP
- **Guide**: [GUIDE.md](GUIDE.md)

---

*Zap — one syntax, AI-native, deploy-ready.*
