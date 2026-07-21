"""
CLI entrypoint. The grammar-version check, the diagnostic formatting, and
all subcommands live here.

Subcommands:
  zap run <file|folder>      execute a .zap file or folder (auto-detects entrypoint)
  zap check <file>           parse + type-check, emit diagnostics
  zap build <file>           check + run
  zap repl                   interactive REPL
  zap test [path]            run @test / expect blocks
  zap version                print VERSION and GRAMMAR_VERSION
  zap compile <file>         transpile to Python bytecode (stub)
  zap diag <text>            parse human-readable diagnostic output -> JSON
  zap init [name]            scaffold a new Zap project
  zap install                install dependencies from zap.json
  zap add <spec>             add and install a dependency
"""

from __future__ import annotations

import json
import os
import sys
import traceback

# Force UTF-8 stdout/stderr on Windows so ANSI color codes work in pipes.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def _diagnostics_from_exception(exc: BaseException, *, file: str | None = None,
                                code: str = "Z001") -> list:
    from .diagnostics import parse_error
    msg = str(exc)
    line = col = 0
    # The lexer/parser embed "L<line>:C<col>:" in their messages; pull it
    # out so the diagnostic carries a real span instead of a stringy one.
    import re
    m = re.search(r"L(\d+):(\d+)", msg)
    if m:
        line, col = int(m.group(1)), int(m.group(2))
    from .diagnostics import Span
    span = Span(line=line, col=col) if line else None
    return [parse_error(msg, code=code, span=span, file=file)]


# ---------------------------------------------------------------------------
# Entrypoint detection for folder-based execution
# ---------------------------------------------------------------------------

_ENTRYPOINT_CANDIDATES = (
    "main.zap",
    "index.zap",
    "app.zap",
    "server.zap",
    "run.zap",
    "start.zap",
    "cli.zap",
    "api.zap",
    "web.zap",
)


def _find_entrypoint(path: str) -> str | None:
    """Return the entrypoint file path if path is a directory with a known entrypoint."""
    if not os.path.isdir(path):
        return None
    for name in _ENTRYPOINT_CANDIDATES:
        candidate = os.path.join(path, name)
        if os.path.exists(candidate):
            return candidate
    # Fallback: any .zap file in the directory (first one alphabetically)
    try:
        zap_files = sorted(f for f in os.listdir(path) if f.endswith(".zap"))
        if zap_files:
            return os.path.join(path, zap_files[0])
    except OSError:
        pass
    return None


def _resolve_target(target: str) -> str:
    """Resolve a file or folder to an executable .zap file."""
    if os.path.isfile(target):
        return target
    entrypoint = _find_entrypoint(target)
    if entrypoint:
        return entrypoint
    # If it's a folder with no entrypoint, error with helpful message
    raise FileNotFoundError(
        f"No entrypoint found in {target!r}. "
        f"Expected one of: {', '.join(_ENTRYPOINT_CANDIDATES)} "
        f"or any .zap file."
    )


# ---------------------------------------------------------------------------
# Core execution functions
# ---------------------------------------------------------------------------

