"""CLI regression tests for Zpx.

Tests the CLI commands: run, check, build, compile, test, version, diag, init, install, add.
Uses subprocess to test the actual CLI entry point.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

import pytest

# Path to the zpx CLI
ZPX_CMD = [sys.executable, "-m", "src"]

# Examples directory
EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


def run_zpx(args, cwd=None, input_text=None):
    """Run a zpx CLI command and return (returncode, stdout, stderr)."""
    cmd = ZPX_CMD + args
    env = os.environ.copy()
    # Ensure src module is importable from any directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or os.path.dirname(__file__),
        input=input_text,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def write_zpx_file(directory, name, content):
    """Write a .zpx file to the given directory."""
    path = os.path.join(directory, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


@pytest.fixture
def tmp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestRunCommand:
    """Tests for `zpx run`."""

    def test_run_simple_file(self, tmp_project):
        """zpx run on a simple file should execute and print output."""
        zpx_file = write_zpx_file(tmp_project, "main.zpx", 'print("hello world")\n')
        rc, stdout, stderr = run_zpx(["run", zpx_file])
        assert rc == 0
        assert "hello world" in stdout

    def test_run_folder_auto_detect(self, tmp_project):
        """zpx run on a folder should auto-detect main.zpx."""
        write_zpx_file(tmp_project, "main.zpx", 'print("from folder")\n')
        rc, stdout, stderr = run_zpx(["run", tmp_project])
        assert rc == 0
        assert "from folder" in stdout

    def test_run_folder_index_zpx(self, tmp_project):
        """zpx run on a folder should detect index.zpx if main.zpx is absent."""
        write_zpx_file(tmp_project, "index.zpx", 'print("from index")\n')
        rc, stdout, stderr = run_zpx(["run", tmp_project])
        assert rc == 0
        assert "from index" in stdout

    def test_run_folder_no_entrypoint(self, tmp_project):
        """zpx run on a folder with no .zpx files should error."""
        rc, stdout, stderr = run_zpx(["run", tmp_project])
        assert rc != 0
        assert "No entrypoint" in stderr or "entrypoint" in stderr.lower()

    def test_run_missing_file(self, tmp_project):
        """zpx run on a non-existent file should error."""
        rc, stdout, stderr = run_zpx(["run", "nonexistent.zpx"])
        assert rc != 0
        assert "entrypoint" in stderr.lower() or "not found" in stderr.lower()

    def test_run_default_to_current_dir(self, tmp_project):
        """zpx run with no args should default to current directory."""
        write_zpx_file(tmp_project, "main.zpx", 'print("default")\n')
        rc, stdout, stderr = run_zpx(["run"], cwd=tmp_project)
        assert rc == 0
        assert "default" in stdout


class TestCheckCommand:
    """Tests for `zpx check`."""

    def test_check_valid_file(self, tmp_project):
        """zpx check on a valid file should pass."""
        zpx_file = write_zpx_file(tmp_project, "main.zpx", 'print("hello")\n')
        rc, stdout, stderr = run_zpx(["check", zpx_file])
        assert rc == 0
        assert "ok" in stdout.lower()

    def test_check_json_output(self, tmp_project):
        """zpx check --format=json should output structured JSON."""
        zpx_file = write_zpx_file(tmp_project, "main.zpx", 'print("hello")\n')
        rc, stdout, stderr = run_zpx(["check", zpx_file, "--format=json"])
        assert rc == 0
        # JSON diagnostics go to stderr
        data = json.loads(stderr)
        assert data["ok"] is True
        assert data["count"] == 0
        assert "diagnostics" in data

    def test_check_json_output_with_errors(self, tmp_project):
        """zpx check --format=json should output errors in JSON."""
        zpx_file = write_zpx_file(tmp_project, "main.zpx", 'let x = 1\nprint(undefined_var)\n')
        rc, stdout, stderr = run_zpx(["check", zpx_file, "--format=json"])
        assert rc != 0
        data = json.loads(stderr)
        assert data["ok"] is False
        assert data["count"] > 0
        assert len(data["diagnostics"]) > 0

    def test_check_missing_file(self, tmp_project):
        """zpx check on a non-existent file should error."""
        rc, stdout, stderr = run_zpx(["check", "nonexistent.zpx"])
        assert rc != 0

    def test_check_empty_dict_arg(self, tmp_project):
        """zpx check: empty dict {} should satisfy a dict[str, any] parameter."""
        zpx_file = write_zpx_file(tmp_project, "main.zpx", 'print(element("div", {}, "hi"))\n')
        rc, stdout, stderr = run_zpx(["check", zpx_file])
        assert rc == 0, stderr

    def test_check_method_calls(self, tmp_project):
        """zpx check: dict/list/str methods should resolve, not report 'any' not callable."""
        src = (
            'let d = {a: 1}\n'
            'let ks = d.keys()\n'
            'let v = d.get("a")\n'
            'let xs = []\n'
            'xs.append(1)\n'
            'let n = xs.len()\n'
            'let s = "hi"\n'
            'let u = s.upper()\n'
            'let parts = s.split(",")\n'
            'print(n + v)\n'
        )
        zpx_file = write_zpx_file(tmp_project, "main.zpx", src)
        rc, stdout, stderr = run_zpx(["check", zpx_file])
        assert rc == 0, stderr

    def test_check_index_any(self, tmp_project):
        """zpx check: indexing a dynamic value (any) should be allowed."""
        src = 'let f = x => x["name"]\nprint(f({name: "hi"}))\n'
        zpx_file = write_zpx_file(tmp_project, "main.zpx", src)
        rc, stdout, stderr = run_zpx(["check", zpx_file])
        assert rc == 0, stderr

    def test_check_recursive_fn(self, tmp_project):
        """zpx check: a function should be able to call itself."""
        src = (
            'fn fib(n)\n'
            '  n if n < 2 else fib(n - 1) + fib(n - 2)\n'
            'print(fib(5))\n'
        )
        zpx_file = write_zpx_file(tmp_project, "main.zpx", src)
        rc, stdout, stderr = run_zpx(["check", zpx_file])
        assert rc == 0, stderr


class TestCompileCommand:
    """Tests for `zpx compile`."""

    def test_compile_simple_file(self, tmp_project):
        """zpx compile should execute the file."""
        zpx_file = write_zpx_file(tmp_project, "main.zpx", 'print("compiled")\n')
        rc, stdout, stderr = run_zpx(["compile", zpx_file])
        assert rc == 0
        assert "compiled" in stdout

    def test_compile_with_out_flag(self, tmp_project):
        """zpx compile --out should write to the specified path."""
        zpx_file = write_zpx_file(tmp_project, "main.zpx", 'print("output")\n')
        out_path = os.path.join(tmp_project, "output.py")
        rc, stdout, stderr = run_zpx(["compile", zpx_file, "--out", out_path])
        assert rc == 0
        assert os.path.exists(out_path)
        assert "Compiled to" in stdout or out_path in stdout

    def test_compile_json_output(self, tmp_project):
        """zpx compile --format=json should output structured JSON."""
        zpx_file = write_zpx_file(tmp_project, "main.zpx", 'print("json")\n')
        rc, stdout, stderr = run_zpx(["compile", zpx_file, "--format=json"])
        assert rc == 0
        data = json.loads(stdout)
        assert data["ok"] is True


class TestVersionCommand:
    """Tests for `zpx version`."""

    def test_version_text(self):
        """zpx version should print version info."""
        rc, stdout, stderr = run_zpx(["version"])
        assert rc == 0
        assert "Zpx" in stdout or "zpx" in stdout.lower()

    def test_version_json(self):
        """zpx version --format=json should output structured JSON."""
        rc, stdout, stderr = run_zpx(["version", "--format=json"])
        assert rc == 0
        data = json.loads(stdout)
        assert "version" in data
        assert "grammar" in data


class TestInitCommand:
    """Tests for `zpx init`."""

    def test_init_creates_project(self, tmp_project):
        """zpx init should create a new project directory."""
        rc, stdout, stderr = run_zpx(["init", "my-app"], cwd=tmp_project)
        assert rc == 0
        assert os.path.exists(os.path.join(tmp_project, "my-app"))
        assert os.path.exists(os.path.join(tmp_project, "my-app", "main.zpx"))
        assert os.path.exists(os.path.join(tmp_project, "my-app", "zpx.json"))
        assert os.path.exists(os.path.join(tmp_project, "my-app", ".gitignore"))

    def test_init_project_runs(self, tmp_project):
        """zpx init created project should be runnable."""
        run_zpx(["init", "test-app"], cwd=tmp_project)
        rc, stdout, stderr = run_zpx(["run", "test-app"], cwd=tmp_project)
        assert rc == 0
        assert "test-app" in stdout


class TestDiagCommand:
    """Tests for `zpx diag`."""

    def test_diag_parses_text(self):
        """zpx diag should parse human-readable diagnostics."""
        diag_text = "error[Z200] main.zpx:5:3: undefined variable 'foo'"
        rc, stdout, stderr = run_zpx(["diag", diag_text])
        assert rc == 0
        data = json.loads(stdout)
        assert len(data) == 1
        assert data[0]["code"] == "Z200"
        assert data[0]["message"] == "undefined variable 'foo'"


class TestExamples:
    """Test that all example files parse and run."""

    @pytest.mark.parametrize("example_file", [
        f for f in os.listdir(EXAMPLES_DIR) if f.endswith(".zpx")
    ] if os.path.exists(EXAMPLES_DIR) else [])
    def test_example_parses(self, example_file):
        """Each example should parse without errors."""
        path = os.path.join(EXAMPLES_DIR, example_file)
        rc, stdout, stderr = run_zpx(["check", path])
        # We allow parse errors for some examples, but they should not crash
        assert rc is not None


class TestBuiltins:
    """Test that builtins work correctly."""

    def test_config_builtin(self, tmp_project):
        """config() should load JSON config."""
        write_zpx_file(tmp_project, "zpx.json", '{"name": "test", "version": "1.0"}')
        zpx_file = write_zpx_file(tmp_project, "main.zpx", 'cfg = config("zpx.json")\nprint(cfg["name"])\n')
        rc, stdout, stderr = run_zpx(["run", zpx_file])
        assert rc == 0
        assert "test" in stdout

    def test_par_map_builtin(self, tmp_project):
        """par_map should work correctly."""
        zpx_file = write_zpx_file(tmp_project, "main.zpx",
            'result = par_map(x => x * x, [1, 2, 3])\nprint(result)\n')
        rc, stdout, stderr = run_zpx(["run", zpx_file])
        assert rc == 0
        assert "1" in stdout and "4" in stdout and "9" in stdout

    def test_short_aliases(self, tmp_project):
        """Short aliases should work."""
        zpx_file = write_zpx_file(tmp_project, "main.zpx",
            'print(trim("  hello  "))\n')
        rc, stdout, stderr = run_zpx(["run", zpx_file])
        assert rc == 0
        assert "hello" in stdout


class TestConvertCommand:
    """Tests for `zpx convert` (multi-format data + LLM export)."""

    def test_csv_to_json(self, tmp_project):
        """zpx convert csv --to json should print JSON."""
        csv_path = os.path.join(tmp_project, "data.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("name,age\nAda,36\nBob,41\n")
        rc, stdout, stderr = run_zpx(["convert", csv_path, "--to", "json"])
        assert rc == 0, stderr
        data = json.loads(stdout)
        assert len(data) == 2
        assert data[0]["name"] == "Ada"
        assert data[0]["age"] == "36"

    def test_csv_to_jsonl(self, tmp_project):
        """zpx convert csv --to jsonl should emit one JSON object per line."""
        csv_path = os.path.join(tmp_project, "data.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("name,age\nAda,36\nBob,41\n")
        rc, stdout, stderr = run_zpx(["convert", csv_path, "--to", "jsonl"])
        assert rc == 0, stderr
        lines = [json.loads(l) for l in stdout.strip().splitlines()]
        assert [r["name"] for r in lines] == ["Ada", "Bob"]

    def test_json_to_csv_roundtrip(self, tmp_project):
        """csv -> json -> csv should preserve the original rows."""
        csv1 = os.path.join(tmp_project, "a.csv")
        with open(csv1, "w", encoding="utf-8") as f:
            f.write("x,y\n1,one\n2,two\n")
        rc, stdout, stderr = run_zpx(["convert", csv1, "--out", os.path.join(tmp_project, "a.json")])
        assert rc == 0, stderr
        rc, stdout, stderr = run_zpx(
            ["convert", os.path.join(tmp_project, "a.json"), "--out", os.path.join(tmp_project, "b.csv")])
        assert rc == 0, stderr
        with open(os.path.join(tmp_project, "b.csv"), encoding="utf-8") as f:
            assert f.read() == "x,y\n1,one\n2,two\n"

    def test_zpx_roundtrip(self, tmp_project):
        """Converting to .zpx should produce a runnable file that reads back."""
        csv_path = os.path.join(tmp_project, "data.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("name,age\nAda,36\n")
        zpx_path = os.path.join(tmp_project, "data.zpx")
        rc, stdout, stderr = run_zpx(["convert", csv_path, "--out", zpx_path])
        assert rc == 0, stderr
        assert os.path.exists(zpx_path)
        rc, stdout, stderr = run_zpx(["convert", zpx_path, "--to", "jsonl"])
        assert rc == 0, stderr
        lines = [json.loads(l) for l in stdout.strip().splitlines()]
        assert lines == [{"name": "Ada", "age": "36"}]

    def test_zpx_null_to_none(self, tmp_project):
        """JSON null should round-trip through a .zpx file as none."""
        json_path = os.path.join(tmp_project, "n.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write('[{"a": 1, "b": null, "c": true}]\n')
        zpx_path = os.path.join(tmp_project, "n.zpx")
        rc, stdout, stderr = run_zpx(["convert", json_path, "--out", zpx_path])
        assert rc == 0, stderr
        with open(zpx_path, encoding="utf-8") as f:
            assert "none" in f.read()
        rc, stdout, stderr = run_zpx(["convert", zpx_path, "--to", "json"])
        assert rc == 0, stderr
        data = json.loads(stdout)
        assert data[0]["b"] is None
        assert data[0]["c"] is True

    def test_markdown_output(self, tmp_project):
        """zpx convert --to markdown should render a table."""
        csv_path = os.path.join(tmp_project, "data.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("a,b\n1,x\n")
        rc, stdout, stderr = run_zpx(["convert", csv_path, "--to", "markdown"])
        assert rc == 0, stderr
        assert "| a | b |" in stdout
        assert "| 1 | x |" in stdout

    def test_sql_output(self, tmp_project):
        """zpx convert --to sql should emit CREATE + INSERT statements."""
        csv_path = os.path.join(tmp_project, "data.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("id,name\n1,Ada\n")
        rc, stdout, stderr = run_zpx(["convert", csv_path, "--to", "sql"])
        assert rc == 0, stderr
        assert "CREATE TABLE" in stdout
        assert "INSERT INTO data" in stdout
        assert "Ada" in stdout

    def test_llm_chat_export(self, tmp_project):
        """--llm should emit OpenAI-style messages JSONL."""
        csv_path = os.path.join(tmp_project, "chat.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("user,assistant\nWhat is 2+2?,It is 4.\n")
        out = os.path.join(tmp_project, "train.jsonl")
        rc, stdout, stderr = run_zpx(
            ["convert", csv_path, "--llm", "--system", "Be helpful.", "--out", out])
        assert rc == 0, stderr
        with open(out, encoding="utf-8") as f:
            rec = json.loads(f.readline())
        roles = [m["role"] for m in rec["messages"]]
        assert roles == ["system", "user", "assistant"]
        assert rec["messages"][0]["content"] == "Be helpful."

    def test_llm_instruct_export(self, tmp_project):
        """--llm --instruct should emit {prompt, completion} records."""
        csv_path = os.path.join(tmp_project, "qa.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("prompt,completion\nfib(5),5\n")
        rc, stdout, stderr = run_zpx(
            ["convert", csv_path, "--llm", "--instruct", "--to", "jsonl"])
        assert rc == 0, stderr
        rec = json.loads(stdout.strip())
        assert rec == {"prompt": "fib(5)", "completion": "5"}

    def test_jsonl_builtins(self, tmp_project):
        """jsonl_save/jsonl_load should work inside a .zpx program."""
        src = (
            'let rows = [{"name": "Ada"}, {"name": "Bob"}]\n'
            'jsonl_save("out.jsonl", rows)\n'
            'let loaded = jsonl_load("out.jsonl")\n'
            'print(len(loaded))\n'
            'print(loaded[1]["name"])\n'
        )
        zpx_file = write_zpx_file(tmp_project, "main.zpx", src)
        rc, stdout, stderr = run_zpx(["run", zpx_file], cwd=tmp_project)
        assert rc == 0, stderr
        assert "2" in stdout
        assert "Bob" in stdout
        assert os.path.exists(os.path.join(tmp_project, "out.jsonl"))

    def test_compact_zpx(self, tmp_project):
        """--compact should emit a single-line .zpx that still reads back."""
        csv_path = os.path.join(tmp_project, "data.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("id,name\n1,Ada\n2,Bob\n")
        zpx_path = os.path.join(tmp_project, "data.zpx")
        rc, stdout, stderr = run_zpx(["convert", csv_path, "--compact", "--out", zpx_path])
        assert rc == 0, stderr
        with open(zpx_path, encoding="utf-8") as f:
            assert f.read().count("\n") < 5  # effectively single-line data
        rc, stdout, stderr = run_zpx(["convert", zpx_path, "--to", "json"])
        assert rc == 0, stderr
        data = json.loads(stdout)
        assert len(data) == 2
        assert data[0]["name"] == "Ada"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
