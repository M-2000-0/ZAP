"""Zap compile support.

This module provides a minimal compile path for `zap compile`.
It transpiles Zap source into an executable Python wrapper and writes
an adjacent `.py` / `.pyc` file next to the original .zap source.

The implementation is intentionally a small compatibility shim rather
than a full native backend.
"""

from __future__ import annotations

import json
import os
import py_compile
import textwrap

from .lexer import Lexer
from .parser import Parser
from .evaluator import Evaluator


def transpile_to_python_source(source: str, filename: str | None = None) -> str:
    """Return Python source that executes the given Zap source."""
    filename = filename or "<zap>"
    zap_text = json.dumps(source)
    python_filename = json.dumps(filename)
    return textwrap.dedent(f"""\
        # Auto-generated Zap wrapper for {filename}
        from __future__ import annotations
        import json
        from src.lexer import Lexer
        from src.parser import Parser
        from src.evaluator import Evaluator

        zap_source = {zap_text}
        filepath = {python_filename}

        tokens = Lexer(zap_source, filepath).tokenize()
        prog = Parser(tokens).parse()
        ev = Evaluator(current_file=filepath)
        result = ev.evaluate(prog)
        if result is not None:
            print(result)
    """)


def _write_python_source(source: str, out_path: str) -> None:
    dirpath = os.path.dirname(out_path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(source)


def transpile_and_exec(source: str, filepath: str, *, fallback_to_interpreter: bool = True):
    """Transpile Zap source to Python and execute it immediately."""
    python_source = transpile_to_python_source(source, filepath)
    py_path = filepath + ".py"
    pyc_path = filepath + ".pyc"
    _write_python_source(python_source, py_path)
    try:
        py_compile.compile(py_path, cfile=pyc_path, doraise=True)
    except Exception:
        if fallback_to_interpreter:
            tokens = Lexer(source, filepath).tokenize()
            prog = Parser(tokens).parse()
            return Evaluator(current_file=filepath).evaluate(prog)
        raise

    globals_: dict[str, object] = {"__name__": "__main__", "__file__": py_path}
    exec(compile(python_source, py_path, "exec"), globals_)
    return globals_.get("result")
