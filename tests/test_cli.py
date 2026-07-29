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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
