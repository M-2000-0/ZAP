"""Self-hosting differential test harness for Zpx.

Runs a small corpus of Zpx programs through BOTH the host interpreter
(`python -m src run`) and the Zpx-written self-hosted interpreter
(`self_host/self_host_interpreter.zpx`) and compares their stdout.

Usage:
    python test_self_hosting.py
    python test_self_hosting.py --verbose
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SELF_HOST_INTERP = os.path.join(HERE, "self_host", "self_host_interpreter.zpx")

# Corpus of small programs both interpreters should agree on.
# Each entry: (name, source).
CORPUS = [
    ("hello", 'let name = "Zpx"\nlet v = 42\nprint("Hello from self-hosted Zpx!")\nprint("Name: $name")\nprint("Version: $v")\n'),
    ("arithmetic", 'print(1 + 2)\nprint(10 - 3)\nprint(6 * 7)\nprint(20 / 4)\nprint(2 ** 10)\nprint(17 % 5)\n'),
    ("comparison", 'print(1 < 2)\nprint(2 <= 2)\nprint(3 > 4)\nprint(4 >= 4)\nprint(1 == 1)\nprint(1 != 2)\nprint("a" < "b")\n'),
    ("let_expr", 'let x = 5\nlet y = x * 2\nlet z = y + 1\nprint(z)\nprint(x + y + z)\n'),
    ("fn_call", 'fn add(a, b):\n  ret a + b\nfn mul(a, b):\n  ret a * b\nprint(add(3, 7))\nprint(mul(add(1, 2), 4))\n'),
    ("fn_recursive", 'fn fib(n):\n  if n < 2:\n    ret n\n  ret fib(n - 1) + fib(n - 2)\nprint(fib(10))\n'),
    ("if_else", 'let x = 10\nif x > 5:\n  print("big")\nel:\n  print("small")\nlet y = 3\nif y > 5:\n  print("big")\nel:\n  print("small")\n'),
    ("for_loop", 'let sum = 0\nfor i in range(5):\n  sum = sum + i\nprint(sum)\n'),
    ("while_loop", 'let i = 0\nlet total = 0\nwhile i < 5:\n  total = total + i\n  i = i + 1\nprint(total)\n'),
    ("list_index", 'let nums = [1, 2, 3, 4, 5]\nprint(nums[0])\nprint(nums[4])\nprint(len(nums))\n'),
    ("list_loop", 'let nums = [1, 2, 3]\nlet total = 0\nfor n in nums:\n  total = total + n\nprint(total)\n'),
    ("dict_get", 'let person = {"name": "Ada", "age": 36}\nprint(person["name"])\nprint(person["age"])\n'),
    ("string_concat", 'let a = "foo"\nlet b = "bar"\nprint(a + b)\nprint(a + "!")\n'),
    ("interp_expr", 'let a = 3\nlet b = 4\nprint("sum is ${a + b}")\nprint("$a and $b")\n'),
    ("nested_fn", 'fn outer(x):\n  fn inner(y):\n    ret y * 2\n  ret inner(x) + 1\nprint(outer(10))\n'),
    ("string_methods", 'let s = "Hello, World"\nprint(len(s))\nprint(s.upper())\nprint(s.lower())\n'),
    ("modulo_neg", 'print(-7 % 3)\nprint(7 % -3)\n'),
]


def run_interp(py_args):
    """Run the host interpreter and return stdout."""
    env = os.environ.copy()
    env["PYTHONPATH"] = HERE + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "src"] + py_args,
        capture_output=True,
        text=True,
        cwd=HERE,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def run_host(source, name):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, name + ".zpx")
        with open(path, "w", encoding="utf-8") as f:
            f.write(source)
        return run_interp(["run", path])


def run_selfhost(source, name):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, name + ".zpx")
        with open(path, "w", encoding="utf-8") as f:
            f.write(source)
        return run_interp(["run", SELF_HOST_INTERP, path])


def main():
    verbose = "--verbose" in sys.argv
    passed = 0
    failed = []

    for name, source in CORPUS:
        rc_h, out_h, err_h = run_host(source, name)
        rc_s, out_s, err_s = run_selfhost(source, name)
        if verbose:
            print(f"\n=== {name} ===")
            print(f"  host:      rc={rc_h} out={out_h!r} err={err_h[-200:]!r}")
            print(f"  self-host: rc={rc_s} out={out_s!r} err={err_s[-200:]!r}")

        if rc_h != 0 and rc_s == 0:
            print(f"FAIL {name}: host errored (rc={rc_h}) but self-host succeeded")
            failed.append(name)
            continue
        if rc_h == 0 and rc_s != 0:
            print(f"FAIL {name}: self-host errored (rc={rc_s}): {err_s.strip()[-300:]}")
            failed.append(name)
            continue
        if out_h != out_s:
            print(f"FAIL {name}: output mismatch\n  host:      {out_h!r}\n  self-host: {out_s!r}")
            failed.append(name)
            continue
        passed += 1
        if verbose:
            print(f"  PASS {name}")

    print(f"\n{passed}/{len(CORPUS)} self-hosting corpus tests passed")
    if failed:
        print("Failed:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
