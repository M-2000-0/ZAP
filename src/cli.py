import sys
import os
import traceback


def run_file(filepath):
    from .lexer import Lexer
    from .parser import Parser
    from .evaluator import Evaluator

    if not os.path.exists(filepath):
        print(f"error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    lexer = Lexer(text, filepath)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    try:
        prog = parser.parse()
    except SyntaxError as e:
        print(f"parse error: {e}", file=sys.stderr)
        sys.exit(1)

    evaluator = Evaluator(current_file=filepath)
    try:
        result = evaluator.evaluate(prog)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

    if result is not None:
        print(result)


def check_file(filepath):
    from .lexer import Lexer
    from .parser import Parser
    from .types import TypeChecker

    if not os.path.exists(filepath):
        print(f"error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    lexer = Lexer(text, filepath)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    parser.recovery_mode = True
    try:
        prog = parser.parse()
    except SyntaxError as e:
        print(f"parse error: {e}", file=sys.stderr)
        sys.exit(1)

    had_errors = False
    for err in parser.errors:
        print(f"  {err}", file=sys.stderr)
        had_errors = True

    tc = TypeChecker()
    try:
        tc.check(prog)
    except Exception as e:
        print(f"  type error: {e}", file=sys.stderr)
        had_errors = True

    for line, col, msg in tc.errors:
        print(f"  L{line}:{col}: {msg}", file=sys.stderr)
        had_errors = True

    if had_errors:
        sys.exit(1)

    print("ok")


def build_file(filepath):
    from .lexer import Lexer
    from .parser import Parser
    from .evaluator import Evaluator

    basedir = os.path.dirname(os.path.abspath(filepath))
    sys.path.insert(0, basedir)

    if not os.path.exists(filepath):
        print(f"error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    lexer = Lexer(text, filepath)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    parser.recovery_mode = True
    try:
        prog = parser.parse()
    except SyntaxError as e:
        print(f"parse error: {e}", file=sys.stderr)
        sys.exit(1)

    evaluator = Evaluator(current_file=filepath)

    def print_error(msg):
        print(f"  {msg}", file=sys.stderr)

    for err in parser.errors:
        print_error(err)

    tc_result = None
    try:
        from .types import TypeChecker
        tc = TypeChecker()
        tc.check(prog)
        for line, col, msg in tc.errors:
            print_error(f"L{line}:{col}: {msg}")
        tc_result = len(tc.errors) == 0
    except Exception as e:
        print_error(f"type check error: {e}")
        tc_result = False

    try:
        result = evaluator.evaluate(prog)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

    if tc_result is False:
        print("warning: type check had errors", file=sys.stderr)

    if result is not None:
        print(result)


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

    evaluator = Evaluator()
    print("Zap REPL -- type 'exit' or Ctrl+C to quit")
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

        if buffer:
            buffer += "\n" + line
        else:
            buffer = line

        # Multi-line detection: unbalanced brackets/braces/parens, or trailing : \
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
            lexer = Lexer(buffer, "<repl>")
            tokens = lexer.tokenize()
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


def main():
    if len(sys.argv) < 2:
        print("usage: zap <command> [file]", file=sys.stderr)
        print("commands: run, check, build, repl", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "repl":
        repl()
    elif command == "run":
        if len(sys.argv) < 3:
            print("usage: zap run <file.zap>", file=sys.stderr)
            sys.exit(1)
        run_file(sys.argv[2])
    elif command == "check":
        if len(sys.argv) < 3:
            print("usage: zap check <file.zap>", file=sys.stderr)
            sys.exit(1)
        check_file(sys.argv[2])
    elif command == "build":
        if len(sys.argv) < 3:
            print("usage: zap build <file.zap>", file=sys.stderr)
            sys.exit(1)
        build_file(sys.argv[2])
    else:
        print(f"unknown command: {command}", file=sys.stderr)
        print("commands: run, check, build, repl", file=sys.stderr)
        sys.exit(1)
