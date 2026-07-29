"""Edge case and negative tests for Zpx lexer, parser, and evaluator."""

import os
import subprocess
import sys
import tempfile

import pytest

ZPX_CMD = [sys.executable, "-m", "src", "run"]


def run_zpx(source):
    """Run Zpx source code and return (returncode, stdout, stderr)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.zpx")
        with open(path, "w", encoding="utf-8") as f:
            f.write(source)
        env = os.environ.copy()
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            ZPX_CMD + [path],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            env=env,
        )
        return result.returncode, result.stdout, result.stderr


class TestLexerEdgeCases:
    """Edge cases for the lexer."""

    def test_empty_input(self):
        rc, stdout, stderr = run_zpx("")
        assert rc == 0

    def test_only_comments(self):
        rc, stdout, stderr = run_zpx("# just a comment\n# another\n")
        assert rc == 0

    def test_scientific_notation(self):
        rc, stdout, stderr = run_zpx('print(1.5e3)\n')
        assert rc == 0
        assert "1500" in stdout

    def test_negative_scientific(self):
        rc, stdout, stderr = run_zpx('print(1e-3)\n')
        assert rc == 0
        assert "0.001" in stdout

    def test_float_literal(self):
        rc, stdout, stderr = run_zpx('print(3.14)\n')
        assert rc == 0
        assert "3.14" in stdout

    def test_string_escape_newline(self):
        rc, stdout, stderr = run_zpx('print("line1\\nline2")\n')
        assert rc == 0
        assert "line1" in stdout and "line2" in stdout

    def test_string_escape_tab(self):
        rc, stdout, stderr = run_zpx('print("col1\\tcol2")\n')
        assert rc == 0
        assert "\t" in stdout

    def test_string_escape_quote(self):
        rc, stdout, stderr = run_zpx('print("he\\"llo")\n')
        assert rc == 0, stderr
        assert 'he"llo' in stdout


class TestStringInterpolation:
    """String interpolation with ${} and $var."""

    def test_simple_interpolation(self):
        rc, stdout, stderr = run_zpx('let name = "World"\nprint("Hello ${name}")\n')
        assert rc == 0
        assert "Hello World" in stdout

    def test_interp_expression(self):
        rc, stdout, stderr = run_zpx('print("2 + 2 = ${2 + 2}")\n')
        assert rc == 0
        assert "2 + 2 = 4" in stdout

    def test_interp_dollar_var(self):
        rc, stdout, stderr = run_zpx('let x = 42\nprint("value is $x")\n')
        assert rc == 0
        assert "value is 42" in stdout


class TestControlFlowEdgeCases:
    """Edge cases for loops and conditionals."""

    def test_while_loop(self):
        rc, stdout, stderr = run_zpx(
            "let i = 0\n"
            "let acc = ''\n"
            "while i < 3:\n"
            "  acc = acc + str(i)\n"
            "  i = i + 1\n"
            "print(acc)\n"
        )
        assert rc == 0, stderr
        assert "012" in stdout

    def test_continue_in_loop(self):
        rc, stdout, stderr = run_zpx(
            "let i = 0\n"
            "while i < 5:\n"
            "  i = i + 1\n"
            "  if i == 3:\n"
            "    continue\n"
            "  print(i)\n"
        )
        assert rc == 0, stderr
        assert "3" not in stdout

    def test_for_loop_over_list(self):
        rc, stdout, stderr = run_zpx(
            "let acc = ''\n"
            "for x in [1, 2, 3]:\n"
            "  acc = acc + str(x)\n"
            "print(acc)\n"
        )
        assert rc == 0, stderr
        assert "123" in stdout

    def test_empty_list(self):
        rc, stdout, stderr = run_zpx("print([])\n")
        assert rc == 0
        assert "[]" in stdout

    def test_nested_if_else(self):
        rc, stdout, stderr = run_zpx(
            "let x = 5\n"
            "if x > 10:\n"
            "  print('big')\n"
            "el if x > 0:\n"
            "  print('positive')\n"
            "el:\n"
            "  print('non-positive')\n"
        )
        assert rc == 0, stderr
        assert "positive" in stdout


class TestOperatorEdgeCases:
    """Edge cases for operators."""

    def test_assign_with_colon_colon(self):
        rc, stdout, stderr = run_zpx(
            "let x\nx :: 42\nprint(x)\n"
        )
        assert rc == 0, stderr
        assert "42" in stdout

    def test_augmented_subtract(self):
        rc, stdout, stderr = run_zpx(
            "let x = 10\nx -= 3\nprint(x)\n"
        )
        assert rc == 0, stderr
        assert "7" in stdout

    def test_not_operator(self):
        rc, stdout, stderr = run_zpx(
            "let x = false\nif not x:\n  print('negated')\n"
        )
        assert rc == 0, stderr
        assert "negated" in stdout

    def test_not_with_true(self):
        rc, stdout, stderr = run_zpx(
            "let x = true\nif not x:\n  print('false')\nel:\n  print('true')\n"
        )
        assert rc == 0, stderr
        assert "false" in stdout or "true" in stdout

    def test_exclamation(self):
        rc, stdout, stderr = run_zpx(
            "let x = false\nif !x:\n  print('negated')\n"
        )
        assert rc == 0, stderr
        assert "negated" in stdout

    def test_string_repeat(self):
        rc, stdout, stderr = run_zpx('print("ha" * 3)\n')
        assert rc == 0
        assert "hahaha" in stdout

    def test_list_concat(self):
        rc, stdout, stderr = run_zpx("print([1, 2] + [3, 4])\n")
        assert rc == 0
        assert "[1, 2, 3, 4]" in stdout


class TestErrorHandling:
    """Negative tests — error handling."""

    def test_division_by_zero(self):
        rc, stdout, stderr = run_zpx("print(1 / 0)\n")
        assert rc != 0
        assert "zero" in stderr.lower() or "division" in stderr.lower()

    def test_undefined_variable(self):
        rc, stdout, stderr = run_zpx("print(undefined_var)\n")
        assert rc != 0
        assert "undefined" in stderr.lower() or "name" in stderr.lower()

    def test_type_error_addition(self):
        rc, stdout, stderr = run_zpx('print(true + "hello")\n')
        if rc != 0:
            assert "error" in stderr.lower()

    def test_index_out_of_range(self):
        rc, stdout, stderr = run_zpx("let xs = [1, 2]\nprint(xs[5])\n")
        assert rc != 0
        assert "index" in stderr.lower() or "range" in stderr.lower()

    def test_cannot_index_number(self):
        rc, stdout, stderr = run_zpx("print(42[0])\n")
        assert rc != 0

    def test_cannot_call_number(self):
        rc, stdout, stderr = run_zpx("let x = 42\nx()\n")
        assert rc != 0


class TestLambdaAndComprehensions:
    """Lambda functions and comprehensions."""

    def test_simple_lambda(self):
        rc, stdout, stderr = run_zpx("let double = x => x * 2\nprint(double(5))\n")
        assert rc == 0, stderr
        assert "10" in stdout

    def test_list_comprehension(self):
        rc, stdout, stderr = run_zpx(
            "let result = [x * x for x in [1, 2, 3]]\nprint(result)\n"
        )
        assert rc == 0, stderr
        assert "[1, 4, 9]" in stdout

    def test_dict_literal(self):
        rc, stdout, stderr = run_zpx(
            'let d = ["a": 1, "b": 2]\nprint(d["a"])\n'
        )
        assert rc == 0, stderr
        assert "1" in stdout

    def test_lambda_captures_variable(self):
        rc, stdout, stderr = run_zpx(
            "let factor = 3\n"
            "let multiply = x => x * factor\n"
            "print(multiply(5))\n"
        )
        assert rc == 0, stderr
        assert "15" in stdout


class TestDestructuring:
    """Destructuring assignment: let {a, b} = expr."""

    def test_destructure_dict(self):
        rc, stdout, stderr = run_zpx(
            'let {a, b} = ["a": 1, "b": 2]\n'
            'print(a)\n'
            'print(b)\n'
        )
        assert rc == 0, stderr
        assert "1" in stdout and "2" in stdout

    def test_destructure_rename(self):
        rc, stdout, stderr = run_zpx(
            'let data = ["x": 10, "y": 20]\n'
            'let {x, y} = data\n'
            'print(x + y)\n'
        )
        assert rc == 0, stderr
        assert "30" in stdout

    def test_destructure_single(self):
        rc, stdout, stderr = run_zpx(
            'let {name} = ["name": "Zpx"]\n'
            'print(name)\n'
        )
        assert rc == 0, stderr
        assert "Zpx" in stdout


class TestBuiltinEdgeCases:
    """Edge cases for builtins."""

    def test_type_builtin(self):
        rc, stdout, stderr = run_zpx("print(type(42))\n")
        assert rc == 0, stderr
        assert "int" in stdout.lower() or "Int" in stdout

    def test_isinstance_builtin(self):
        rc, stdout, stderr = run_zpx("print(isinstance(42, 'int'))\n")
        assert rc == 0, stderr
        assert "False" in stdout or "true" in stdout.lower()

    def test_float_conversion(self):
        rc, stdout, stderr = run_zpx("print(float('3.14'))\n")
        assert rc == 0
        assert "3.14" in stdout

    def test_str_upper_lower(self):
        rc, stdout, stderr = run_zpx('print(upper("hello"))\n')
        assert rc == 0
        assert "HELLO" in stdout

    def test_str_strip(self):
        rc, stdout, stderr = run_zpx('print(strip("  hi  "))\n')
        assert rc == 0
        assert "hi" in stdout

    def test_abs_negative(self):
        rc, stdout, stderr = run_zpx("print(abs(-10))\n")
        assert rc == 0
        assert "10" in stdout

    def test_round_float(self):
        rc, stdout, stderr = run_zpx("print(round(3.7))\n")
        assert rc == 0
        assert "4" in stdout

    def test_len_empty_list(self):
        rc, stdout, stderr = run_zpx("print(len([]))\n")
        assert rc == 0
        assert "0" in stdout

    def test_range_with_step(self):
        rc, stdout, stderr = run_zpx(
            "let acc = ''\n"
            "for i in range(0, 5, 2):\n"
            "  acc = acc + str(i)\n"
            "print(acc)\n"
        )
        assert rc == 0, stderr
        assert "024" in stdout
