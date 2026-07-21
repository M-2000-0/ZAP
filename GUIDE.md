# AI Coding Guide for Zap

This guide teaches AI language models how to generate Zap code efficiently. Zap is designed so that an AI can express any application — backend, frontend, database, config, contracts — in **one language with one syntax**.

## Why Zap Exists

Most languages were designed for *humans reading printed code* (FORTRAN 1957, C 1972, Python 1991).
Zap was designed for *AI generating code in a context window*.

| Traditional languages | Zap |
|---|---|
| Different syntax for every layer | One syntax for everything |
| 30+ languages per app | 1 language per app |
| ~300 tokens for a CRUD app | ~65 tokens for the same app |
| Context switching between modes | Single mental model |
| Type annotations + docstrings + tests + schemas = 4x redundancy | Contracts cover all four |
| Build tools, config files, package managers | `zap run file.zap` |

## Golden Rule

**Every Zap file is a valid program.** No build step, no config file, no package.json. Just `zap run file.zap`.

## Core Syntax (2 spaces indentation)

```python
# Comment
let name = value            # Variable
fn add(a, b) a + b          # Function (implicit return)
ret value                   # Early return
if cond body el else_body   # If/else
for x in items body         # For loop
while cond body             # While loop
match value {cases}         # Pattern matching
```

## Token Optimization Rules

### 1. Replace 3+ languages with 1

Instead of generating Python + SQL + HTML + JS + CSS + YAML in one response, generate **only Zap**:

```
# BAD: 6 languages in one file
# Python API, SQL string, HTML template, JS logic, CSS style, YAML config

# GOOD: 1 language
fn render(user)
  element("div", {class: "card", style: "padding:1rem"}, [
    element("h2", {}, user.name),
    element("p", {}, user.email),
  ])

api GET "/users/{id}"
  let user = query("SELECT * FROM users WHERE id = ?", id)
  render(user)
```

### 2. Use pipe operator instead of nesting

```
# BAD (nested, hard to read)
print(json_stringify(query("SELECT * FROM users WHERE id = ?", id)))

# GOOD (pipe, linear)
id |> query("SELECT * FROM users WHERE id = ?", ?) |> json_stringify |> print
```

`|>` threads the left value as the **first argument** of the right call.

### 3. Dict keys are string shortcuts

```
# These are equivalent:
{name: "zap", version: 1}
{"name": "zap", "version": 1}
```

Use identifier keys `{key: val}` to save 2 tokens per key.

### 4. Implicit return saves tokens

```python
# Explicit ret (wasteful)
fn double(x) ret x * 2

# Implicit return (correct)
fn double(x) x * 2
```

The last expression is the return value. Only use `ret` for early returns.

### 5. Lambdas are single-param-arrow

```python
# Multi-line fn def
fn square(x) x * x

# Inline lambda
map(items, x => x * x)
filter(items, x => x > 0)
```

### 6. Strings use double quotes

```python
let name = "zap"       # Standard
let path = "C:\\dir"   # Backslash escapes work
```

### 7. Contracts replace comments + tests + validation

```python
@requires(amount > 0)
@ensures(balance >= 0)
fn withdraw(amount: float)
  balance = balance - amount
```

Don't write separate docstrings, separate test cases, and validation logic. One `@requires` clause covers all three.

## Common Patterns (Token-Efficient)

### Full-stack web app

```python
schema Task
  title: string
  done: bool

database App
  tasks: Task

fn render_task(t)
  element("li", {class: if t.done "done" el "pending"}, t.title)

api GET "/tasks"
  tasks |> query("SELECT * FROM tasks") |> map(t => render_task(t))

service Api
  expose on "/api"
  fn list() -> string query("SELECT * FROM tasks")
```

### File processing pipeline

```python
"data.json"
  |> read_file
  |> json_parse
  |> get("items")
  |> map(x => x.name)
  |> sort
  |> join(", ")
  |> write_file("output.txt")
```

### Reactive UI

```python
let count = signal(0)
effect(count, v => print("count:", v))
count.set(1)
count.set(2)
```

### Type-safe API

```python
fn divide(a: int, b: int) -> float
  @requires(b != 0)
  @ensures(result * b == a)
  a / b
```

## Keywords (never use as variable names)

```
fn let if el for in while ret
true false none and or not
import from class async await match intend
service database api page schema model
expose requires ensures invariant expect
permission concurrent channel guarantees version
check
```

## Short Aliases (Token Optimization)

Use these to reduce token count by 40-60%:

| Short | Long | When to use |
|---|---|---|
| `el` | `element` | HTML elements |
| `rd` | `read_file` | File I/O |
| `wr` | `write_file` | File I/O |
| `jp` | `json_parse` | JSON parsing |
| `js` | `json_stringify` | JSON output |
| `sha` | `sha256` | Hashing |
| `uid` | `uuid` | Unique IDs |
| `rstr` | `random_string` | Random strings |
| `has` | `contains` | String contains |
| `b64e` / `b64d` | `base64_encode/decode` | Encoding |
| `ls` | `list_dir` | Directory listing |
| `ex` | `file_exists` | File check |
| `hget` | `http_get` | HTTP GET |
| `hpost` | `http_post` | HTTP POST |
| `@req` | `@requires` | Pre-conditions |
| `@ens` | `@ensures` | Post-conditions |

