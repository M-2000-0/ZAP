import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.values import make_zap_builtins


def test_builtin_max_accepts_multiple_args():
    env = make_zap_builtins()
    max_fn = env.store["max"]
    result = max_fn.fn(3, 7)
    assert result == 7


def test_builtin_min_accepts_multiple_args():
    env = make_zap_builtins()
    min_fn = env.store["min"]
    result = min_fn.fn(3, 7)
    assert result == 3


def test_builtin_max_accepts_single_collection():
    env = make_zap_builtins()
    max_fn = env.store["max"]
    result = max_fn.fn([1, 4, 2])
    assert result == 4


def test_builtin_min_accepts_single_collection():
    env = make_zap_builtins()
    min_fn = env.store["min"]
    result = min_fn.fn([1, 4, 2])
    assert result == 1
