"""
Structured diagnostic system for Zap.

A Diagnostic carries everything an AI agent (or a human) needs to fix the
problem: a stable error code, a span pointing at the source, the message,
and a list of suggested fixes. Diagnostics serialize to JSON so an LLM
can parse them programmatically.

The existing string error path keeps working — `Diagnostic.format()` is
the human-readable string. The JSON path is opt-in via `zap check --format=json`
and via `parse_diagnostics(string)` for tools that already have a stream
of human-readable output.

Error code ranges:
  Z001-Z099  parser / grammar version
  Z100-Z199  lexer
  Z200-Z299  type checker
  Z300-Z399  runtime
  Z400-Z499  contracts
  Z500-Z599  import / module
  Z600-Z699  test runner
  Z900-Z999  internal
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


@dataclass
class Span:
    """A range in source. End is exclusive. line/col are 1-indexed."""
    line: int
    col: int
    end_line: int | None = None
    end_col: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Fix:
    """A machine-applicable or human-readable suggested fix."""
    description: str
    replacement: str | None = None
    span: Span | None = None

    def to_dict(self) -> dict:
        d = {"description": self.description}
        if self.replacement is not None:
            d["replacement"] = self.replacement
        if self.span is not None:
            d["span"] = self.span.to_dict()
        return d


@dataclass
class Diagnostic:
    code: str
    severity: Severity
    message: str
    span: Span | None = None
    expected: list[str] = field(default_factory=list)
    got: str | None = None
    fixes: list[Fix] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    file: str | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.span is not None:
            d["span"] = self.span.to_dict()
        if self.expected:
            d["expected"] = self.expected
        if self.got is not None:
            d["got"] = self.got
        if self.fixes:
            d["fixes"] = [f.to_dict() for f in self.fixes]
        if self.notes:
            d["notes"] = list(self.notes)
        if self.file is not None:
            d["file"] = self.file
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def format(self, color: bool = True) -> str:
        """Human-readable single-line form, optionally ANSI-colored."""
        if color:
            RED = "\x1b[31m"
            YELLOW = "\x1b[33m"
            BLUE = "\x1b[34m"
            DIM = "\x1b[2m"
            RESET = "\x1b[0m"
        else:
            RED = YELLOW = BLUE = DIM = RESET = ""

        sev_color = RED if self.severity == Severity.ERROR else (
            YELLOW if self.severity == Severity.WARNING else BLUE
        )
        loc = ""
        if self.file:
            loc = f"{self.file}:"
        if self.span is not None:
            loc += f"{self.span.line}:{self.span.col}"
        prefix = f"{sev_color}{self.severity.value}{RESET}[{self.code}]"
        if loc:
            prefix += f" {DIM}{loc}{RESET}"
        out = f"{prefix}: {self.message}"
        if self.got is not None:
            out += f"\n  {DIM}got: {RESET}{self.got}"
        if self.expected:
            out += f"\n  {DIM}expected: {RESET}" + " | ".join(self.expected)
        for fix in self.fixes:
            out += f"\n  {BLUE}fix:{RESET} {fix.description}"
            if fix.replacement is not None:
                out += f"  →  {fix.replacement}"
        for note in self.notes:
            out += f"\n  {DIM}note: {note}{RESET}"
        return out


# ── Factory helpers — the public API the rest of the codebase should use ──


def parse_error(message: str, *, code: str = "Z001", span: Span | None = None,
                got: str | None = None, expected: list[str] | None = None,
                fixes: list[Fix] | None = None, file: str | None = None) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        span=span,
        got=got,
        expected=expected or [],
        fixes=fixes or [],
        file=file,
    )


def parse_warning(message: str, *, code: str = "Z002", span: Span | None = None,
                  file: str | None = None) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.WARNING,
        message=message,
        span=span,
        file=file,
    )


def type_error(message: str, *, code: str = "Z200", span: Span | None = None,
               got: str | None = None, expected: list[str] | None = None,
               fixes: list[Fix] | None = None, file: str | None = None) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        span=span,
        got=got,
        expected=expected or [],
        fixes=fixes or [],
        file=file,
    )


def runtime_error(message: str, *, code: str = "Z300", span: Span | None = None,
                  file: str | None = None) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        span=span,
        file=file,
    )


def contract_violation(message: str, *, code: str = "Z400", span: Span | None = None,
                       file: str | None = None) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        span=span,
        file=file,
    )


def test_failure(message: str, *, code: str = "Z600", span: Span | None = None,
                 file: str | None = None) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        span=span,
        file=file,
    )


# ── Parsing human-readable output back into structured form ──


def parse_diagnostics(text: str) -> list[dict]:
    """
    Parse the human-readable diagnostic output back into a list of
    diagnostic dicts. This is the round-trip guarantee: anything we print
    via `Diagnostic.format()` should be parseable here.

    The format is intentionally line-oriented so a partial stream (one
    diagnostic at a time from a subprocess) can be parsed incrementally.
    """
    diagnostics: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        stripped = line.strip()
        # Strip ANSI escape sequences
        clean = _strip_ansi(stripped)
        if not clean:
            continue
        # New diagnostic header: "error[Z001] file:line:col: message" or
        # "error[Z001] line:col: message" or "error[Z001]: message"
        header = _parse_header(clean)
        if header is not None:
            if current is not None:
                diagnostics.append(current)
            current = header
            continue
        if current is None:
            # Stray line, skip
            continue
        # Continuation lines
        if clean.startswith("got:"):
            current["got"] = clean[4:].strip()
        elif clean.startswith("expected:"):
            current["expected"] = [s.strip() for s in clean[9:].split("|")]
        elif clean.startswith("fix:"):
            fix_text = clean[4:].strip()
            replacement = None
            if "→" in fix_text:
                fix_text, replacement = fix_text.split("→", 1)
                fix_text = fix_text.strip()
                replacement = replacement.strip()
            current.setdefault("fixes", []).append({
                "description": fix_text,
                "replacement": replacement,
            })
        elif clean.startswith("note:"):
            current.setdefault("notes", []).append(clean[5:].strip())
    if current is not None:
        diagnostics.append(current)
    return diagnostics


def _strip_ansi(s: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def _parse_header(line: str) -> dict | None:
    # Match "<severity>[<code>] <loc>: <message>"
    import re
    m = re.match(
        r"^(error|warning|note)\[(Z\d{3})\]\s+"
        r"(?:([^:]+):)?(\d+):(\d+):\s+(.*)$",
        line,
    )
    if not m:
        return None
    sev, code, file_, line_, col_, msg = m.groups()
    d: dict = {
        "code": code,
        "severity": sev,
        "message": msg,
        "span": {"line": int(line_), "col": int(col_)},
    }
    if file_:
        d["file"] = file_
    return d


# ── Convenience: collect + emit ──


def emit(diagnostics: list[Diagnostic], fmt: str = "text", stream=None) -> None:
    """Print diagnostics in the requested format. fmt is 'text' or 'json'.

    JSON output is wrapped in a structured object with a summary so AI agents
    can quickly assess the result without parsing the full list:
    {
      "ok": false,
      "count": 2,
      "errors": 1,
      "warnings": 1,
      "diagnostics": [...]
    }
    """
    import sys
    stream = stream or sys.stderr
    if fmt == "json":
        errors = sum(1 for d in diagnostics if d.severity == Severity.ERROR)
        warnings = sum(1 for d in diagnostics if d.severity == Severity.WARNING)
        out = {
            "ok": len(diagnostics) == 0,
            "count": len(diagnostics),
            "errors": errors,
            "warnings": warnings,
            "diagnostics": [d.to_dict() for d in diagnostics],
        }
        print(json.dumps(out, indent=2), file=stream)
    else:
        for d in diagnostics:
            print(d.format(), file=stream)
