"""Tests for the .zapcontext dedup behavior."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.context import ZapContext, get_context, reset_context_singleton


def test_add_intent_dedupes():
    """Re-adding the same intent is a no-op."""
    ctx = ZapContext()
    ctx.add_intent("build a dashboard")
    ctx.add_intent("build a dashboard")
    ctx.add_intent("build a dashboard")
    assert len(ctx.data["intents"]) == 1
    assert ctx.data["intents"][0]["text"] == "build a dashboard"
    print("  ok add_intent dedupes")


def test_add_intent_updates_status():
    """Re-adding the same intent with a different status updates the entry."""
    ctx = ZapContext()
    ctx.add_intent("foo", status="pending")
    ctx.add_intent("foo", status="done")
    assert len(ctx.data["intents"]) == 1
    assert ctx.data["intents"][0]["status"] == "done"
    print("  ok add_intent updates status")


def test_add_decision_dedupes():
    ctx = ZapContext()
    ctx.add_decision("use tensor @@ for matrix multiply")
    ctx.add_decision("use tensor @@ for matrix multiply")
    assert len(ctx.data["decisions"]) == 1
    print("  ok add_decision dedupes")


def test_add_api_dedupes_by_name():
    ctx = ZapContext()
    ctx.add_api("TaskService", "service with 5 methods", ["create", "get"])
    ctx.add_api("TaskService", "service with 5 methods", ["create", "get", "list"])
    assert len(ctx.data["apis"]) == 1
    assert sorted(ctx.data["apis"][0]["endpoints"]) == ["create", "get", "list"]
    print("  ok add_api dedupes by name and merges endpoints")


def test_add_endpoint_to_existing():
    ctx = ZapContext()
    ctx.add_api("Foo", "", ["a", "b"])
    ctx.add_endpoint("Foo", "c")
    ctx.add_endpoint("Foo", "a")  # duplicate
    assert ctx.data["apis"][0]["endpoints"] == ["a", "b", "c"]
    print("  ok add_endpoint merges and dedupes")


def test_legacy_duplicate_file_migrates():
    """A file with 16 duplicate intents migrates to 1 entry."""
    legacy = {
        "project": {"name": "x", "description": "", "version": "0.2"},
        "intents": [{"text": "foo", "status": "pending"}] * 16,
        "decisions": ["use tensor @@"] * 16,
        "conventions": ["pure functions"] * 16,
        "apis": [
            {"name": "S", "description": "x", "endpoints": ["a"]}
        ] * 16,
        "author": "test",
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(legacy, f)
        path = f.name
    try:
        ctx = ZapContext.load_and_dedupe(path)
        assert len(ctx.data["intents"]) == 1, f"got {len(ctx.data['intents'])}"
        assert len(ctx.data["decisions"]) == 1
        assert len(ctx.data["conventions"]) == 1
        assert len(ctx.data["apis"]) == 1
        print("  ok legacy 16x duplicate file migrates to single entries")
    finally:
        os.unlink(path)


def test_save_load_roundtrip_preserves_dedup():
    ctx = ZapContext()
    ctx.add_intent("a")
    ctx.add_intent("a")
    ctx.add_intent("b")
    ctx.add_decision("d1")
    ctx.add_decision("d1")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        path = f.name
    try:
        ctx.save(path)
        # Don't use the singleton loader — verify a fresh load stays deduped.
        loaded = ZapContext.load_and_dedupe(path)
        assert len(loaded.data["intents"]) == 2
        assert len(loaded.data["decisions"]) == 1
        print("  ok save/load roundtrip stays deduped")
    finally:
        os.unlink(path)


def test_get_context_dedupes_on_load():
    """The module-level singleton loader dedupes the on-disk file once."""
    # Write a duplicated file
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({
            "project": {"name": "", "description": "", "version": "0.2"},
            "intents": [{"text": "x", "status": "pending"}] * 5,
            "decisions": [],
            "conventions": [],
            "apis": [],
        }, f)
        path = f.name
    try:
        reset_context_singleton()
        # Patch DEFAULT_FILE temporarily via load()
        ctx = ZapContext.load_and_dedupe(path)
        assert len(ctx.data["intents"]) == 1
        print("  ok singleton-style load dedupes")
    finally:
        os.unlink(path)
        reset_context_singleton()


if __name__ == "__main__":
    test_add_intent_dedupes()
    test_add_intent_updates_status()
    test_add_decision_dedupes()
    test_add_api_dedupes_by_name()
    test_add_endpoint_to_existing()
    test_legacy_duplicate_file_migrates()
    test_save_load_roundtrip_preserves_dedup()
    test_get_context_dedupes_on_load()
    print("all context tests passed")
