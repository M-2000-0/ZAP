"""Differential self-hosting tests.

Runs a small corpus of Zpx programs through BOTH the host interpreter
(`python -m src run`) and the Zpx-written self-hosted interpreter
(`self_host/self_host_interpreter.zpx`) and asserts their stdout matches.
"""

import importlib.util
import os
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELF_HOST_INTERP = os.path.join(HERE, "self_host", "self_host_interpreter.zpx")

_HARNESS = os.path.join(HERE, "test_self_hosting.py")
_spec = importlib.util.spec_from_file_location("zpx_self_hosting_harness", _HARNESS)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
CORPUS = _module.CORPUS


def run_zpx(py_args):
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


def _run_source(source, name, interp):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, name + ".zpx")
        with open(path, "w", encoding="utf-8") as f:
            f.write(source)
        if interp == "host":
            return run_zpx(["run", path])
        return run_zpx(["run", SELF_HOST_INTERP, path])


@pytest.mark.parametrize("name,source", CORPUS)
def test_self_host_matches_host(name, source):
    rc_h, out_h, _ = _run_source(source, name, "host")
    rc_s, out_s, err_s = _run_source(source, name, "selfhost")
    assert rc_s == rc_h, f"self-host rc={rc_s} (host rc={rc_h}): {err_s[-500:]}"
    assert out_s == out_h, f"output mismatch for '{name}':\n  host: {out_h!r}\n  self: {out_s!r}"
