# Zpx Design Guide

> How to get professional visual results with Zpx - design systems, web apps, and
> desktop-style apps - while keeping the code AI-friendly and token-minimal.

Zpx has no CSS framework or design library. It doesn't need one. Every visual
style is a **string** you swap, and every page is **markup** you keep. The
whole frontend DSL is `element(tag, attrs, children)` rendered by `html(...)`.
(`el` is reserved for `else`, so use `element`.)

```zpx
let glass = ".card { background: rgba(255,255,255,0.18); backdrop-filter: blur(18px); }"
print(html(element("div", {class: "card"}, "Hello")))
```

Change the string, change the look. The markup never changes.

---

## 1. Design Systems (one string per style)

A design system in Zpx is a CSS string that defines `.card`, `.btn`, typography,
and the page background. Apply it with one `<style>` tag, reuse it everywhere.

### Claymorphism - soft, tactile, 3D clay

Clay uses warm colors, large rounded corners, and **dual shadows**: a soft outer
drop shadow plus light **inset** highlights (top) and dark inset shadows (bottom).

```zpx
let clay = ".card { background: #e7d6c3; border-radius: 24px; padding: 28px; box-shadow: 0 10px 24px rgba(90,60,20,0.25), inset 0 2px 6px rgba(255,255,255,0.7), inset 0 -8px 16px rgba(120,80,30,0.18); }
.btn { background: #f0a94e; border-radius: 16px; padding: 12px 24px; box-shadow: 0 8px 0 #c47f2e; color: #3a2506; }
.btn:active { transform: translateY(6px); box-shadow: 0 2px 0 #c47f2e; }
body { background: #f4e9d8; font-family: 'Segoe UI', sans-serif; }"

# Key ingredients:
#   border-radius: 16-28px          # rounded "clay"
#   box-shadow: outer soft + inset highlight + inset shade
#   warm palette (#e7d6c3, #f0a94e, #5a3c14)
#   button "pressed" state via :active translateY
```

### Glassmorphism - frosted translucent glass

Glass uses **translucent backgrounds**, a light border, `backdrop-filter: blur`,
and a colorful gradient behind it so the blur is visible.

```zpx
let glass = ".card { background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.35); border-radius: 20px; padding: 28px; backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px); box-shadow: 0 8px 32px rgba(0,0,0,0.25); }
.btn { background: rgba(255,255,255,0.25); border: 1px solid rgba(255,255,255,0.4); border-radius: 14px; padding: 12px 24px; color: #fff; backdrop-filter: blur(8px); }
h1, h2 { color: #fff; }
body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); font-family: 'Segoe UI', sans-serif; }"

# Key ingredients:
#   background: rgba(255,255,255,0.15-0.3)  # see-through panel
#   border: 1px solid rgba(255,255,255,0.3-0.5)  # light glass edge
#   backdrop-filter: blur(12-20px)           # frosted effect
#   a vivid gradient behind the glass         # makes blur visible
```

### Neumorphism - soft extruded plastic

Neumorphism replaces shadows with **dual shadows on the same surface**: one dark
shadow (bottom-right) and one light shadow (top-left), both on the element's own
background color.

```zpx
let neumorph = ".card { background: #e0e5ec; border-radius: 20px; padding: 28px; box-shadow: 9px 9px 16px rgba(163,177,198,0.6), -9px -9px 16px rgba(255,255,255,0.8); }
.btn { background: #e0e5ec; border-radius: 16px; padding: 12px 24px; box-shadow: 6px 6px 12px rgba(163,177,198,0.6), -6px -6px 12px rgba(255,255,255,0.8); color: #4a5568; }
.btn:active { box-shadow: inset 6px 6px 12px rgba(163,177,198,0.6), inset -6px -6px 12px rgba(255,255,255,0.8); }
body { background: #e0e5ec; font-family: 'Segoe UI', sans-serif; }"

# Key ingredients:
#   surface color == background color (#e0e5ec)
#   box-shadow: 6-12px dark (offset +,+) and 6-12px light (offset -,-)
#   :active flips to inset shadows for a "pressed in" feel
```

### Brutalism - raw, bold, hard-edged

Brutalism uses stark contrasts: pure black borders, hard box shadows, no rounded
corners, bold colors, and monospace or heavy fonts.

```zpx
let brutal = ".card { background: #fff; border: 4px solid #000; border-radius: 0; padding: 28px; box-shadow: 8px 8px 0 #000; }
.btn { background: #ffe600; border: 3px solid #000; border-radius: 0; padding: 12px 24px; box-shadow: 4px 4px 0 #000; color: #000; font-weight: bold; }
h1, h2 { color: #000; text-transform: uppercase; }
body { background: #f0f0f0; font-family: 'Courier New', monospace; }"

# Key ingredients:
#   border: 3-4px solid #000          # hard edge
#   box-shadow: Npx Npx 0 #000        # hard offset shadow (no blur)
#   border-radius: 0                  # no curves
#   high-contrast accent (#ffe600), uppercase type
```

### Minimal - quiet, spacious, restrained

Minimal relies on whitespace, thin borders, low-contrast greys, and one dark
accent.

```zpx
let minimal = ".card { background: #fff; border: 1px solid #e2e2e2; border-radius: 4px; padding: 28px; }
.btn { background: #111; border-radius: 2px; padding: 12px 24px; color: #fff; }
h1, h2 { color: #111; font-weight: 300; letter-spacing: 1px; }
body { background: #fafafa; font-family: 'Helvetica Neue', sans-serif; }"

# Key ingredients:
#   generous padding, thin 1px borders (#e2e2e2)
#   near-black text on near-white bg
#   light font weights (300), subtle letter-spacing
```

