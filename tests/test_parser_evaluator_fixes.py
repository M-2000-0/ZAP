"""Tests for parser and evaluator fixes from the ZPX host review."""
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def run_zpx(code: str, timeout: int = 10) -> str:
    """Run Zpx code via CLI and capture stdout."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".zpx", delete=False) as f:
        f.write(textwrap.dedent(code))
        f.flush()
        tmp_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "run", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        return result.stdout.strip()
    finally:
        os.unlink(tmp_path)


def run_zpx_raw(code: str, timeout: int = 10):
    """Run Zpx code and return (returncode, stdout, stderr)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".zpx", delete=False) as f:
        f.write(textwrap.dedent(code))
        f.flush()
        tmp_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "run", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    finally:
        os.unlink(tmp_path)


class TestElIfChaining:
    """Test that 'el' accepts optional colon before 'if'."""

    def test_el_if_without_colon(self):
        code = """
        let x = 0
        if x > 10:
          print("big")
        el if x > 0:
          print("pos")
        el:
          print("zero")
        """
        assert run_zpx(code) == "zero"

    def test_el_if_with_optional_colon(self):
        code = """
        let x = 5
        if x > 10:
          print("big")
        el: if x > 0:
          print("pos")
        el:
          print("zero")
        """
        assert run_zpx(code) == "pos"

    def test_el_else_with_optional_colon(self):
        code = """
        let x = 0
        if x > 5:
          print("big")
        el:
          print("small")
        """
        assert run_zpx(code) == "small"


class TestKeywordAsFunctionName:
    """Test that keywords can be used as function names."""

    def test_keyword_fn_name_match(self):
        code = """
        fn match(items):
          ret "found " + str(len(items))
        print(match([1, 2, 3]))
        """
        assert run_zpx(code) == "found 3"

    def test_keyword_fn_name_type(self):
        code = """
        fn type(x):
          ret str(x)
        print(type(42))
        """
        assert run_zpx(code) == "42"

    def test_keyword_fn_name_test(self):
        code = """
        fn test():
          ret "testing"
        print(test())
        """
        assert run_zpx(code) == "testing"

    def test_keyword_method_name_match(self):
        code = """
        class Finder:
          fn match(self, s):
            ret "matching: " + str(s)

        let f = Finder()
        print(f.match("hello"))
        """
        assert run_zpx(code) == "matching: hello"


class TestKeywordArguments:
    """Test keyword arguments in function calls."""

    def test_kwarg_in_function_call(self):
        code = """
        fn greet(name, greeting="Hello"):
          ret greeting + ", " + name
        print(greet(name="World"))
        """
        assert run_zpx(code) == "Hello, World"

    def test_kwarg_with_explicit_value(self):
        code = """
        fn greet(name, greeting="Hello"):
          ret greeting + ", " + name
        print(greet(name="World", greeting="Hey"))
        """
        assert run_zpx(code) == "Hey, World"

    def test_kwarg_reorder(self):
        code = """
        fn add(a, b):
          ret a + b
        print(add(b=3, a=5))
        """
        assert run_zpx(code) == "8"

    def test_mixed_args_and_kwargs(self):
        code = """
        fn configure(mode, timeout=30):
          ret mode + ":" + str(timeout)
        print(configure("fast", timeout=10))
        """
        assert run_zpx(code) == "fast:10"

    def test_kwarg_keyword_param_name(self):
        code = """
        fn test(type="default", value=0):
          ret type + ":" + str(value)
        print(test())
        """
        assert run_zpx(code) == "default:0"

    def test_kwarg_only_call(self):
        code = """
        fn multi(a, b, c):
          ret a + b + c
        print(multi(c=3, a=1, b=2))
        """
        assert run_zpx(code) == "6"


class TestMemberAccessKeywordNames:
    """Test that keywords work after dot in member access."""

    def test_member_access_keyword_method(self):
        code = """
        let lst = [1, 2, 3]
        lst.append(4)
        print(lst)
        """
        assert run_zpx(code) == "[1, 2, 3, 4]"

    def test_member_access_type_attribute(self):
        code = """
        class Container:
          fn init(self):
            self.type = "box"

        let c = Container()
        print(c.type)
        """
        assert run_zpx(code) == "box"