def run_file(filepath: str, *, diag_format: str = "text"):
    from .lexer import Lexer
    from .parser import Parser
    from .evaluator import Evaluator
    from .diagnostics import Span, runtime_error, emit
    from .version import GRAMMAR_VERSION, parse_grammar_pragma as vpragma

    if not os.path.exists(filepath):
        emit([runtime_error(f"file not found: {filepath}", code="Z500", file=filepath)],
             fmt=diag_format)
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    declared = vpragma(text)
    if declared is not None and declared != GRAMMAR_VERSION:
        from .diagnostics import parse_error
        emit([parse_error(
            f"grammar version mismatch: file declares {declared!r}, this interpreter is {GRAMMAR_VERSION!r}",
            code="Z001",
            fixes=[],
        )], fmt=diag_format)
        sys.exit(2)

    try:
        tokens = Lexer(text, filepath).tokenize()
    except SyntaxError as e:
        emit(_diagnostics_from_exception(e, file=filepath, code="Z100"), fmt=diag_format)
        sys.exit(1)

    parser = Parser(tokens)
    try:
        prog = parser.parse()
    except SyntaxError as e:
        emit(_diagnostics_from_exception(e, file=filepath, code="Z001"), fmt=diag_format)
        sys.exit(1)

    evaluator = Evaluator(current_file=filepath)
    try:
        result = evaluator.evaluate(prog)
    except SystemExit:
        raise
    except Exception as e:
        emit([runtime_error(f"{type(e).__name__}: {e}", code="Z300", file=filepath)],
             fmt=diag_format)
        if diag_format == "json":
            sys.exit(1)
        traceback.print_exc()
        sys.exit(1)

    if result is not None:
        print(result)


def run_path(target: str, *, diag_format: str = "text"):
    """Run a .zap file or folder (auto-detects entrypoint)."""
    try:
        filepath = _resolve_target(target)
    except FileNotFoundError as e:
        from .diagnostics import runtime_error, emit
        emit([runtime_error(str(e), code="Z500", file=target)], fmt=diag_format)
        sys.exit(1)
    run_file(filepath, diag_format=diag_format)


def check_file(filepath: str, *, diag_format: str = "text"):
    from .lexer import Lexer
    from .parser import Parser
    from .types import TypeChecker
    from .diagnostics import (
        Diagnostic, Severity, Span, type_error, parse_error, emit,
    )
    from .version import GRAMMAR_VERSION, parse_grammar_pragma

    if not os.path.exists(filepath):
        emit([parse_error(f"file not found: {filepath}", code="Z500", file=filepath)],
             fmt=diag_format)
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    declared = parse_grammar_pragma(text)
    if declared is not None and declared != GRAMMAR_VERSION:
        emit([parse_error(
            f"grammar version mismatch: file declares {declared!r}, this interpreter is {GRAMMAR_VERSION!r}",
            code="Z001",
            file=filepath,
        )], fmt=diag_format)
        sys.exit(2)

    diagnostics: list[Diagnostic] = []

    try:
        tokens = Lexer(text, filepath).tokenize()
    except SyntaxError as e:
        diagnostics.extend(_diagnostics_from_exception(e, file=filepath, code="Z100"))
        emit(diagnostics, fmt=diag_format)
        sys.exit(1)

    parser = Parser(tokens)
    parser.recovery_mode = True
    try:
        prog = parser.parse()
    except SyntaxError as e:
        diagnostics.extend(_diagnostics_from_exception(e, file=filepath, code="Z001"))
        emit(diagnostics, fmt=diag_format)
        sys.exit(1)

    # Parser errors come back as SyntaxError strings. Convert each to a Diagnostic.
    for err in parser.errors:
        msg = str(err)
        import re
        m = re.search(r"L(\d+):(\d+)", msg)
        span = Span(line=int(m.group(1)), col=int(m.group(2))) if m else None
        diagnostics.append(parse_error(msg, code="Z001", span=span, file=filepath))

    try:
        tc = TypeChecker()
        tc.check(prog)
        for line, col, msg in tc.errors:
            diagnostics.append(type_error(
                msg,
                span=Span(line=line, col=col),
                file=filepath,
            ))
    except Exception as e:
        diagnostics.append(type_error(f"type checker crashed: {e}", code="Z900", file=filepath))

    if diagnostics:
        emit(diagnostics, fmt=diag_format)
        sys.exit(1)
    # Always emit in JSON mode (even when ok) so AI agents get a structured response
    if diag_format == "json":
        emit(diagnostics, fmt=diag_format)
    else:
        print("ok")


def build_file(filepath: str, *, diag_format: str = "text"):
    # build == check + run, both with diagnostics
    check_file(filepath, diag_format=diag_format)
    run_file(filepath, diag_format=diag_format)


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