### Using the theme

```zpx
fn page(title, css)
  element("html", {}, [
    element("head", {}, [element("title", {}, title), element("style", {}, css)]),
    element("body", {}, [element("div", {class: "card"}, title)]),
  ])

print(html(page("Glass", glass)))   # swap `glass` for `clay`, `neumorph`, ...
```

**Run the full 5-theme demo:**

```bash
zpx run examples/design_systems.zpx   # writes build/design-systems.html
```

---

## 2. Building Web Apps

A web app in Zpx is one file: theme string + components + `serve()`. No build
step, no framework, no package.json.

```zpx
# examples/web_app.zpx (abridged)
let glass = "..."                      # design system string (section 1)

fn render_item(item)
  element("div", {class: "list-item"}, [
    element("span", {}, item["name"]),
    element("span", {}, "done" if item["done"] else ""),
  ])

fn page()
  element("html", {}, [
    element("head", {}, [element("style", {}, glass)]),
    element("body", {}, [element("div", {class: "card"}, [
      element("h1", {}, "Glassmorphism App"),
      element("div", {id: "list"}, map(items, it => render_item(it))),
    ])]),
  ])

let routes = {
  "/": () => html(page()),            # render HTML for the browser
  "/api/items": () => items,          # JSON API, same server
}
serve(3000, routes)
```

### Serving rules
- `serve(port, routes)` starts a server. Route values are functions; call them
  with `() =>`.
- If a route returns a dict, it's sent as JSON; otherwise as HTML.
- Data shared between UI and API lives in the same file - no serialization gap.

**Run it:**

```bash
zpx run examples/web_app.zpx
# open http://localhost:3000  (Ctrl+C to stop)
```

---

## 3. Building Desktop-Style Apps

Zpx has no native window toolkit yet (roadmap: `ui` module). Until then you can
build **desktop-feeling apps entirely in Zpx** using an *HTML shell*: generate
window chrome, taskbar, menus, and app logic as HTML/CSS/JS, then open the result
in a browser. It runs like a desktop app, with zero native dependencies.

```zpx
# examples/desktop_app.zpx (abridged)
let desktop_css = "... #window { border-radius: 12px; box-shadow: 0 24px 64px rgba(0,0,0,0.5); }
#titlebar { height: 40px; background: #0f172a; } ..."

let desktop_js = "const views = { notes: '<h2>Notes</h2>', todo: '<h2>Tasks</h2>' };
document.querySelectorAll('.menu-item').forEach(b => b.onclick = () => {
  content.innerHTML = views[b.dataset.view];
});"

fn taskbar()
  element("div", {id: "taskbar"}, [element("span", {class: "app-dot"}, ""), element("span", {id: "clock"}, "Zpx Desktop")])

fn titlebar(title)
  element("div", {id: "titlebar"}, [
    element("span", {class: "title"}, title),
    element("button", {class: "win-btn close"}, "x"),
  ])

fn app()
  element("html", {}, [
    element("head", {}, [element("style", {}, desktop_css)]),
    element("body", {}, [
      element("div", {id: "desktop"}, [
        taskbar(),
        element("div", {id: "window"}, [titlebar("Zpx Desktop App"), element("div", {id: "content"}, "Click a menu item.")]),
      ]),
      element("script", {}, desktop_js),
    ]),
  ])

mkdir("build")
write_file("build/desktop-app.html", html(app()))
print("Open build/desktop-app.html in a browser")
```

**Run it:**

```bash
zpx run examples/desktop_app.zpx   # writes build/desktop-app.html
```

### Desktop patterns that work today
- **Window chrome** - a titlebar with fake minimize/maximize/close buttons.
- **App logic** - inline JS strings toggle views, update a clock, handle clicks.
- **State** - keep data in Zpx vars or use `signal()`/`effect()` from the guide.
- **Persistence** - `write_file`/`json_save` to store state next to the app.

As the `ui` module lands, the same components will map to native windows.

---

## 4. Token Efficiency for AI Code Generation

The design layer is deliberately **string + markup**, which is the cheapest way
for an AI to produce great visuals. Rules:

1. **One CSS string per style.** Reuse it; never inline styles everywhere.
2. **`map(xs, fn)` renders lists** - no manual loops or joins for lists of items.
3. **Ternary is `X if COND else Y`** (Python-style), e.g. `"done" if t.done else ""`.
4. **`format("Hello {name}", {name: n})`** for string interpolation in content.
5. **Serve UI and JSON from one `serve()`** - no separate frontend/backend files.
6. **Keep markup identical across themes** - only the CSS string changes, so an
   AI can restyle a page by editing one line.

### Side-by-side

| Task | HTML+CSS+JS separately | Zpx alone |
|---|---|---|
| Glass landing page | ~120 lines / 3 files | ~15 lines / 1 file |
| Themed CRUD app | ~250 lines / 5 files | ~35 lines / 1 file |
| Desktop-feel app shell | ~180 lines / 3 files | ~40 lines / 1 file |

Zpx expresses design in **one syntax** (element trees + CSS strings) instead of
three languages, cutting the tokens an AI needs by **60-80%**.

---

## Related
- [GUIDE.md](GUIDE.md) - full AI coding guide and token-optimization rules
- [showcase.md](showcase.md) - more examples
- [SPEC.md](SPEC.md) - language reference
- Examples: `examples/design_systems.zpx`, `examples/web_app.zpx`, `examples/desktop_app.zpx`