class TestImportAliases:
    """Test import with 'as' aliases."""

    def test_module_alias_import(self):
        tmpdir = tempfile.mkdtemp()
        try:
            # Create module file
            module_path = os.path.join(tmpdir, "mylib.zpx")
            with open(module_path, 'w') as f:
                f.write("fn helper():\n  ret 42\n")

            # Create main file that imports with alias
            main_path = os.path.join(tmpdir, "main.zpx")
            with open(main_path, 'w') as f:
                f.write('import mylib as mymod\nprint(mymod.helper())\n')

            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..") + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [sys.executable, "-m", "src.cli", "run", main_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir,
                env=env,
            )
            assert "42" in result.stdout, result.stderr
        finally:
            shutil.rmtree(tmpdir)

    def test_from_import_with_alias(self):
        tmpdir = tempfile.mkdtemp()
        try:
            # Create module file
            module_path = os.path.join(tmpdir, "mylib.zpx")
            with open(module_path, 'w') as f:
                f.write("fn my_func():\n  ret 100\n")

            # Create main file that imports with alias
            main_path = os.path.join(tmpdir, "main.zpx")
            with open(main_path, 'w') as f:
                f.write('from mylib import my_func as aliased\nprint(aliased())\n')

            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..") + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [sys.executable, "-m", "src.cli", "run", main_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir,
                env=env,
            )
            assert "100" in result.stdout, result.stderr
        finally:
            shutil.rmtree(tmpdir)


class TestDottedImports:
    """Test dotted module path imports."""

    def test_dotted_module_path(self):
        tmpdir = tempfile.mkdtemp()
        try:
            # Create nested directory structure
            mod_dir = os.path.join(tmpdir, "testmod", "sub")
            os.makedirs(mod_dir, exist_ok=True)

            # Create module file
            module_path = os.path.join(mod_dir, "dotted.zpx")
            with open(module_path, 'w') as f:
                f.write("fn dotted_test():\n  ret 55\n")

            # Create main file that imports with dotted path
            main_path = os.path.join(tmpdir, "main.zpx")
            with open(main_path, 'w') as f:
                f.write('import testmod.sub.dotted as tm\nprint(tm.dotted_test())\n')

            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..") + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [sys.executable, "-m", "src.cli", "run", main_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir,
                env=env,
            )
            assert "55" in result.stdout, result.stderr
        finally:
            shutil.rmtree(tmpdir)


class TestMatchStatement:
    """Test match statement with proper DEDENT handling."""

    def test_basic_match(self):
        code = """
        let x = 2
        match x:
          1:
            print("one")
          2:
            print("two")
          3:
            print("three")
        """
        assert run_zpx(code) == "two"

    def test_match_with_default(self):
        code = """
        let x = 99
        match x:
          1:
            print("one")
          2:
            print("two")
          el:
            print("default")
        """
        assert run_zpx(code) == "default"

    def test_match_nested(self):
        code = """
        let x = 1
        let y = 2
        match x:
          1:
            match y:
              1:
                print("1,1")
              2:
                print("1,2")
          el:
            print("other")
        """
        assert run_zpx(code) == "1,2"


class TestNullGuard:
    """Test that null/empty guard doesn't crash parser."""

    def test_empty_call(self):
        rc, stdout, stderr = run_zpx_raw("print()")
        assert rc == 0

    def test_function_call_with_no_args(self):
        code = """
        fn noargs():
          ret 0
        print(noargs())
        """
        assert run_zpx(code) == "0"


class TestKeywordAsIdentifier:
    """Test that keywords work in various identifier contexts."""

    def test_keyword_as_dict_key(self):
        code = """
        let d = ["type": "value"]
        print(d["type"])
        """
        assert run_zpx(code) == "value"

    def test_keyword_as_let_var(self):
        code = """
        let type = 42
        print(type)
        """
        assert run_zpx(code) == "42"

    def test_keyword_as_service_name(self):
        code = """
        service api:
          fn init(self):
            self.endpoint = "test"

        let s = api()
        print(s.endpoint)
        """
        assert run_zpx(code) == "test"


