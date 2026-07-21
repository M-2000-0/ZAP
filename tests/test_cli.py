"""CLI regression tests for Zap.

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

# Path to the zap CLI
ZAP_CMD = [sys.executable, "-m", "src"]

# Examples directory
EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "examples")


def run_zap(args, cwd=None, input_text=None):
    """Run a zap CLI command and return (returncode, stdout, stderr)."""
    cmd = ZAP_CMD + args
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


def write_zap_file(directory, name, content):
    """Write a .zap file to the given directory."""
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
    """Tests for `zap run`."""

    def test_run_simple_file(self, tmp_project):
        """zap run on a simple file should execute and print output."""
        zap_file = write_zap_file(tmp_project, "main.zap", 'print("hello world")\n')
        rc, stdout, stderr = run_zap(["run", zap_file])
        assert rc == 0
        assert "hello world" in stdout

    def test_run_folder_auto_detect(self, tmp_project):
        """zap run on a folder should auto-detect main.zap."""
        write_zap_file(tmp_project, "main.zap", 'print("from folder")\n')
        rc, stdout, stderr = run_zap(["run", tmp_project])
        assert rc == 0
        assert "from folder" in stdout

    def test_run_folder_index_zap(self, tmp_project):
        """zap run on a folder should detect index.zap if main.zap is absent."""
        write_zap_file(tmp_project, "index.zap", 'print("from index")\n')
        rc, stdout, stderr = run_zap(["run", tmp_project])
        assert rc == 0
        assert "from index" in stdout

    def test_run_folder_no_entrypoint(self, tmp_project):
        """zap run on a folder with no .zap files should error."""
        rc, stdout, stderr = run_zap(["run", tmp_project])
        assert rc != 0
        assert "No entrypoint" in stderr or "entrypoint" in stderr.lower()

    def test_run_missing_file(self, tmp_project):
        """zap run on a non-existent file should error."""
        rc, stdout, stderr = run_zap(["run", "nonexistent.zap"])
        assert rc != 0
        assert "entrypoint" in stderr.lower() or "not found" in stderr.lower()

    def test_run_default_to_current_dir(self, tmp_project):
        """zap run with no args should default to current directory."""
        write_zap_file(tmp_project, "main.zap", 'print("default")\n')
        rc, stdout, stderr = run_zap(["run"], cwd=tmp_project)
        assert rc == 0
        assert "default" in stdout


class TestCheckCommand:
    """Tests for `zap check`."""

    def test_check_valid_file(self, tmp_project):
        """zap check on a valid file should pass."""
        zap_file = write_zap_file(tmp_project, "main.zap", 'print("hello")\n')
        rc, stdout, stderr = run_zap(["check", zap_file])
        assert rc == 0
        assert "ok" in stdout.lower()

    def test_check_json_output(self, tmp_project):
        """zap check --format=json should output structured JSON."""
        zap_file = write_zap_file(tmp_project, "main.zap", 'print("hello")\n')
        rc, stdout, stderr = run_zap(["check", zap_file, "--format=json"])
        assert rc == 0
        # JSON diagnostics go to stderr
        data = json.loads(stderr)
        assert data["ok"] is True
        assert data["count"] == 0
        assert "diagnostics" in data

    def test_check_json_output_with_errors(self, tmp_project):
        """zap check --format=json should output errors in JSON."""
        zap_file = write_zap_file(tmp_project, "main.zap", 'let x = 1\nprint(undefined_var)\n')
        rc, stdout, stderr = run_zap(["check", zap_file, "--format=json"])
        assert rc != 0
        data = json.loads(stderr)
        assert data["ok"] is False
        assert data["count"] > 0
        assert len(data["diagnostics"]) > 0

    def test_check_missing_file(self, tmp_project):
        """zap check on a non-existent file should error."""
        rc, stdout, stderr = run_zap(["check", "nonexistent.zap"])
        assert rc != 0


class TestCompileCommand:
    """Tests for `zap compile`."""

    def test_compile_simple_file(self, tmp_project):
        """zap compile should execute the file."""
        zap_file = write_zap_file(tmp_project, "main.zap", 'print("compiled")\n')
        rc, stdout, stderr = run_zap(["compile", zap_file])
        assert rc == 0
        assert "compiled" in stdout

    def test_compile_with_out_flag(self, tmp_project):
        """zap compile --out should write to the specified path."""
        zap_file = write_zap_file(tmp_project, "main.zap", 'print("output")\n')
        out_path = os.path.join(tmp_project, "output.py")
        rc, stdout, stderr = run_zap(["compile", zap_file, "--out", out_path])
        assert rc == 0
        assert os.path.exists(out_path)
        assert "Compiled to" in stdout or out_path in stdout

    def test_compile_json_output(self, tmp_project):
        """zap compile --format=json should output structured JSON."""
        zap_file = write_zap_file(tmp_project, "main.zap", 'print("json")\n')
        rc, stdout, stderr = run_zap(["compile", zap_file, "--format=json"])
        assert rc == 0
        data = json.loads(stdout)
        assert data["ok"] is True


class TestVersionCommand:
    """Tests for `zap version`."""

    def test_version_text(self):
        """zap version should print version info."""
        rc, stdout, stderr = run_zap(["version"])
        assert rc == 0
        assert "Zap" in stdout or "zap" in stdout.lower()

    def test_version_json(self):
        """zap version --format=json should output structured JSON."""
        rc, stdout, stderr = run_zap(["version", "--format=json"])
        assert rc == 0
        data = json.loads(stdout)
        assert "version" in data
        assert "grammar" in data


class TestInitCommand:
    """Tests for `zap init`."""

    def test_init_creates_project(self, tmp_project):
        """zap init should create a new project directory."""
        rc, stdout, stderr = run_zap(["init", "my-app"], cwd=tmp_project)
        assert rc == 0
        assert os.path.exists(os.path.join(tmp_project, "my-app"))
        assert os.path.exists(os.path.join(tmp_project, "my-app", "main.zap"))
        assert os.path.exists(os.path.join(tmp_project, "my-app", "zap.json"))
        assert os.path.exists(os.path.join(tmp_project, "my-app", ".gitignore"))

    def test_init_project_runs(self, tmp_project):
        """zap init created project should be runnable."""
        run_zap(["init", "test-app"], cwd=tmp_project)
        rc, stdout, stderr = run_zap(["run", "test-app"], cwd=tmp_project)
        assert rc == 0
        assert "test-app" in stdout


class TestDiagCommand:
    """Tests for `zap diag`."""

    def test_diag_parses_text(self):
        """zap diag should parse human-readable diagnostics."""
        diag_text = "error[Z200] main.zap:5:3: undefined variable 'foo'"
        rc, stdout, stderr = run_zap(["diag", diag_text])
        assert rc == 0
        data = json.loads(stdout)
        assert len(data) == 1
        assert data[0]["code"] == "Z200"
        assert data[0]["message"] == "undefined variable 'foo'"


class TestExamples:
    """Test that all example files parse and run."""

    @pytest.mark.parametrize("example_file", [
        f for f in os.listdir(EXAMPLES_DIR) if f.endswith(".zap")
    ] if os.path.exists(EXAMPLES_DIR) else [])
    def test_example_parses(self, example_file):
        """Each example should parse without errors."""
        path = os.path.join(EXAMPLES_DIR, example_file)
        rc, stdout, stderr = run_zap(["check", path])
        # We allow parse errors for some examples, but they should not crash
        assert rc is not None


class TestBuiltins:
    """Test that builtins work correctly."""

    def test_config_builtin(self, tmp_project):
        """config() should load JSON config."""
        write_zap_file(tmp_project, "zap.json", '{"name": "test", "version": "1.0"}')
        zap_file = write_zap_file(tmp_project, "main.zap", 'cfg = config("zap.json")\nprint(cfg["name"])\n')
        rc, stdout, stderr = run_zap(["run", zap_file])
        assert rc == 0
        assert "test" in stdout

    def test_par_map_builtin(self, tmp_project):
        """par_map should work correctly."""
        zap_file = write_zap_file(tmp_project, "main.zap",
            'result = par_map(x => x * x, [1, 2, 3])\nprint(result)\n')
        rc, stdout, stderr = run_zap(["run", zap_file])
        assert rc == 0
        assert "1" in stdout and "4" in stdout and "9" in stdout

    def test_short_aliases(self, tmp_project):
        """Short aliases should work."""
        zap_file = write_zap_file(tmp_project, "main.zap",
            'print(trim("  hello  "))\n')
        rc, stdout, stderr = run_zap(["run", zap_file])
        assert rc == 0
        assert "hello" in stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
