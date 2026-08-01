# Zpx Showcase

Real-world examples built with Zpx — one language, zero boilerplate.

## 🌟 Featured Examples

### 1. REST API Server

A complete REST API with user management in a single file.

```zpx
schema User:
  id: int
  name: str
  email: str
  active: bool

let users = []
let next_id = 1

fn create_user(name, email):
  let user = {id: next_id, name: name, email: email, active: true}
  users.append(user)
  next_id += 1
  ret user

fn find_user(id):
  for u in users:
    if u["id"] == id: ret u
  ret none

api GET "/users":
  ret users

api GET "/users/{id}":
  let user = find_user(id)
  if user != none: ret user
  ret {error: "Not found"}

api POST "/users":
  let body = json_parse(req.body)
  ret create_user(body.name, body.email)
```

**Run it:** `zpx run examples/rest_api.zpx`

---

### 2. Blog with HTML Rendering

A complete blog with HTML rendering, no frontend framework needed.

```zpx
let posts = [
  {title: "Hello Zpx", author: "Zpx Team", body: "Welcome!"},
  {title: "Full-Stack", author: "Dev", body: "One language for everything."},
]

fn render_post(post):
  element("article", {class: "post"}, [
    element("h2", {}, post.title),
    element("p", {class: "meta"}, "By " + post.author),
    element("p", {}, post.body),
  ])

fn page(title, posts):
  element("html", {}, [
    element("head", {}, [
      element("title", {}, title),
      element("style", {}, "body { font-family: sans-serif; max-width: 800px; margin: auto; padding: 2rem; }"),
    ]),
    element("body", {}, [
      element("h1", {}, title),
      map(posts, p => render_post(p)),
    ]),
  ])

print(html(page("My Blog", posts)))
```

**Run it:** `zpx run examples/blog.zpx`

---

### 3. Data Pipeline

Process data with functional-style pipelines.

```zpx
let transactions = [
  {product: "Laptop", amount: 999, category: "Electronics", quantity: 1},
  {product: "Mouse", amount: 25, category: "Electronics", quantity: 3},
  {product: "Desk", amount: 150, category: "Furniture", quantity: 1},
]

fn total(t):
  ret t["amount"] * t["quantity"]

let revenues = [total(t) for t in transactions]
let total_revenue = sum(revenues)

print("Total Revenue: $" + str(total_revenue))
```

**Run it:** `zpx run examples/data_pipeline.zpx`

---

### 4. AI-Native Features

Contracts, permissions, structured concurrency, and compile-time checks.

```zpx
# Contracts
fn divide(a: int, b: int) -> int:
  requires b != 0
  ensures result >= 0
  ret a / b

# Permissions
permission filesystem_read "read access to filesystem"
permission network_http "outbound HTTP access"

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
```

**Run it:** `zpx run examples/ai_native.zpx`

---

### 5. Text Adventure Game

A complete interactive game in one file.

```zpx
let player = {
  name: "Hero",
  health: 100,
  attack: 10,
  defense: 5,
  gold: 0,
  inventory: [],
}

let rooms = {
  "start": {
    name: "Village Square",
    description: "You stand in a peaceful village.",
    exits: {"north": "forest"},
  },
  "forest": {
    name: "Dark Forest",
    description: "Trees tower above you.",
    exits: {"south": "start"},
  },
}

fn describe_room():
  let room = rooms[current_room]
  print("=== " + room["name"] + " ===")
  print(room["description"])

fn play():
  describe_room()
  while player["health"] > 0:
    let command = input("> ")
    # ... game logic
```

**Run it:** `zpx run examples/game.zpx`

---

### 6. Design Systems (5 visual styles)

Claymorphism, glassmorphism, neumorphism, brutalism, and minimal — all from one
file where each style is a single CSS string.

```zpx
let glass = ".card { background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.35); border-radius: 20px; padding: 28px; backdrop-filter: blur(18px); box-shadow: 0 8px 32px rgba(0,0,0,0.25); }
body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); font-family: 'Segoe UI', sans-serif; }"

fn hero(name, desc, css):
  element("html", {}, [
    element("head", {}, [element("title", {}, name), element("style", {}, css)]),
    element("body", {}, [
      element("h1", {}, name),
      element("div", {class: "card"}, [element("button", {class: "btn"}, "Action")]),
    ]),
  ])

print(html(hero("Glassmorphism", "Frosted UI", glass)))
```

**Run it:** `zpx run examples/design_systems.zpx` → writes `build/design-systems.html`

---

### 7. Desktop-Style App

A desktop-feeling app shell (titlebar, taskbar, menus, app logic) generated
entirely in Zpx as an HTML shell — no native dependencies.

**Run it:** `zpx run examples/desktop_app.zpx` → writes `build/desktop-app.html`

---

### 8. Machine Learning Pipeline

High-level ML concepts with tensor operations.

```zpx
let data = tensor([1, 2, 3, 4, 5, 6, 7, 8], [4, 2])
let labels = tensor([0, 1, 0, 1], [4, 1])

fn sigmoid(x):
  ret 1 / (1 + exp(-x))

fn linear(x, w, b):
  ret x @@ w + b

let w = zeros(2, 1)
let b = 0.0

for epoch in range(100):
  let pred = sigmoid(linear(data, w, b))
  let loss = sum((pred - labels) ** 2) / len(labels)
  if epoch % 10 == 0:
    print("epoch", epoch, "loss", loss)
```

**Run it:** `zpx run examples/ml_pipeline.zpx`

---

## 🚀 Try Them All

```bash
# Run any example
zpx run examples/hello.zpx
zpx run examples/blog.zpx
zpx run examples/rest_api.zpx
zpx run examples/data_pipeline.zpx
zpx run examples/ai_native.zpx
zpx run examples/game.zpx
zpx run examples/ml_pipeline.zpx
zpx run examples/comprehensions.zpx
zpx run examples/pattern_matching.zpx
zpx run examples/oop.zpx
zpx run examples/design_systems.zpx
zpx run examples/desktop_app.zpx
```

## 📊 Token Efficiency Comparison

| Example | Python + JS + SQL | Zpx | Reduction |
|---------|-------------------|-----|-----------|
| Hello World | 1 line / 1 file | 1 line / 1 file | 0% |
| Blog | ~200 lines / 5 files | 25 lines / 1 file | 87% |
| REST API | ~150 lines / 3 files | 40 lines / 1 file | 73% |
| Data Pipeline | ~100 lines / 3 files | 15 lines / 1 file | 85% |
| Game | ~300 lines / 4 files | 142 lines / 1 file | 53% |

**Average token reduction: 70%**

---

## 💡 Build Your Own

Want to create something amazing with Zpx? Here are some ideas:

1. **Personal Website** — Use `element()` for HTML, `api` for dynamic content
2. **API Service** — Define `schema` and `api` endpoints in one file
3. **Data Dashboard** — Process CSV/JSON, render HTML tables
4. **AI Agent** — Use HTTP builtins, JSON parsing, and contracts
5. **Educational Tool** — Simple syntax makes it great for teaching programming
6. **Prototyping** — Iterate in seconds, not hours
7. **Internal Tool** — Database + UI + auth in one command

---

## 🌈 Community Showcase

Have you built something cool with Zpx? Share it with us!

1. Open a [GitHub Discussion](https://github.com/M-2000-0/ZPX/discussions)
2. Show your code and what you built
3. We'll feature it here!

---

**Zpx — Write less. Ship faster. Let AI do the rest.**