def repl():
    import atexit
    history_file = os.path.join(os.path.expanduser("~"), ".zap_history")
    try:
        import readline
        readline.set_history_length(500)
        try:
            readline.read_history_file(history_file)
        except FileNotFoundError:
            pass
        atexit.register(lambda: readline.write_history_file(history_file))
    except ImportError:
        pass

    from .lexer import Lexer
    from .parser import Parser
    from .evaluator import Evaluator, ReturnSignal
    from .environment import Environment
    from .version import VERSION, GRAMMAR_VERSION

    evaluator = Evaluator()
    print(f"Zap REPL v{VERSION} (grammar {GRAMMAR_VERSION}) -- type 'exit' or Ctrl+C to quit")
    buffer = ""
    continuing = False

    while True:
        try:
            prompt = "... " if continuing else ">>> "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if line.strip() == "exit":
            break

        buffer = (buffer + "\n" + line) if buffer else line

        stripped = line.strip()
        open_count = stripped.count('(') + stripped.count('[') + stripped.count('{')
        close_count = stripped.count(')') + stripped.count(']') + stripped.count('}')
        is_continue = (not stripped or stripped.endswith(":") or stripped.endswith("\\")
                       or open_count > close_count)
        if is_continue:
            continuing = True
            continue
        continuing = False

        try:
            tokens = Lexer(buffer, "<repl>").tokenize()
        except Exception as e:
            print(f"  error: {e}")
            buffer = ""
            continue

        parser = Parser(tokens)
        parser.recovery_mode = True
        try:
            prog = parser.parse()
        except Exception as e:
            print(f"  error: {e}")
            buffer = ""
            continue

        for err in parser.errors:
            print(f"  {err}")

        try:
            prev_env = evaluator.env
            evaluator.env = Environment(evaluator.global_env)
            try:
                result = evaluator.evaluate(prog)
            except ReturnSignal as rs:
                result = rs.value
            finally:
                evaluator.global_env = evaluator.env
                evaluator.env = prev_env
        except Exception as e:
            print(f"  error: {e}")
            buffer = ""
            continue

        if result is not None:
            print(repr(result))
        buffer = ""


# ---------------------------------------------------------------------------
# Test command
# ---------------------------------------------------------------------------

def test_command(args, *, diag_format: str = "text"):
    """Run all @test / expect blocks under the given path (default: cwd)."""
    from .test_runner import run_tests
    path = args[0] if args else "."
    summary = run_tests(path, diag_format=diag_format)
    if summary.failed or summary.errored:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Version command
# ---------------------------------------------------------------------------

def version_command(_args, *, diag_format: str = "text"):
    from .version import VERSION, GRAMMAR_VERSION
    if diag_format == "json":
        print(json.dumps({"version": VERSION, "grammar": GRAMMAR_VERSION}))
    else:
        print(f"Zap v{VERSION}")
        print(f"Grammar: {GRAMMAR_VERSION}")


# ---------------------------------------------------------------------------
# Compile command (transpile to Python bytecode)
# ---------------------------------------------------------------------------

