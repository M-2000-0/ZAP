"""Zap compile support.

This module provides a minimal compile path for `zap compile`.
It transpiles Zap source into an executable Python wrapper and writes
an adjacent `.py` / `.pyc` file next to the original .zap source.

The implementation is intentionally a small compatibility shim rather
than a full native backend.

Caching: compiled bytecode is cached in `.zap_cache/` next to the source
file. The cache key is based on the file's mtime and size, so edits
automatically invalidate the cache.
"""

from __future__ import annotations

import hashlib
import json
import os
import py_compile
import textwrap

from .lexer import Lexer
from .parser import Parser
from .evaluator import Evaluator

CACHE_DIR = ".zap_cache"


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


import tempfile


def _cache_key(filepath: str, source: str) -> str:
    """Generate a cache key based on file mtime, size, and source hash."""
    stat = os.stat(filepath)
    key = f"{stat.st_mtime_ns}_{stat.st_size}_{hashlib.sha256(source.encode()).hexdigest()[:16]}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def _cache_path(filepath: str, source: str) -> str:
    """Get the cache file path for a given source file."""
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(filepath)), CACHE_DIR)
    os.makedirs(cache_dir, exist_ok=True)
    key = _cache_key(filepath, source)
    return os.path.join(cache_dir, key + ".pyc")


def transpile_and_exec(source: str, filepath: str, *, fallback_to_interpreter: bool = True,
                       use_cache: bool = True):
    """Transpile Zap source to Python and execute it immediately.

    If use_cache is True, compiled bytecode is cached in .zap_cache/ and
    reused on subsequent runs (invalidated by mtime/size changes).
    """
    # Try cache first
    if use_cache:
        cached_pyc = _cache_path(filepath, source)
        if os.path.exists(cached_pyc):
            try:
                with open(cached_pyc, "rb") as f:
                    code = f.read()
                globals_: dict[str, object] = {"__name__": "__main__", "__file__": filepath}
                exec(compile(code, filepath, "exec"), globals_)
                return globals_.get("result")
            except Exception:
                pass  # Cache miss/corrupt, fall through to recompile

    python_source = transpile_to_python_source(source, filepath)
    with tempfile.TemporaryDirectory() as tmpdir:
        py_path = os.path.join(tmpdir, os.path.basename(filepath) + ".py")
        pyc_path = os.path.join(tmpdir, os.path.basename(filepath) + ".pyc")
        _write_python_source(python_source, py_path)
        try:
            py_compile.compile(py_path, cfile=pyc_path, doraise=True)
        except Exception:
            if fallback_to_interpreter:
                tokens = Lexer(source, filepath).tokenize()
                prog = Parser(tokens).parse()
                return Evaluator(current_file=filepath).evaluate(prog)
            raise

        # Cache the compiled bytecode
        if use_cache:
            cached_pyc = _cache_path(filepath, source)
            try:
                with open(pyc_path, "rb") as src:
                    with open(cached_pyc, "wb") as dst:
                        dst.write(src.read())
            except Exception:
                pass  # Cache write failure is non-fatal

        globals_: dict[str, object] = {"__name__": "__main__", "__file__": py_path}
        exec(compile(python_source, py_path, "exec"), globals_)
        return globals_.get("result")
