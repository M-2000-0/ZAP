import os

import pytest


@pytest.fixture
def tmp_cwd(tmp_path, monkeypatch):
    """Create a temporary working directory for CLI tests."""
    monkeypatch.chdir(tmp_path)
    return str(tmp_path)
