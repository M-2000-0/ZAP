"""Integration tests: run Zpx code through the host evaluator and verify output."""
import os
import sys
import subprocess
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


class TestArithmetic:
    def test_basic_math(self):
        assert run_zpx("print(2 + 3)") == "5"

    def test_precedence(self):
        assert run_zpx("print(2 + 3 * 4)") == "14"

    def test_power(self):
        assert run_zpx("print(2 ** 10)") == "1024"

    def test_modulo(self):
        assert run_zpx("print(17 % 5)") == "2"

    def test_negative(self):
        assert run_zpx("print(-5 + 3)") == "-2"


class TestVariables:
    def test_let_and_print(self):
        code = """
        let x = 42
        print(x)
        """
        assert run_zpx(code) == "42"

    def test_augmented_assignment(self):
        code = """
        let x = 10
        x += 5
        print(x)
        """
        assert run_zpx(code) == "15"

    def test_string_variable(self):
        code = """
        let name = "Zpx"
        print("Hello, " + name + "!")
        """
        assert run_zpx(code) == "Hello, Zpx!"


class TestControlFlow:
    def test_if_true(self):
        code = """
        let x = 10
        if x > 5:
          print("big")
        """
        assert run_zpx(code) == "big"

    def test_if_false(self):
        code = """
        let x = 3
        if x > 5:
          print("big")
        el:
          print("small")
        """
        assert run_zpx(code) == "small"

    def test_if_else_if(self):
        code = """
        let x = 0
        if x > 0:
          print("pos")
        el if x < 0:
          print("neg")
        el:
          print("zero")
        """
        assert run_zpx(code) == "zero"

    def test_while_loop(self):
        code = """
        let i = 0
        let sum = 0
        while i < 5:
          sum += i
          i += 1
        print(sum)
        """
        assert run_zpx(code) == "10"

    def test_for_loop(self):
        code = """
        let sum = 0
        for i in range(5):
          sum += i
        print(sum)
        """
        assert run_zpx(code) == "10"

    def test_for_loop_list(self):
        code = """
        let result = ""
        for item in [1, 2, 3]:
          result = result + str(item)
        print(result)
        """
        assert run_zpx(code) == "123"


class TestFunctions:
    def test_simple_function(self):
        code = """
        fn add(a, b):
          ret a + b
        print(add(3, 4))
        """
        assert run_zpx(code) == "7"

    def test_recursive_function(self):
        code = """
        fn factorial(n):
          if n <= 1:
            ret 1
          ret n * factorial(n - 1)
        print(factorial(5))
        """
        assert run_zpx(code) == "120"

    def test_default_params(self):
        code = """
        fn greet(name, greeting="Hello"):
          print(greeting + ", " + name)
        greet("World")
        greet("Alice", "Hey")
        """
        output = run_zpx(code)
        assert "Hello, World" in output
        assert "Hey, Alice" in output

    def test_multi_return(self):
        code = """
        fn divmod(a, b):
          ret [a / b, a % b]
        let result = divmod(17, 5)
        print(result[0])
        print(result[1])
        """
        output = run_zpx(code)
        assert "3" in output
        assert "2" in output


class TestClasses:
    def test_basic_class(self):
        code = """
        class Point:
          fn init(self, x, y):
            self.x = x
            self.y = y

          fn distance(self):
            ret sqrt(self.x * self.x + self.y * self.y)

        let p = Point(3, 4)
        print(p.distance())
        """
        assert run_zpx(code) == "5.0"

    def test_class_inheritance(self):
        code = """
        class Animal:
          fn init(self, name):
            self.name = name

          fn speak(self):
            ret self.name + " says ..."

        class Dog(Animal):
          fn speak(self):
            ret self.name + " says Woof"

        let d = Dog("Rex")
        print(d.speak())
        """
        assert run_zpx(code) == "Rex says Woof"

    def test_class_methods(self):
        code = """
        class Counter:
          fn init(self):
            self.value = 0

          fn increment(self):
            self.value += 1

          fn get(self):
            ret self.value

        let c = Counter()
        c.increment()
        c.increment()
        c.increment()
        print(c.get())
        """
        assert run_zpx(code) == "3"


