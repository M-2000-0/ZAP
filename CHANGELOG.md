# Zpx Language Changelog

All notable changes to the Zpx programming language.

## v0.3.0 - Renamed from ZAP to ZPX for legal reasons

## [0.2.0] - 2026-07-28

### Added
- **Self-hosting interpreter**: ~95% of interpreter written in Zpx (lexer, parser, evaluator, AST, environment, builtins)
- **248+ builtins** with short aliases (`el`, `ret`, `fn`, `imp`, `svc`, `db`, `req`, `gnt`, etc.)
- **Compound type annotations**: `list[T]`, `dict[K,V]`, `T|U`, `type User = dict[str, any]`
- **Contract system**: `@requires`, `@ensures`, `@invariant`, `@expect`, `check` blocks
- **Pattern matching**: `match` expressions with wildcard `_` and `el:` fallback
- **List/dict/set comprehensions**: `[x*2 for x in xs]`, `{k: v for k,v in items}`
- **Structured concurrency**: `concurrent:` blocks
- **AI-native features**: permissions, service declarations, versioning, guarantees
- **Auto-deploy database**: `db_auto()` with platform detection (Vercel, Netlify, Render, Fly, Heroku, Replit)
- **Deployment platform detection**: `db_platform()` returns `vercel`/`netlify`/`render`/`fly`/`heroku`/`replit`/`self_hosted`
- **Grammar versioning**: `# zpx:grammar=0.2` pragma with mismatch detection
- **LSP server**: `zpx lsp` for IDE integration (hover, goto-def, diagnostics)
- **Package manager**: `zpx init`, `zpx add`, `zpx install` with `zpx.json` config
- **WASM transpiler**: `wasm/zpx-to-js.js` compiles Zpx to JavaScript
- **VS Code extension**: Syntax highlighting, snippets, language config
- **Time-travel debugging**: Checkpoints, rewind, query, diff
- **CLI commands**: `run`, `check`, `build`, `compile`, `test`, `version`, `diag`, `repl`, `ai`
- **Diagnostic formats**: Text and JSON output for AI agent integration
- **165 passing tests**: Arithmetic, control flow, functions, classes, builtins, edge cases, integration

### Changed
- Keywords shortened: `else` → `el`, `return` → `ret`, `function` → `fn`, `import` → `imp`
- Logical operators: `&&` → `and`, `||` → `or`, `!` → `not`
- Dict syntax: `{key: value}` (no quotes on keys)
- Grammar version bumped to `0.2`

### Fixed
- Parser recovery mode for better error messages
- Indentation handling with dedent tracking
- String interpolation with `${expr}` and `$var`
- Type checker stability with compound types
- Evaluator handling of closures and scopes

---

## [0.1.0] - 2026-07-20

### Added
- Initial Zpx language implementation
- Lexer with indentation-based blocks
- Recursive descent parser
- AST node definitions
- Environment/scoping system
- Core evaluator
- Basic builtins (print, len, str, int, float, range, math, collections)
- HTTP client (http_get, http_post)
- JSON parsing (json_parse, json_stringify)
- Database operations (db_open, db_query, db_exec)
- File I/O (read_file, write_file, list_dir)
- Class system with inheritance
- Function definitions with default parameters
- Control flow: if/el/el if, for, while, break, continue, ret
- Lambda expressions: `x => x * 2`
- Basic type annotations
- Grammar version `0.1`
- CLI with `run` and `check` commands
- Example programs: hello, fibo, blog, rest_api, ai_native, game, zpxphysics

---

## Release Notes Format

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes