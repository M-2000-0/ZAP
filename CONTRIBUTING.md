# Contributing to Zap

Thank you for your interest in contributing to Zap! We're building the language that AI models actually want to write, and we need your help.

## Why Contribute?

- **Shape the future of coding** — You're not just contributing to a language, you're helping define how AI and humans will write code together
- **Learn a new paradigm** — Experience what a language designed for AI code generation looks like
- **Build something real** — Zap is self-hosting (written in Zap), so your contributions directly improve the language itself

## Quick Start

```bash
# Clone and run
git clone https://github.com/M-2000-0/ZAP.git
cd ZAP
python -m src run examples/hello.zap

# Run tests
python -m pytest tests/ -q
```

## Ways to Contribute

### 1. Try Zap and Give Feedback

The easiest way to contribute is to **use Zap** and tell us what works and what doesn't:

- Try the examples in `examples/`
- Write your own code
- Report issues or confusion
- Suggest improvements

### 2. Fix Bugs

Look at [open issues](https://github.com/M-2000-0/ZAP/issues) for bugs to fix.

### 3. Add Features

Check the [roadmap](README.md#roadmap) for planned features. If you see something you want to work on, open an issue first to discuss it.

### 4. Improve Documentation

- Fix typos
- Add examples
- Improve explanations
- Translate docs

### 5. Add Examples

Create example `.zap` files that showcase the language. Good examples help new users learn.

### 6. Port Builtins

Help port the 248+ builtins from Python to Zap in `self_host/builtins.zap`.

## Architecture

```
src/
  lexer.py          - Tokenizer
  parser.py         - Recursive descent parser
  ast_nodes.py      - AST node definitions
  evaluator.py      - Runtime evaluator
  values.py         - Runtime values and builtins
  tokens.py         - Token types and keywords
  types.py          - Type system
  cli.py            - Command-line interface

self_host/          - Zap interpreter written in Zap
  tokens.zap        - Token system
  lexer.zap         - Lexer
  parser.zap        - Parser
  ast_nodes.zap     - AST definitions
  env.zap           - Environment/scoping
  evaluator.zap     - Evaluator
  builtins.zap      - Standard library

lib/                - Standard library
  db.zap            - Database operations
  deploy.zap        - Deployment helpers
  strings.zap       - String utilities
  http.zap          - HTTP client
  zap_ai.zap        - AI/ML primitives
```

## Code Style

### Zap Files

- Use `#` for comments (not `//`)
- Use `ret` for return (not `return`)
- Use `el:` for else-if (not `elif` or `else if`)
- Use indentation with `:` for blocks (not `{}`)
- Use `fn` for functions (not `function`)
- Use `and`/`or`/`not` (not `&&`/`||`/`!`)
- No semicolons
- No `this` (use `self`)
- No `null` (use `none`)

### Python Files

- Follow PEP 8
- Use type hints
- Write docstrings

## Testing

```bash
# Run all tests
python -m pytest tests/ -q

# Run specific test
python -m pytest tests/test_cli.py -q

# Run self-hosting tests
python test_self_hosting.py
```

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/my-feature`)
3. **Commit** your changes (`git commit -m 'Add my feature'`)
4. **Push** to your branch (`git push origin feature/my-feature`)
5. **Open** a Pull Request

### PR Guidelines

- Keep PRs focused on one change
- Include tests if adding features
- Update documentation if needed
- Follow existing code style
- Write clear commit messages

## Development Setup

```bash
# Install dependencies
pip install -e .

# Run in development mode
python -m src run your_file.zap

# Run tests
python -m pytest tests/ -q
```

## Questions?

Open a [discussion](https://github.com/M-2000-0/ZAP/discussions) or ask in issues.

## Code of Conduct

Be respectful, inclusive, and constructive. We're building something cool together.

---

Thank you for helping build the language of the future! 🚀
