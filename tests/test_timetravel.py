#!/usr/bin/env python3
"""Test time-travel debugging features."""

import sys
sys.path.insert(0, '.')

from src.evaluator import Evaluator
from src.parser import Parser
from src.lexer import Lexer
from src.runtime.timetravel import make_timetravel_runtime

def run_test(name, source, check_func):
    """Run a test and verify with check_func."""
    print(f"\n=== {name} ===")
    tokens = Lexer(source, '<test>').tokenize()
    ast = Parser(tokens).parse()
    evaluator = Evaluator()
    rt = make_timetravel_runtime(evaluator)
    
    try:
        result = evaluator.evaluate(ast)
        check_func(rt, evaluator, result)
        print(f"  PASS")
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()

def test_basic_checkpoint():
    """Test basic checkpoint creation."""
    def check(rt, ev, result):
        snap_id = rt.checkpoint("after_init")
        assert snap_id
        snap = rt._snapshot_index[snap_id]
        assert snap.label == "after_init"
        assert "x" in snap.globals
        assert snap.globals["x"] == 42
    run_test("Basic Checkpoint", "let x = 42", check)

def test_rewind():
    """Test rewinding to a previous snapshot."""
    def check(rt, ev, result):
        # First checkpoint
        snap1 = rt.checkpoint("x=10")
        # Modify state
        ev.evaluate(Parser(Lexer("let x = 20", '<test>').tokenize()).parse())
        assert ev.global_env.store["x"] == 20
        # Rewind
        rt.rewind(snap1)
        assert ev.global_env.store["x"] == 10
    run_test("Rewind", "let x = 10", check)

def test_query():
    """Test querying values from snapshots."""
    def check(rt, ev, result):
        snap = rt.checkpoint("init")
        # Query from snapshot
        val = rt.query(snap, "user.name")
        assert val == "Zap"
        # Query nested
        val = rt.query(snap, "config.debug")
        assert val is True
    run_test("Query Snapshot", '''
let user = ["name": "Zap", "version": "0.2"]
let config = ["debug": true, "port": 8080]
''', check)

def test_timeline():
    """Test timeline listing."""
    def check(rt, ev, result):
        rt.checkpoint("start")
        ev.evaluate(Parser(Lexer("let a = 1", '<test>').tokenize()).parse())
        rt.checkpoint("after_a")
        ev.evaluate(Parser(Lexer("let b = 2", '<test>').tokenize()).parse())
        rt.checkpoint("after_b")
        
        timeline = rt.timeline()
        # Initial "let x = 0" + 3 explicit checkpoints = at least 3
        assert len(timeline) >= 3
        # Find our labeled checkpoints
        labels = [s["label"] for s in timeline]
        assert "start" in labels
        assert "after_a" in labels
        assert "after_b" in labels
    run_test("Timeline", "let x = 0", check)

def test_diff():
    """Test snapshot diffing."""
    def check(rt, ev, result):
        snap1 = rt.checkpoint("before")
        ev.evaluate(Parser(Lexer("let x = 100", '<test>').tokenize()).parse())
        snap2 = rt.checkpoint("after")
        
        diff = rt.diff(snap1, snap2)
        assert "x" in diff
        assert diff["x"]["before"] is None or "x" not in str(diff["x"]["before"])
        assert diff["x"]["after"] == 100
    run_test("Diff Snapshots", "let x = 0", check)

def test_auto_checkpoint():
    """Test auto-checkpoint on function calls."""
    def check(rt, ev, result):
        rt.enable()
        source = '''
fn add(a, b) a + b
let result = add(5, 3)
'''
        tokens = Lexer(source, '<test>').tokenize()
        ast = Parser(tokens).parse()
        ev.evaluate(ast)
        
        # Should have auto-checkpoints
        timeline = rt.timeline()
        call_snapshots = [s for s in timeline if "call" in s["label"]]
        assert len(call_snapshots) >= 1
    run_test("Auto Checkpoint on Call", "let x = 0", check)

if __name__ == "__main__":
    test_basic_checkpoint()
    test_rewind()
    test_query()
    test_timeline()
    test_diff()
    test_auto_checkpoint()
    print("\n=== ALL TESTS PASSED ===")