class TestInOperator:
    """Tests for the 'in' and 'not in' membership operators."""

    def test_in_list(self):
        code = """
        let x = 2
        print(x in [1, 2, 3])
        """
        assert run_zpx(code) == "True"

    def test_not_in_list(self):
        code = """
        let x = 5
        print(x not in [1, 2, 3])
        """
        assert run_zpx(code) == "True"

    def test_in_string(self):
        code = """
        let s = "hello"
        print("ell" in s)
        """
        assert run_zpx(code) == "True"

    def test_in_dict(self):
        code = """
        let d = {'a': 1, 'b': 2}
        print('a' in d)
        """
        assert run_zpx(code) == "True"

    def test_in_dict_values(self):
        code = """
        let d = {'a': 1, 'b': 2}
        print(1 not in d)
        """
        assert run_zpx(code) == "True"

    def test_in_with_for(self):
        code = """
        for x in [1, 2, 3]:
            if x in [1, 2, 3]:
                continue
        print("ok")
        """
        assert run_zpx(code) == "ok"


class TestTernaryOperator:
    """Tests for ternary operator: expr if cond else expr2."""

    def test_ternary_true(self):
        code = """
        let x = 1 if true else 2
        print(x)
        """
        assert run_zpx(code) == "1"

    def test_ternary_false(self):
        code = """
        let x = 1 if false else 2
        print(x)
        """
        assert run_zpx(code) == "2"

    def test_ternary_complex_condition(self):
        code = """
        let x = "yes" if 5 > 3 else "no"
        print(x)
        """
        assert run_zpx(code) == "yes"

    def test_nested_ternary(self):
        code = """
        let x = 1 if true else (2 if false else 3)
        print(x)
        """
        assert run_zpx(code) == "1"

    def test_ternary_in_function(self):
        code = """
        fn sign(n):
            ret "pos" if n > 0 else "neg"

        print(sign(5))
        print(sign(-3))
        """
        assert run_zpx(code) == "pos\nneg"


class TestDictMethods:
    """Tests for dict iteration methods."""

    def test_dict_keys(self):
        code = """
        let d = {'a': 1, 'b': 2}
        print(d.keys())
        """
        assert run_zpx(code) == "[a, b]"

    def test_dict_values(self):
        code = """
        let d = {'a': 1, 'b': 2}
        print(d.values())
        """
        assert run_zpx(code) == "[1, 2]"

    def test_dict_items(self):
        code = """
        let d = {'a': 1, 'b': 2}
        print(d.items())
        """
        assert run_zpx(code) == "[[a, 1], [b, 2]]"

    def test_dict_len(self):
        code = """
        let d = {'a': 1, 'b': 2, 'c': 3}
        print(d.len())
        """
        assert run_zpx(code) == "3"

    def test_dict_iteration(self):
        code = """
        let d = {'a': 1, 'b': 2}
        let sum = 0
        for k in d.keys():
            sum = sum + d[k]
        print(sum)
        """
        assert run_zpx(code) == "3"


class TestFString:
    """Tests for f-string interpolation: f"...{expr}..."""

    def test_basic_fstring(self):
        code = """
        let name = "world"
        print(f"hello {name}")
        """
        assert run_zpx(code) == "hello world"

    def test_fstring_multiple_interp(self):
        code = """
        let a = 1
        let b = 2
        print(f"{a} + {b} = {a + b}")
        """
        assert run_zpx(code) == "1 + 2 = 3"

    def test_fstring_no_interp(self):
        code = """
        print(f"hello world")
        """
        assert run_zpx(code) == "hello world"

    def test_fstring_expression(self):
        code = """
        let x = 5
        print(f"x is {x} and x*2 is {x * 2}")
        """
        assert run_zpx(code) == "x is 5 and x*2 is 10"

    def test_fstring_with_method_call(self):
        code = """
        let s = "hello"
        print(f"{s.upper()}")
        """
        assert run_zpx(code) == "HELLO"
