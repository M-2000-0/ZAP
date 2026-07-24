"""Tests for the grammar version pragma and version command."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.version import (
    VERSION, GRAMMAR_VERSION, parse_grammar_pragma, GRAMMAR_0_2_KEYWORDS, is_keyword,
)


def test_version_constants_are_strings():
    assert isinstance(VERSION, str)
    assert isinstance(GRAMMAR_VERSION, str)
    assert "." in VERSION
    print("  ok version constants are strings")


def test_grammar_version_is_locked():
    """GRAMMAR_VERSION is a stable string AI tools and humans can target."""
    assert GRAMMAR_VERSION == "0.2"
    print("  ok grammar version is locked at 0.2")


def test_pragma_parsing():
    cases = [
        ("# grammar: 0.1", "0.1"),
        ("# grammar: 0.2\nlet x = 1", "0.2"),
        ("let x = 1", None),
        ("# grammar = 0.3", "0.3"),
        ("# grammar 0.4\nlet x", "0.4"),
        ("#\n# grammar: 0.5\nlet x", "0.5"),
        ("", None),
        ("# grammar:0.6", "0.6"),
        ("# grammar : 0.7", "0.7"),
    ]
    for src, expected in cases:
        got = parse_grammar_pragma(src)
        assert got == expected, f"parse_grammar_pragma({src!r}) = {got!r}, expected {expected!r}"
    print("  ok pragma parses all 10 cases")


def test_pragma_stops_at_first_code_line():
    """A comment after code is not a pragma."""
    src = "let x = 1\n# grammar: 0.1\n"
    assert parse_grammar_pragma(src) is None
    print("  ok pragma stops at first code line")


def test_keyword_set_is_stable():
    """The keyword set is locked. AI tools can rely on these being reserved."""
    expected = {
        "fn", "let", "if", "el", "for", "in", "while", "ret",
        "true", "false", "none", "and", "or", "not",
        "import", "from", "class", "async", "await", "match", "intend",
        "service", "database", "api", "page", "schema", "model", "expose",
        "requires", "ensures", "invariant", "expect", "permission",
        "concurrent", "channel", "guarantees", "version", "check",
        "break", "continue",
    }
    assert GRAMMAR_0_2_KEYWORDS == frozenset(expected)
    assert is_keyword("fn")
    assert is_keyword("service")
    assert not is_keyword("foo")
    assert not is_keyword("bar")
    print("  ok keyword set is stable and is_keyword works")


def test_cli_version_command_runs(tmp_cwd):
    """`python -m src.cli version` works in isolation."""
    import subprocess
    env = os.environ.copy()
    # PYTHONPATH so src/ resolves when cwd is the empty temp dir
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..")
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "version"],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, f"stderr={result.stderr!r}"
    assert "Zap v" in result.stdout
    assert "0.2" in result.stdout
    print("  ok CLI version command runs")


def test_cli_check_rejects_wrong_grammar(tmp_cwd):
    """`zap check` returns non-zero exit code on grammar mismatch."""
    import subprocess
    src = "# grammar: 0.1\nlet x = 1\n"
    path = os.path.join(tmp_cwd, "bad.zap")
    with open(path, "w") as f:
        f.write(src)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..")
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "check", path],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode != 0, f"stderr={result.stderr!r}"
    assert "Z001" in result.stderr
    print("  ok CLI rejects wrong grammar version")


def test_cli_check_accepts_matching_grammar(tmp_cwd):
    """`zap check` returns 0 on matching grammar."""
    import subprocess
    src = "# grammar: 0.2\nlet x = 1\n"
    path = os.path.join(tmp_cwd, "ok.zap")
    with open(path, "w") as f:
        f.write(src)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..")
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "check", path],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    print("  ok CLI accepts matching grammar version")


def test_cli_check_emits_json_on_request(tmp_cwd):
    """`zap check --format=json` returns structured diagnostics."""
    import subprocess
    import json
    src = "# grammar: 0.1\nlet x = 1\n"
    path = os.path.join(tmp_cwd, "bad.zap")
    with open(path, "w") as f:
        f.write(src)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..")
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "check", path, "--format=json"],
        capture_output=True, text=True, env=env,
    )
    diags = json.loads(result.stderr)
    assert isinstance(diags, dict), f"expected dict, got {type(diags)}"
    assert "diagnostics" in diags, f"missing 'diagnostics' key in {diags}"
    assert any(d["code"] == "Z001" for d in diags["diagnostics"])
    print("  ok CLI emits JSON diagnostics")


if __name__ == "__main__":
    import contextlib
    with tempfile.TemporaryDirectory() as tmp:
        # Inject a `tmp_cwd` fixture via attribute on the module.
        import sys as _sys
        _sys.modules[__name__].tmp_cwd = tmp
        for name, fn in list(globals().items()):
            if name.startswith("test_cli_") and callable(fn):
                fn.__globals__["tmp_cwd"] = tmp
        test_version_constants_are_strings()
        test_grammar_version_is_locked()
        test_pragma_parsing()
        test_pragma_stops_at_first_code_line()
        test_keyword_set_is_stable()
        test_cli_version_command_runs(tmp)
        test_cli_check_rejects_wrong_grammar(tmp)
        test_cli_check_accepts_matching_grammar(tmp)
        test_cli_check_emits_json_on_request(tmp)
    print("all version tests passed")
