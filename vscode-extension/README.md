# Zpx Language Extension for VS Code

AI-native full-stack programming language support with syntax highlighting, IntelliSense, diagnostics, formatting, debugging, and run integration.

## Features

### 🎨 Syntax Highlighting
- Full TextMate grammar with 50+ token types
- Keywords, operators, functions, classes, types, decorators
- String interpolation `${expr}` and `$var`
- Regex literals `/pattern/`
- Built-in function categories (io, string, math, async, db, ml, ui, system)

### 💡 IntelliSense & Completion
- Keywords, builtins, types, decorators
- Snippets for all language constructs (fn, class, if, for, match, try, etc.)
- Context-aware completions (function params, class members)
- Variable, function, class detection from current document

### 🔍 Hover & Documentation
- Rich markdown documentation for all builtins
- Function signatures from definitions
- Links to online docs

### 📋 Diagnostics (Real-time)
- `return` → use `ret`
- `elif` → use `el: if`
- `&&` → use `and`
- `||` → use `or`
- `function` → use `fn`
- `this` → use `self`
- Missing colon on block statements
- Type-check integration (on save)

### ✨ Formatting
- Auto-indentation (2 spaces)
- Block-aware formatting on save
- Configurable indent size

### 🏃 Run & Debug
- **Run File** (F5): Execute current `.zpx` file
- **Run Project**: Run entire workspace
- **Type Check** (Ctrl+Shift+C): Static analysis
- **Debug**: Launch configurations with breakpoints

### ⚡ CodeLens
- Run/Debug buttons above functions
- Test runner for `test` blocks

### 🔧 Commands
| Command | Keybinding | Description |
|---------|------------|-------------|
| `zpx.runFile` | F5 | Run current file |
| `zpx.runProject` | - | Run project |
| `zpx.check` | Ctrl+Shift+C | Type check |
| `zpx.format` | Shift+Alt+F | Format document |
| `zpx.newProject` | - | Create new project |
| `zpx.restartServer` | - | Restart LSP |

## Configuration

```json
{
  "zpx.executablePath": "python -m src",
  "zpx.enableDiagnostics": true,
  "zpx.enableFormatOnSave": true,
  "zpx.enableHover": true,
  "zpx.enableCompletion": true,
  "zpx.runOnSave": false,
  "zpx.checkOnSave": true
}
```

## Snippets

| Prefix | Description |
|--------|-------------|
| `fn` | Function |
| `fn->` | Function with return type |
| `async fn` | Async function |
| `class` | Class |
| `trait` | Trait |
| `if` | If statement |
| `el` | Else |
| `elif` | Else-if |
| `for` | For loop |
| `while` | While loop |
| `match` | Pattern matching |
| `try` | Try-catch |
| `schema` | Schema definition |
| `api` | API endpoint |
| `service` | Service |
| `database` | Database |
| `concurrent` | Concurrent block |
| `test` | Test definition |
| `doc` | Documentation |
| `check` | Check block |
| `lambda` / `=>` | Lambda |
| `comp` | List comprehension |
| `dcomp` | Dict comprehension |
| `pipe` / `|>` | Pipe operator |
| `http_get` / `http_post` | HTTP requests |
| `db_query` | Database query |
| `element` | HTML element |
| `signal` / `effect` | Reactive UI |

## Language Server (Optional)

For enhanced features (cross-file navigation, workspace symbols, refactoring):

```bash
# Install the language server
cargo install zpx-lsp  # or download binary
```

Then set in settings:
```json
"zpx.languageServerPath": "/path/to/zpx-lsp"
```

## Debugging

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "zpx",
      "request": "launch",
      "name": "Debug Zpx File",
      "program": "${file}",
      "stopOnEntry": false,
      "console": "integratedTerminal"
    }
  ]
}
```

## Contributing

1. Fork the repository
2. Make changes to grammar/snippets/extension
2. Test with `npm run compile` and `F5`
3. Submit PR

## License

MIT - see [LICENSE](../LICENSE)