## AI-Specific Tips

1. **Stay in Zap.** If you need to generate SQL, generate it as a string literal inside Zap. If you need HTML, use `element()`. Never switch languages.
2. **One response, one app.** A Zap file can contain API endpoints, database schemas, business logic, and UI components. Generate everything at once.
3. **Use contracts before tests.** `@requires` and `@ensures` are more token-efficient than inline `if/error` checks.
4. **Prefer pipes over nesting** for readability.
5. **Numbers can be variable names** — `let 1 = "one"` is valid, access with `get("1")`.

## File Size Comparison

| App | Python + JS + SQL + HTML | Zap alone |
|---|---|---|
| Blog API + frontend | ~450 lines / 5 files | ~30 lines / 1 file |
| CRUD service | ~300 lines / 4 files | ~20 lines / 1 file |
| Data pipeline | ~200 lines / 3 files | ~15 lines / 1 file |

Zap reduces token count by **60-80%** for the same application.

## When to Bridge to Other Languages

Zap's goal is to replace 30+ languages, but pragmatism wins. Here's when to bridge:

### Bridge OUT of Zap (call other languages)

```python
# Python — for libraries that don't have a Zap equivalent yet
import numpy as np
let arr = np.array([1, 2, 3])
print(np.mean(arr))

# JavaScript — for npm packages
import "./node_modules/lodash.js"
```

**AI rule:** If a well-known library exists in Python/JS that has no Zap stdlib equivalent,
generate an `import` statement. Don't reimplement numpy in Zap.

### Bridge INTO Zap (call Zap from other languages)

```python
# Python host
from src.evaluator import Evaluator
eval = Evaluator()
eval.env.define("my_data", [1, 2, 3])
eval.evaluate(parse("fn double(x) x * 2"))
```

### When to stay pure vs bridge

| Scenario | Choice |
|---|---|
| New project, no dependencies | Pure Zap |
| Need numpy/pandas/torch | `import` from Zap |
| Prototyping | Pure Zap (faster to iterate) |
| Production with existing infra | Bridge both ways |
| AI code generation | Pure Zap (simpler context) |

The rule: **write new code in Zap, bridge to existing libraries.** Over time the stdlib
grows until bridges are rarely needed.

## Setting Up AI Assistants for Zap

### Cursor

Create `.cursorrules`:

```
You generate ONLY Zap code (.zap files). Zap is a full-stack language where schemas,
APIs, HTML, and logic all use the same syntax. Never output Python, JavaScript, SQL,
HTML, CSS, or YAML separately. Use element() for HTML, fn for functions, api for endpoints,
service for grouping endpoints, schema for data models. 2-space indentation.
Implicit return on last expression. Pipes with |> for chaining.
```

### Windsurf

Add to `.windsurfrules`:

```
- Primary language: Zap (.zap)
- Never split into multiple files or languages
- UI = element(tag, {attrs}, children)
- Data = query("SQL", params) or file builtins
- Validation = @requires/@ensures
- Full app in one file
```

### Claude (Projects)

Upload `GUIDE.md` to project knowledge. System prompt:

```
You are a Zap language specialist. Respond with ONLY Zap code.
Zap replaces Python + JavaScript + SQL + HTML + CSS + YAML in one language.
Write complete applications in single .zap files.
```

### ChatGPT / Custom GPT

Custom instruction:

```
Generate only Zap code. Zap is a single language for backend, frontend, databases,
and configuration. Never suggest using multiple languages. Every application
feature can be expressed in Zap alone. Use element() for HTML, fn for functions,
let for variables, schema for models, api for endpoints.
```

### GitHub Copilot

`.github/copilot-instructions.md`:

```markdown
This project uses the Zap language (.zap).
- One file per application
- 2-space indentation for blocks
- Functions: fn name(params) body
- HTML: element(tag, attrs, children)
- APIs: api METHOD "/path" body
- Schemas: schema Name field: type
- Pipes: value |> fn
```

## Use Cases for AI Generation

### Best suited
- Full-stack web apps (one file, zero config)
- API services (schema + endpoints in one definition)
- Data pipelines (read → transform → write in pipe chain)
- AI agent tools (HTTP + JSON + logic, no boilerplate)
- Prototypes and MVPs (iterate in seconds, not hours)
- Internal tools (database + UI + auth in one command)
- Educational examples (no framework learning curve)

### Still maturing
- Native desktop apps (planned: `ui` module)
- Mobile apps (planned: mobile adapters)
- Game development (not a priority)
- Embedded systems (not a target)