def compile_command(filepath: str, *, out: str | None = None, diag_format: str = "text"):
    """Compile a .zap file to cached Python bytecode.

    Uses .zap_cache/ for caching with automatic invalidation based on
    source hash, mtime, and grammar version.
    """
    from .diagnostics import parse_error, runtime_error, emit
    from .version import parse_grammar_pragma, GRAMMAR_VERSION

    if not os.path.exists(filepath):
        emit([runtime_error(f"file not found: {filepath}", code="Z500", file=filepath)],
             fmt=diag_format)
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    declared = parse_grammar_pragma(text)
    if declared is not None and declared != GRAMMAR_VERSION:
        emit([parse_error(
            f"grammar version mismatch: file declares {declared!r}, this interpreter is {GRAMMAR_VERSION!r}",
            code="Z001", file=filepath,
        )], fmt=diag_format)
        sys.exit(2)

    from .compiler import transpile_and_exec, compile_to_file
    import io
    import contextlib

    if out:
        # Compile to explicit output path
        try:
            py_path = compile_to_file(text, filepath, out_path=out)
            if diag_format == "json":
                print(json.dumps({"ok": True, "output": py_path}))
            else:
                print(f"Compiled to {py_path}")
        except Exception as e:
            emit([runtime_error(f"compile failed: {e}", code="Z300", file=filepath)],
                 fmt=diag_format)
            sys.exit(1)
    else:
        # Execute with caching
        try:
            if diag_format == "json":
                # Capture stdout to avoid mixing program output with JSON diagnostics
                captured = io.StringIO()
                with contextlib.redirect_stdout(captured):
                    result = transpile_and_exec(text, filepath, fallback_to_interpreter=True)
                program_output = captured.getvalue()
            else:
                result = transpile_and_exec(text, filepath, fallback_to_interpreter=True)
        except Exception as e:
            emit([runtime_error(f"compile failed: {e}", code="Z300", file=filepath)],
                 fmt=diag_format)
            sys.exit(1)

        if diag_format == "json":
            print(json.dumps({"ok": True, "result": str(result) if result is not None else None, "output": program_output}))
        elif result is not None:
            print(result)


# ---------------------------------------------------------------------------
# Diagnostic parsing (for AI agents)
# ---------------------------------------------------------------------------

def diag_command(args, *, diag_format: str = "text"):
    """Read human-readable diagnostic output on stdin (or first arg) and
    print the structured JSON. Useful for AI agents that capture stderr
    and want a typed payload."""
    from .diagnostics import parse_diagnostics
    if args:
        text = args[0]
    else:
        text = sys.stdin.read()
    diags = parse_diagnostics(text)
    print(json.dumps(diags, indent=2))


# ---------------------------------------------------------------------------
# Init command - scaffold a new project
# ---------------------------------------------------------------------------

