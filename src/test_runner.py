"""
`zap test` — the Zap test runner.

A test in Zap is any `expect` statement or any `check:` block anywhere in
the program. The runner walks the AST, executes the program, and turns
each assertion into a pass/fail entry. Output is a human summary by
default and JSON when `--format=json` is requested.

Test discovery:
  1. If a path is given, recurse into it for .zap files.
  2. Otherwise, recurse from the current directory.
  3. Files starting with `test_` or in a `tests/` directory are
     preferred, but every .zap file is loaded.

Each file runs in a fresh Evaluator with the on-disk `.zapcontext` as its
memory. This mirrors the way real projects are run.

The runner does NOT halt on the first failure. It collects all
assertions and reports at the end, which is what AI agents need to
iterate: the model wants to see "5/7 passed, here are the 2 failures"
rather than "exploded on failure 1".
"""

from __future__ import annotations

import os
import sys
import json
import time
from dataclasses import dataclass, field

from .ast_nodes import (
    Program, ExpectStmt, CheckBlock, FnDef, ContractAnnotation,
    ContractClause, Identifier, Call, Literal, IntendStmt, ServiceDecl,
    DatabaseDecl, ApiEndpoint, SchemaDecl,
)


@dataclass
class TestResult:
    name: str
    file: str
    line: int
    passed: bool
    message: str = ""
    error: str | None = None


@dataclass
class FileSummary:
    file: str
    tests: list[TestResult] = field(default_factory=list)
    error: str | None = None
    duration_ms: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.passed)

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if not t.passed)


@dataclass
class RunSummary:
    files: list[FileSummary] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(len(f.tests) for f in self.files)

    @property
    def passed(self) -> int:
        return sum(f.passed for f in self.files)

    @property
    def failed(self) -> int:
        return sum(f.failed for f in self.files)

    @property
    def errored(self) -> int:
        return sum(1 for f in self.files if f.error)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errored": self.errored,
            "files": [
                {
                    "file": f.file,
                    "passed": f.passed,
                    "failed": f.failed,
                    "duration_ms": round(f.duration_ms, 2),
                    "error": f.error,
                    "tests": [
                        {
                            "name": t.name,
                            "line": t.line,
                            "passed": t.passed,
                            "message": t.message,
                            "error": t.error,
                        }
                        for t in f.tests
                    ],
                }
                for f in self.files
            ],
        }


# ── discovery ───────────────────────────────────────────────────────────


def discover_files(path: str) -> list[str]:
    """Recurse into `path` and return every .zap file found."""
    if os.path.isfile(path):
        return [path] if path.endswith(".zap") else []
    if not os.path.isdir(path):
        return []
    out: list[str] = []
    for root, _, files in os.walk(path):
        # Skip __pycache__ and .git
        if "__pycache__" in root or "/.git" in root or "\\.git" in root:
            continue
        for name in sorted(files):
            if name.endswith(".zap"):
                out.append(os.path.join(root, name))
    return out


# ── test extraction ─────────────────────────────────────────────────────


def _condition_repr(node) -> str:
    """Best-effort source-text for an expression node. Used for the
    assertion message in test output. Returns a stable string even when
    the AST lacks a `source` field."""
    if isinstance(node, Literal):
        return repr(node.value)
    if isinstance(node, Identifier):
        return node.name
    if isinstance(node, Call):
        callee = _condition_repr(node.callee)
        args = ", ".join(_condition_repr(a) for a in node.args)
        return f"{callee}({args})"
    return f"<expr@{getattr(node, 'line', '?')}:{getattr(node, 'col', '?')}>"


def extract_tests(prog: Program) -> list[tuple[str, str, int]]:
    """
    Walk a Program and yield (name, source_text, line) for every test
    that can be statically observed. Two sources:

      1. Top-level `expect cond "msg"` statements.
      2. `check:` blocks (each `expect` inside is a test).

    Note: we extract statically, then re-execute the program. The
    interpreter collects the pass/fail status by side-effect on the
    `_test_results` list of the captured Evaluator. That decouples
    discovery from evaluation cleanly.
    """
    out: list[tuple[str, str, int]] = []
    for stmt in prog.stmts:
        _extract_from_stmt(stmt, out, prefix="")
    return out


def _extract_from_stmt(stmt, out: list, prefix: str) -> None:
    if isinstance(stmt, ExpectStmt):
        text = _condition_repr(stmt.condition)
        name = f"{prefix}expect {text}"
        if stmt.message:
            name += f'  // "{stmt.message}"'
        out.append((name, text, stmt.line))
    elif isinstance(stmt, CheckBlock):
        for i, a in enumerate(stmt.assertions):
            if isinstance(a, ExpectStmt):
                text = _condition_repr(a.condition)
                name = f"{prefix}check[{i}]: expect {text}"
                if a.message:
                    name += f'  // "{a.message}"'
                out.append((name, text, a.line))
    elif isinstance(stmt, FnDef):
        # Don't recurse into function bodies — expects there are local
        # assertions, not test cases. Only top-level and check-block
        # expects are tests.
        return
    # Other statement types don't carry expects.


