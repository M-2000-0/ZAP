# Contributing to Zap

Zap is an AI-native full-stack programming language. We welcome contributions!

## Quick Start

```bash
git clone https://github.com/M-2000-0/ZAP.git
cd ZAP
python main.py run examples/hello.zap
```

## Architecture

- `src/lexer.py` — Tokenizer
- `src/parser.py` — Recursive-descent parser
- `src/ast_nodes.py` — AST node definitions
- `src/evaluator.py` — Runtime evaluator (Python)
- `src/values.py` — Runtime values and 248+ builtins
- `src/tokens.py` — Token types and keywords
- `src/types.py` — Type system and inference
- `self_host/` — Full Zap interpreter written in Zap

## Key Conventions

- **Keywords**: use short forms (`fn`, `ret`, `el`, `and`, `or`)
- **No semicolons**: indentation-based blocks
- **`ret` not `return`**
- **`el:` not `elif`** (use on separate line with `if`)
- **`match` is reserved** — use `try_match` for method names
- **`expect` is reserved** — use `require_token` for method names
- **`version` is reserved** — use `svc_version` or similar
- **No default params** — pass all arguments explicitly
- **No `try/except`** — use `try/catch/throw` syntax
- **No `raise`** — use `throw`
- **No tuple syntax** — use dicts `{"key": val}` instead
- **No `.pop()`** on ZapList — use slice `lst[:len(lst)-1]`
- **`exit()`** not `sys_exit()`

## Adding a New Keyword

1. Add `TokenType.KW_NEW` to `src/tokens.py`
2. Add `'new': TokenType.KW_NEW` to the KEYWORDS dict
3. Add AST node to `src/ast_nodes.py`
4. Add parsing logic to `src/parser.py`
5. Add evaluation logic to `src/evaluator.py`
6. Add builtin value to `src/values.py` if needed
7. Port to `self_host/` files

## Adding a New Builtin

1. Define `_stdlib_name` function in `src/values.py`
2. Register with `env.define('name', ZapBuiltin(_stdlib_name, 'name'))`
3. Add type signature to `src/types.py` if needed
4. Add short alias in the `short` dict if applicable

## Testing

```bash
python -m pytest tests/ -q
python test_self_hosting.py
```

## AI Code Generation Notes

- Use `fn name(args) expr` expression form for single-line functions
- Use `@requires` / `@ensures` for contracts
- Use `test "name":` for test groups
- Use `doc` for structured documentation
- Use `try/catch/throw` for error handling
- Use compound type annotations (`list[int]`, `dict[str, any]`)

## Deployment

Zap supports auto-deploy database integration:

```zap
import "lib/db.zap"
db_auto("my_db"):
  users:
    id: "TEXT PRIMARY KEY"
    name: "TEXT"
```

Works with Vercel, Netlify, Render, Fly.io, Heroku, Replit, and Kubernetes.

---

Thank you for contributing to Zap! 🚀