def init_command(args, *, diag_format: str = "text"):
    """Scaffold a new Zap project with recommended structure."""
    name = args[0] if args else "my-zap-app"
    target_dir = os.path.join(os.getcwd(), name)

    if os.path.exists(target_dir):
        from .diagnostics import runtime_error, emit
        emit([runtime_error(f"directory already exists: {target_dir}", code="Z500")],
             fmt=diag_format)
        sys.exit(1)

    os.makedirs(target_dir, exist_ok=True)

    # Create main.zap entrypoint
    main_zap = f'''# {name} - Zap application
# Run with: zap run .

fn main()
  print("Hello from {name}!")

main()
'''
    with open(os.path.join(target_dir, "main.zap"), "w", encoding="utf-8") as f:
        f.write(main_zap)

    # Create zap.json config
    config = {
        "name": name,
        "version": "0.1.0",
        "entrypoint": "main.zap",
        "grammar": "2026.07",
        "dependencies": {}
    }
    import json as _json
    with open(os.path.join(target_dir, "zap.json"), "w", encoding="utf-8") as f:
        _json.dump(config, f, indent=2)

    # Create .gitignore
    gitignore = """__pycache__/
*.pyc
.zap_cache/
.env
*.log
"""
    with open(os.path.join(target_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(gitignore)

    print(f"Created {name}/")
    print(f"  main.zap      - entrypoint")
    print(f"  zap.json      - project config")
    print(f"  .gitignore    - git ignore rules")
    print(f"\nRun with: zap run {name}")


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

HELP_TEXT = """Zap — one language, every layer

Usage:
  zap run <file.zap|folder>   execute a .zap file or folder (auto-detects entrypoint)
  zap check <file.zap>        parse + type-check
  zap build <file.zap>        check + run
  zap test [path]             run @test / expect blocks
  zap compile <file.zap>      transpile to Python bytecode
  zap repl                    interactive REPL
  zap version                 print version + grammar version
  zap diag <text>             parse diagnostic text -> JSON
  zap init [name]             scaffold a new Zap project
  zap install                 install dependencies from zap.json
  zap add <spec>              add and install a dependency
  zap help                    this message

Common flags:
  --format=json               emit diagnostics as JSON (run, check, build, test)
  --no-color                  disable ANSI colors

Entrypoint detection for folders (in order):
  main.zap, index.zap, app.zap, server.zap, run.zap, start.zap, cli.zap, api.zap, web.zap

Examples:
  zap run main.zap            # run a single file
  zap run .                   # run current folder (finds main.zap, index.zap, etc.)
  zap run ./my-app            # run folder ./my-app
  zap init my-api             # create new project in ./my-api
  zap check main.zap --format=json  # machine-readable diagnostics for AI
"""


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def main(argv=None):
    argv = argv if argv is not None else sys.argv

    # Pre-scan for --format and --no-color so subcommands can use them.
    diag_format = "text"
    color = True
    remaining = []
    for a in argv[1:]:
        if a.startswith("--format="):
            val = a.split("=", 1)[1]
            if val in ("text", "json"):
                diag_format = val
        elif a == "--no-color":
            color = False
        else:
            remaining.append(a)

    if not color:
        # Crude ANSI strip: emit() already supports color=False. The
        # string formatters in src/diagnostics.py also check color arg.
        import src.diagnostics as _d
        _orig_format = _d.Diagnostic.format
        def _no_color(self):  # type: ignore[no-redef]
            return _orig_format(self, color=False)
        _d.Diagnostic.format = _no_color

    if not remaining:
        print(HELP_TEXT, file=sys.stderr)
        sys.exit(1)

    cmd = remaining[0]
    args = remaining[1:]

    if cmd == "repl":
        repl()
    elif cmd == "run":
        if not args:
            # Default to current directory for plug-and-play experience
            args = ["."]
        run_path(args[0], diag_format=diag_format)
    elif cmd == "check":
        if not args:
            print("usage: zap check <file.zap>", file=sys.stderr)
            sys.exit(1)
        check_file(args[0], diag_format=diag_format)
    elif cmd == "build":
        if not args:
            print("usage: zap build <file.zap>", file=sys.stderr)
            sys.exit(1)
        build_file(args[0], diag_format=diag_format)
    elif cmd == "test":
        test_command(args, diag_format=diag_format)
    elif cmd == "version" or cmd == "--version":
        version_command(args, diag_format=diag_format)
    elif cmd == "compile":
        if not args:
            print("usage: zap compile <file.zap> [--out <path>]", file=sys.stderr)
            sys.exit(1)
        # Parse --out flag
        out = None
        compile_args = []
        i = 0
        while i < len(args):
            if args[i] == "--out" and i + 1 < len(args):
                out = args[i + 1]
                i += 2
            else:
                compile_args.append(args[i])
                i += 1
        if not compile_args:
            print("usage: zap compile <file.zap> [--out <path>]", file=sys.stderr)
            sys.exit(1)
        compile_command(compile_args[0], out=out, diag_format=diag_format)
    elif cmd == "diag":
        diag_command(args, diag_format=diag_format)
    elif cmd == "init":
        init_command(args, diag_format=diag_format)
    elif cmd == "install":
        from .pkg import install
        install(args, diag_format=diag_format)
    elif cmd == "add":
        from .pkg import add
        add(args, diag_format=diag_format)
    elif cmd in ("help", "--help", "-h"):
        print(HELP_TEXT)
    else:
        # Back-compat: if the first arg looks like a file, run it.
        if os.path.exists(cmd):
            run_path(cmd, diag_format=diag_format)
            return
        print(f"unknown command: {cmd}\n\n{HELP_TEXT}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()