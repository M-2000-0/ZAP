"""
CLI entrypoint. The grammar-version check, the diagnostic formatting, and
all subcommands live here.

Subcommands:
  zap run <file>           execute a .zap file
  zap check <file>         parse + type-check, emit diagnostics
  zap build <file>         check + run
  zap repl                 interactive REPL
  zap test [path]          run @test / expect blocks
  zap version              print VERSION and GRAMMAR_VERSION
  zap compile <file>       transpile to Python bytecode (stub)
  zap diag <text>          parse human-readable diagnostic output -> JSON
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


def run_file(filepath, *, diag_format: str = "text"):
    from .lexer import Lexer
    from .parser import Parser
    from .evaluator import Evaluator
    from .diagnostics import Span, runtime_error, emit, parse_grammar_pragma
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


def check_file(filepath, *, diag_format: str = "text"):
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
    print("ok")


def build_file(filepath, *, diag_format: str = "text"):
    # build == check + run, both with diagnostics
    check_file(filepath, diag_format=diag_format)
    run_file(filepath, diag_format=diag_format)


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


def test_command(args, *, diag_format: str = "text"):
    """Run all @test / expect blocks under the given path (default: cwd)."""
    from .test_runner import run_tests
    path = args[0] if args else "."
    summary = run_tests(path, diag_format=diag_format)
    if summary.failed or summary.errored:
        sys.exit(1)


def version_command(_args, *, diag_format: str = "text"):
    from .version import VERSION, GRAMMAR_VERSION
    if diag_format == "json":
        print(json.dumps({"version": VERSION, "grammar": GRAMMAR_VERSION}))
    else:
        print(f"Zap v{VERSION}")
        print(f"Grammar: {GRAMMAR_VERSION}")


def compile_command(filepath, *, out: str | None = None, diag_format: str = "text"):
    """Transpile a .zap file to Python bytecode (cached as .pyc next to the
    source) and exec it. Falls back to the tree-walking interpreter on
    unsupported AST nodes."""
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

    from .compiler import transpile_to_python_source, transpile_and_exec
    try:
        result = transpile_and_exec(text, filepath, fallback_to_interpreter=True)
    except Exception as e:
        emit([runtime_error(f"compile failed: {e}", code="Z300", file=filepath)],
             fmt=diag_format)
        sys.exit(1)

    if result is not None:
        print(result)


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


HELP_TEXT = """Zap — one language, every layer

Usage:
  zap run <file.zap>         execute a .zap file
  zap check <file.zap>       parse + type-check
  zap build <file.zap>       check + run
  zap test [path]            run @test / expect blocks
  zap compile <file.zap>     transpile to Python bytecode
  zap repl                   interactive REPL
  zap version                print version + grammar version
  zap diag                   parse diagnostic text -> JSON
  zap help                   this message

Common flags:
  --format=json              emit diagnostics as JSON (run, check, build, test)
  --no-color                 disable ANSI colors
"""


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
            print("usage: zap run <file.zap>", file=sys.stderr)
            sys.exit(1)
        run_file(args[0], diag_format=diag_format)
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
            print("usage: zap compile <file.zap>", file=sys.stderr)
            sys.exit(1)
        compile_command(args[0], diag_format=diag_format)
    elif cmd == "diag":
        diag_command(args, diag_format=diag_format)
    elif cmd in ("help", "--help", "-h"):
        print(HELP_TEXT)
    else:
        # Back-compat: if the first arg looks like a file, run it.
        if os.path.exists(cmd):
            run_file(cmd, diag_format=diag_format)
            return
        print(f"unknown command: {cmd}\n\n{HELP_TEXT}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
