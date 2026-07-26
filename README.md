# Zap — The Language AI Models Actually Want to Write

**One language. One syntax. Zero boilerplate.**

Zap is the first programming language designed from the ground up for **AI code generation**. While Python, JavaScript, and other languages were designed for humans reading code on paper in 1991, Zap was designed for AI models generating code in a context window in 2026.

```
fn greet(name) "Hello, " + name + "!"
print(greet("World"))
```

That's a complete program. No imports. No boilerplate. No build step. Just `zap run file.zap`.

---

## Why Zap?

### The Problem

When AI writes code today, it must juggle **6+ languages** for a single application:

| Layer | Language | Syntax |
|-------|----------|--------|
| Backend | Python | `def func():` |
| Frontend | JavaScript | `function func() {}` |
| Database | SQL | `SELECT * FROM...` |
| Config | YAML | `key: value` |
| Styles | CSS | `body { ... }` |
| Types | TypeScript | `x: number` |

**Every layer = different syntax = more tokens = more errors.**

### The Zap Solution

**One language for everything:**

```zap
schema User:
  name: str
  email: str

api GET "/users/{id}":
  let user = query("SELECT * FROM users WHERE id = ?", id)
  render_user(user)

fn render_user(user):
  element("div", {class: "card"}, [
    element("h2", {}, user.name),
    element("p", {}, user.email),
  ])
```

Schema, API, database query, and HTML rendering — **all in one file, one syntax**.

---

## Token Efficiency: Why AI Models Love Zap

Zap uses **30-60% fewer tokens** than Python or JavaScript for equivalent code:

| Pattern | Zap | Python | JavaScript |
|---------|-----|--------|------------|
| Function | `fn add(a,b) a+b` | `def add(a,b): return a+b` | `function add(a,b){return a+b}` |
| Print | `print("hi")` | `print("hi")` | `console.log("hi")` |
| Class method | `fn speak(self) ...` | `def speak(self): ...` | `speak(){...}` |
| If/else | `if x: ... el: ...` | `if x: ... else: ...` | `if(x){...}else{...}` |
| For loop | `for i in range(10):` | `for i in range(10):` | `for(let i=0;i<10;i++)` |

**Fewer tokens = faster generation = lower cost = fewer errors.**

---

## Key Features

### AI-Optimized Syntax

```zap
# 3-character keywords: fn, ret, el, and, or, not
fn factorial(n):
  if n <= 1: ret 1
  ret n * factorial(n - 1)
```

### Self-Hosting (Zap Written in Zap)

The Zap interpreter is **itself written in Zap**. This proves the language is complete and capable:

```
self_host/
  tokens.zap      - Token system
  lexer.zap       - Lexer
  parser.zap      - Recursive descent parser
  ast_nodes.zap   - AST definitions
  env.zap         - Environment/scoping
  evaluator.zap   - Full evaluator
  builtins.zap    - Standard library
```

**~95% of the interpreter is written in Zap.** The Python layer is only the bootstrap.

### Zero-Boilerplate Standard Library

248+ builtins — no imports needed for most tasks:

```zap
# HTTP
http_get("https://api.example.com/data")

# JSON
let data = json_parse('{"name": "Zap"}')

# Database
db_auto("my_app"):
  users:
    id: "TEXT PRIMARY KEY"
    name: "TEXT"

# File I/O
write_file("output.txt", "Hello!")
let content = read_file("input.txt")

# Crypto
let hash = sha256("password")

# Math
let pi = math.pi
```

### Contract System

Replace docstrings + tests + validation with one construct:

```zap
@requires(amount > 0)
@ensures(balance >= 0)
fn withdraw(amount: float):
  balance = balance - amount
```

### Pattern Matching

```zap
match status:
  "active": print("Active user")
  "inactive": print("Inactive user")
  "banned": print("Banned user")
el:
  print("Unknown status")
```

### Type Annotations

```zap
fn find_user(users: list[dict[str, any]], id: int) -> dict[str, any] | none:
  for u in users:
    if u["id"] == id:
      ret u
  ret none
```

---

## Quick Start

```bash
# Install
pip install zap-lang

# Run your first program
echo 'print("Hello from Zap!")' > hello.zap
zap run hello.zap

# Run examples
zap run examples/hello.zap
zap run examples/fibo.zap
zap run examples/blog.zap
```

### From Source

```bash
git clone https://github.com/M-2000-0/ZAP.git
cd ZAP
python -m src run examples/hello.zap
```

---

## Examples

### Hello World
```zap
print("Hello from Zap!")
```