# ── execution ──────────────────────────────────────────────────────────


def _evaluate_with_capture(source: str, filepath: str):
    """Run the file and return a list of TestResult from expect/check assertions."""
    from .lexer import Lexer
    from .parser import Parser
    from .evaluator import Evaluator, ReturnSignal

    class TestEvaluator(Evaluator):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.tests: list[TestResult] = []

        def _record_expect(self, stmt: ExpectStmt, passed: bool, error: str | None = None, prefix: str = ""):
            name = _condition_repr(stmt.condition)
            if stmt.message:
                name += f'  // "{stmt.message}"'
            if prefix:
                name = f"{prefix}{name}"
            self.tests.append(TestResult(
                name=name,
                file=filepath,
                line=stmt.line,
                passed=passed,
                message=stmt.message or "",
                error=error,
            ))

        def _eval_expect(self, stmt: ExpectStmt):
            try:
                val = super()._eval_expect(stmt)
                self._record_expect(stmt, True)
                return val
            except Exception as e:
                self._record_expect(stmt, False, error=f"{type(e).__name__}: {e}")
                return None

        def _record_check(self, assertion, passed: bool, error: str | None = None, prefix: str = ""):
            if isinstance(assertion, ExpectStmt):
                name = _condition_repr(assertion.condition)
                if assertion.message:
                    name += f'  // "{assertion.message}"'
            else:
                name = f"check expression@L{assertion.line}:{getattr(assertion, 'col', '?')}"
            if prefix:
                name = f"{prefix}{name}"
            self.tests.append(TestResult(
                name=name,
                file=filepath,
                line=assertion.line,
                passed=passed,
                message=assertion.message if isinstance(assertion, ExpectStmt) else "",
                error=error,
            ))

        def _eval_check(self, stmt: CheckBlock):
            results = []
            for idx, assertion in enumerate(stmt.assertions):
                prefix = f"check[{idx}]: "
                if isinstance(assertion, ExpectStmt):
                    try:
                        val = super()._eval_expect(assertion)
                        self._record_check(assertion, True, prefix=prefix)
                        results.append(val)
                    except Exception as e:
                        self._record_check(assertion, False, error=f"{type(e).__name__}: {e}", prefix=prefix)
                        results.append(None)
                else:
                    try:
                        val = self._eval_expr(assertion)
                        passed = self._is_truthy(val)
                        if passed:
                            self._record_check(assertion, True, prefix=prefix)
                        else:
                            self._record_check(assertion, False,
                                               error="check expression evaluated to false",
                                               prefix=prefix)
                        results.append(val)
                    except Exception as e:
                        self._record_check(assertion, False,
                                           error=f"{type(e).__name__}: {e}",
                                           prefix=prefix)
                        results.append(None)
            return results

    results: list[TestResult] = []
    try:
        tokens = Lexer(source, filepath).tokenize()
        prog = Parser(tokens).parse()
        ev = TestEvaluator(current_file=filepath)
        try:
            ev.evaluate(prog)
        except ReturnSignal:
            pass
        results = ev.tests
    except Exception as e:
        results.append(TestResult(
            name="<module load>",
            file=filepath,
            line=0,
            passed=False,
            error=f"{type(e).__name__}: {e}",
        ))
    return results


def run_file(filepath: str) -> FileSummary:
    summary = FileSummary(file=filepath)
    start = time.time()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        summary.error = f"could not read file: {e}"
        summary.duration_ms = (time.time() - start) * 1000
        return summary

    # Parse once for discovery
    from .lexer import Lexer
    from .parser import Parser
    try:
        tokens = Lexer(source, filepath).tokenize()
        prog = Parser(tokens).parse()
    except Exception as e:
        summary.error = f"parse error: {e}"
        summary.duration_ms = (time.time() - start) * 1000
        return summary

    summary.tests = _evaluate_with_capture(source, filepath)
    summary.duration_ms = (time.time() - start) * 1000
    return summary


def run_tests(path: str, *, diag_format: str = "text") -> RunSummary:
    files = discover_files(path)
    summary = RunSummary()
    if not files:
        if diag_format == "json":
            print(json.dumps({"error": "no .zap files found", "path": path}))
        else:
            print(f"no .zap files found under {path!r}", file=sys.stderr)
        return summary
    for f in files:
        summary.files.append(run_file(f))

    # Emit
    if diag_format == "json":
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        for fs in summary.files:
            tag = "OK" if fs.failed == 0 and not fs.error else "FAIL"
            print(f"  [{tag}] {fs.file}  ({fs.passed}/{len(fs.tests)} passed, {fs.duration_ms:.0f}ms)")
            if fs.error:
                print(f"        {fs.error}")
            for t in fs.tests:
                mark = "+" if t.passed else "x"
                print(f"        {mark} L{t.line}: {t.name}")
                if not t.passed and t.error:
                    print(f"             {t.error}")
        print()
        print(f"  {summary.passed}/{summary.total} tests passed across {len(summary.files)} file(s)")
        if summary.failed:
            print(f"  {summary.failed} failure(s)", file=sys.stderr)
    return summary