class TestBuiltinFunctions:
    def test_len_string(self):
        assert run_zpx('print(len("hello"))') == "5"

    def test_len_list(self):
        assert run_zpx("print(len([1, 2, 3, 4, 5]))") == "5"

    def test_str_conversion(self):
        assert run_zpx("print(str(42))") == "42"

    def test_int_conversion(self):
        assert run_zpx('print(int("42"))') == "42"

    def test_abs(self):
        assert run_zpx("print(abs(-5))") == "5"

    def test_sqrt(self):
        assert run_zpx("print(sqrt(9))") == "3.0"

    def test_max(self):
        assert run_zpx("print(max(3, 7))") == "7"

    def test_min(self):
        assert run_zpx("print(min(3, 7))") == "3"

    def test_sum(self):
        assert run_zpx("print(sum([1, 2, 3, 4]))") == "10"

    def test_range(self):
        assert run_zpx("print(range(5))") == "[0, 1, 2, 3, 4]"


class TestListOperations:
    def test_list_literal(self):
        assert run_zpx("print([1, 2, 3])") == "[1, 2, 3]"

    def test_list_index(self):
        code = """
        let lst = [10, 20, 30]
        print(lst[1])
        """
        assert run_zpx(code) == "20"

    def test_list_append(self):
        code = """
        let lst = [1, 2]
        lst.append(3)
        print(lst)
        """
        assert run_zpx(code) == "[1, 2, 3]"

    def test_list_concat(self):
        assert run_zpx("print([1, 2] + [3, 4])") == "[1, 2, 3, 4]"


class TestDictOperations:
    def test_dict_literal(self):
        assert run_zpx('print(["a": 1])') == "{a: 1}"

    def test_dict_access(self):
        code = """
        let d = ["key": "value"]
        print(d["key"])
        """
        assert run_zpx(code) == "value"

    def test_dict_missing_key(self):
        code = """
        let d = ["a": 1]
        print(d["b"])
        """
        assert run_zpx(code) == "None"

    def test_dict_set(self):
        code = """
        let d = ["a": 1]
        d["b"] = 2
        print(d["b"])
        """
        assert run_zpx(code) == "2"


class TestStringOperations:
    def test_string_concat(self):
        assert run_zpx('print("a" + "b" + "c")') == "abc"

    def test_string_index(self):
        assert run_zpx('print("hello"[0])') == "h"

    def test_string_slice(self):
        assert run_zpx('print("hello"[1:4])') == "ell"

    def test_string_len(self):
        assert run_zpx('print(len("hello"))') == "5"


class TestBooleanLogic:
    def test_and(self):
        code = """
        let a = true
        let b = false
        print(a and b)
        """
        assert run_zpx(code) == "False"

    def test_or(self):
        code = """
        let a = true
        let b = false
        print(a or b)
        """
        assert run_zpx(code) == "True"

    def test_not(self):
        assert run_zpx("print(not true)") == "False"

    def test_comparison(self):
        assert run_zpx("print(5 > 3)") == "True"
        assert run_zpx("print(5 < 3)") == "False"
        assert run_zpx("print(5 == 5)") == "True"
        assert run_zpx("print(5 != 5)") == "False"


class TestNestedStructures:
    def test_nested_loops(self):
        code = """
        let result = ""
        for i in range(3):
          for j in range(3):
            if i == j:
              result = result + "X"
            el:
              result = result + "O"
          result = result + "\\n"
        print(result)
        """
        output = run_zpx(code)
        assert "XOO" in output
        assert "OXO" in output
        assert "OOX" in output

    def test_nested_function_calls(self):
        code = """
        fn double(x):
          ret x * 2

        fn apply_twice(func, x):
          ret func(func(x))

        print(apply_twice(double, 3))
        """
        assert run_zpx(code) == "12"


class TestFibonacci:
    def test_fibonacci(self):
        code = """
        fn fib(n):
          if n <= 1:
            ret n
          let a = 0
          let b = 1
          let i = 2
          while i <= n:
            let temp = a + b
            a = b
            b = temp
            i += 1
          ret b
        print(fib(0))
        print(fib(1))
        print(fib(10))
        """
        output = run_zpx(code)
        lines = output.split("\n")
        assert lines[0] == "0"
        assert lines[1] == "1"
        assert lines[2] == "55"
