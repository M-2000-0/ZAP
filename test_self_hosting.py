#!/usr/bin/env python3
"""Test script to verify the self-hosted Zap interpreter."""

import sys
import os
import subprocess

import pytest


def run_zap_file(filepath, args=None):
    """Run a Zap file using the Zap CLI."""
    zap_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = [sys.executable, "-m", "src", "run", filepath]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=zap_dir)
    return result


def test_basic_self_hosting():
    """Test basic self-hosted functionality."""
    # Test hello.zap
    result = run_zap_file("self_host/hello.zap")
    assert result.returncode == 0, f"hello.zap failed: {result.stderr}"

    # Test tokens.zap
    result = run_zap_file("self_host/tokens.zap")
    assert result.returncode == 0, f"tokens.zap failed: {result.stderr}"

    # Test self_host_interpreter.zap
    result = run_zap_file("self_host/self_host_interpreter.zap")
    assert result.returncode == 0, f"self_host_interpreter.zap failed: {result.stderr}"


def test_enhanced_features():
    """Test enhanced features like comprehensions, interpolation."""
    # Test comprehensions.zap
    result = run_zap_file("examples/comprehensions.zap")
    assert result.returncode == 0, f"comprehensions.zap failed: {result.stderr}"

    # Test interp.zap
    result = run_zap_file("examples/interp.zap")
    assert result.returncode == 0, f"interp.zap failed: {result.stderr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