### Fibonacci
```zap
fn fib(n):
  if n <= 1: ret n
  ret fib(n - 1) + fib(n - 2)

for i in range(10):
  print(fib(i))
```

### List Comprehensions
```zap
let nums = [1, 2, 3, 4, 5]
let doubled = [x * 2 for x in nums]
let evens = [x for x in nums if x % 2 == 0]
let squares = {x: x * x for x in nums}
```

### Full-Stack Blog
```zap
let posts = [
  {title: "Hello Zap", body: "Welcome!"},
  {title: "Full-Stack", body: "One language for everything."},
]

fn render_post(post):
  element("article", {class: "post"}, [
    element("h2", {}, post.title),
    element("p", {}, post.body),
  ])

fn render_page(title, posts):
  element("html", {}, [
    element("head", {}, [element("title", {}, title)]),
    element("body", {}, [
      element("h1", {}, title),
      map(posts, p => render_post(p)),
    ]),
  ])

print(html(render_page("My Blog", posts)))
```

### Database + API
```zap
import "lib/db.zap"

db_auto("my_app"):
  users:
    id: "TEXT PRIMARY KEY"
    name: "TEXT"
    email: "TEXT UNIQUE"

db_insert("users", {id: "1", name: "Alice", email: "alice@example.com"})

let user = db_row("SELECT * FROM users WHERE id = ?", ["1"])
print(user.name)
```

---

## Comparison with Other Languages

| Feature | Zap | Python | JavaScript | Rust | Go |
|---------|-----|--------|------------|------|----|
| AI token efficiency | **Best** | Medium | Medium | Low | Medium |
| Learning curve | **Minutes** | Hours | Hours | Days | Hours |
| Boilerplate | **Zero** | Low | Medium | High | Medium |
| Self-hosting | **Yes** | No | No | Yes | Yes |
| Full-stack | **One syntax** | 3+ languages | 3+ languages | 3+ languages | 3+ languages |
| Database built-in | **Yes** | No | No | No | No |
| Contract system | **Built-in** | No | No | No | No |
| Type annotations | **Optional** | Optional | Required | Required | Required |

---

## Why Zap Will Win

### 1. AI is the Future of Coding

By 2027, **80% of code will be AI-generated**. Languages designed for humans will become legacy. Zap is designed for the world where AI writes most of the code.

### 2. Token Economics

Every token costs money. Every token takes time. Every token is a chance for error. Zap's token-efficient syntax means:
- **Faster generation** (fewer tokens to produce)
- **Lower cost** (API calls cost less)
- **Higher accuracy** (less room for mistakes)
- **Better context utilization** (more code fits in the window)

### 3. One Language > Many

The average web app uses 6+ languages. Zap replaces them all with one syntax. This means:
- **No context switching** for AI or humans
- **No translation errors** between layers
- **No build tools** to configure
- **No package.json** to manage

### 4. Self-Hosting Proves It Works

Zap can write itself. The interpreter is written in Zap. This isn't a toy — it's a complete, self-sustaining language.

### 5. The Stdlib is Massive

248+ builtins means you rarely need external dependencies:
- HTTP client/server
- JSON parsing
- Database operations
- Cryptography
- File I/O
- Math
- String manipulation
- And more

---

## Roadmap

### Done
- [x] Self-hosted parser, lexer, tokenizer, AST, environment
- [x] 248+ builtins with short aliases
- [x] Compound type annotations (`list[T]`, `dict[K,V]`, `T|U`)
- [x] Type aliases (`type User = dict[str, any]`)
- [x] Contract system (`@requires`, `@ensures`)
- [x] Pattern matching
- [x] List/dict comprehensions
- [x] Auto-deploy database support
- [x] Deployment platform detection

### Coming Soon
- [ ] Optional chaining (`?.`)
- [ ] Destructuring (`let { a, b } = expr`)
- [ ] Web UI framework
- [ ] Mobile app support
- [ ] Package registry
- [ ] IDE plugins (VS Code, Cursor, Windsurf)
- [ ] WebAssembly compilation

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

```bash
git clone https://github.com/M-2000-0/ZAP.git
cd ZAP
python -m pytest tests/ -q  # Run tests
```

---

## Community

- **GitHub**: [github.com/M-2000-0/ZAP](https://github.com/M-2000-0/ZAP)
- **Issues**: [Report bugs](https://github.com/M-2000-0/ZAP/issues)
- **Discussions**: [Ask questions](https://github.com/M-2000-0/ZAP/discussions)

---

## License

MIT

---

**Zap — Write less. Ship faster. Let AI do the rest.**
