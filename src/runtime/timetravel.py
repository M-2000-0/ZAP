"""
Time-Travel Debugging Runtime for ZAP.

Provides:
- checkpoint()  -> snapshot_id
- rewind(snapshot_id)  -> restores full evaluator state
- query(snapshot_id, path) -> inspect any past value
- timeline() -> list of all snapshots with metadata
"""

import copy
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from collections import deque

from src.environment import Environment
from src.values import ZapType, ZapList, ZapDict, ZapFunction, ZapBuiltin, ZapPromise


@dataclass
class FrameSnapshot:
    """Single stack frame at a point in time."""
    func_name: str
    line: int
    col: int
    locals: Dict[str, Any]
    source_snippet: str = ""


@dataclass
class Snapshot:
    """Complete evaluator state at a moment in time."""
    id: str
    timestamp: float
    label: str
    globals: Dict[str, Any]
    call_stack: List[FrameSnapshot]
    heap_objects: Dict[int, Any]  # id(obj) -> deep copy
    stdin_buffer: str = ""
    stdout_buffer: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class TimeTravelRuntime:
    """
    Drop-in wrapper around Evaluator that adds time-travel debugging.
    
    Usage:
        rt = TimeTravelRuntime(evaluator)
        snap = rt.checkpoint("before payment")
        result = rt.run(fn, args)
        if result.failed:
            rt.rewind(snap)
            rt.query(snap, "order.total")  # inspect past state
    """
    
    def __init__(self, evaluator, max_snapshots: int = 1000):
        self.evaluator = evaluator
        self.max_snapshots = max_snapshots
        self.snapshots: deque = deque(maxlen=max_snapshots)
        self._snapshot_index: Dict[str, Snapshot] = {}
        self._enabled = True
        self._auto_checkpoint_on: set = {"call", "return", "raise", "loop"}
        
    def checkpoint(self, label: str = "") -> str:
        """Capture full evaluator state. Returns snapshot ID."""
        if not self._enabled:
            return ""
        
        snap_id = str(uuid.uuid4())[:8]
        snap = Snapshot(
            id=snap_id,
            timestamp=time.time(),
            label=label or f"checkpoint_{len(self.snapshots)}",
            globals=self._deep_copy_globals(),
            call_stack=self._capture_call_stack(),
            heap_objects=self._capture_heap(),
            stdout_buffer=getattr(self.evaluator, '_stdout_buffer', ""),
        )
        self.snapshots.append(snap)
        self._snapshot_index[snap_id] = snap
        return snap_id
    
    def _deep_copy_globals(self) -> Dict[str, Any]:
        env = self.evaluator.global_env
        result = {}
        for name, val in env.store.items():
            try:
                result[name] = self._deep_copy_value(val)
            except Exception:
                result[name] = f"<unserializable: {type(val).__name__}>"
        return result
    
    def _deep_copy_value(self, val: Any, memo: Optional[Dict] = None) -> Any:
        if memo is None:
            memo = {}
        obj_id = id(val)
        if obj_id in memo:
            return memo[obj_id]
        
        if val is None or isinstance(val, (bool, int, float, str)):
            return val
        if isinstance(val, ZapList):
            copied = ZapList([self._deep_copy_value(v, memo) for v in val.elements])
            memo[obj_id] = copied
            return copied
        if isinstance(val, ZapDict):
            copied = ZapDict({k: self._deep_copy_value(v, memo) for k, v in val.entries.items()})
            memo[obj_id] = copied
            return copied
        if isinstance(val, ZapFunction):
            return val  # functions are immutable-ish
        if isinstance(val, ZapBuiltin):
            return val
        if isinstance(val, ZapPromise):
            return f"<Promise:{id(val)}>"
        if isinstance(val, dict):
            copied = {k: self._deep_copy_value(v, memo) for k, v in val.items()}
            memo[obj_id] = copied
            return copied
        if isinstance(val, list):
            copied = [self._deep_copy_value(v, memo) for v in val]
            memo[obj_id] = copied
            return copied
        if isinstance(val, (set, tuple)):
            return type(val)(self._deep_copy_value(v, memo) for v in val)
        return f"<{type(val).__name__}:{id(val)}>"
    
    def _capture_call_stack(self) -> List[FrameSnapshot]:
        stack = []
        if hasattr(self.evaluator, '_call_stack'):
            for frame in self.evaluator._call_stack:
                stack.append(FrameSnapshot(
                    func_name=getattr(frame, 'func_name', '<unknown>'),
                    line=getattr(frame, 'line', 0),
                    col=getattr(frame, 'col', 0),
                    locals=self._deep_copy_locals(frame),
                    source_snippet=self._get_source_snippet(frame),
                ))
        return stack
    
    def _deep_copy_locals(self, frame) -> Dict[str, Any]:
        if hasattr(frame, 'env') and frame.env:
            return {k: self._deep_copy_value(v) for k, v in frame.env.store.items()}
        return {}
    
    def _get_source_snippet(self, frame) -> str:
        if hasattr(frame, 'source_lines') and frame.source_lines:
            idx = max(0, frame.line - 1)
            return frame.source_lines[idx].strip() if idx < len(frame.source_lines) else ""
        return ""
    
    def _capture_heap(self) -> Dict[int, Any]:
        # Track objects referenced from globals and stack
        seen = set()
        heap = {}
        
        def track(obj):
            oid = id(obj)
            if oid in seen:
                return
            seen.add(oid)
            heap[oid] = self._deep_copy_value(obj)
        
        for val in self.evaluator.global_env.store.values():
            track(val)
        return heap
    
    def rewind(self, snapshot_id: str) -> bool:
        """Restore evaluator to a snapshot. Returns success."""
        snap = self._snapshot_index.get(snapshot_id)
        if not snap:
            return False
        
        # Restore globals
        self.evaluator.global_env.store.clear()
        self.evaluator.global_env.store.update(snap.globals)
        
        # Restore call stack (create new frames)
        self.evaluator._call_stack = []
        for frame_snap in snap.call_stack:
            # Reconstruct minimal frame
            frame = type('Frame', (), {
                'func_name': frame_snap.func_name,
                'line': frame_snap.line,
                'col': frame_snap.col,
                'env': Environment(),
                'source_lines': [frame_snap.source_snippet] if frame_snap.source_snippet else [],
            })()
            for k, v in frame_snap.locals.items():
                frame.env.define(k, v)
            self.evaluator._call_stack.append(frame)
        
        if hasattr(self.evaluator, '_stdout_buffer'):
            self.evaluator._stdout_buffer = snap.stdout_buffer
        
        return True
    
    def query(self, snapshot_id: str, path: str) -> Any:
        """Query a value from a snapshot using dot notation: 'order.user.name'"""
        snap = self._snapshot_index.get(snapshot_id)
        if not snap:
            return None
        
        # Start from globals or call stack locals
        ctx = {**snap.globals}
        if snap.call_stack:
            ctx.update(snap.call_stack[-1].locals)
        
        parts = path.split('.')
        val = ctx.get(parts[0])
        if val is None:
            # Search in call stack
            for frame in reversed(snap.call_stack):
                if parts[0] in frame.locals:
                    val = frame.locals[parts[0]]
                    break
        
        if val is None:
            return None
        
        for part in parts[1:]:
            if isinstance(val, (dict, ZapDict)):
                val = val.get(part) if hasattr(val, 'get') else val.get(part)
            elif isinstance(val, (list, ZapList)):
                try:
                    val = val[int(part)]
                except (ValueError, IndexError):
                    return None
            elif hasattr(val, part):
                val = getattr(val, part)
            else:
                return None
            if val is None:
                return None
        return val
    
    def timeline(self, limit: int = 50) -> List[Dict]:
        """Return recent snapshots with metadata."""
        return [
            {
                "id": s.id,
                "label": s.label,
                "time": s.timestamp,
                "stack_depth": len(s.call_stack),
                "globals_count": len(s.globals),
            }
            for s in list(self.snapshots)[-limit:]
        ]
    
    def diff(self, snap_a: str, snap_b: str) -> Dict:
        """Compare two snapshots."""
        a = self._snapshot_index.get(snap_a)
        b = self._snapshot_index.get(snap_b)
        if not a or not b:
            return {}
        
        def flatten(d, prefix=""):
            result = {}
            for k, v in d.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (dict, ZapDict)):
                    result.update(flatten(v if isinstance(v, dict) else v.entries, key))
                elif isinstance(v, (list, ZapList)):
                    for i, item in enumerate(v):
                        result[f"{key}[{i}]"] = item
                else:
                    result[key] = v
            return result
        
        flat_a = flatten(a.globals)
        flat_b = flatten(b.globals)
        
        all_keys = set(flat_a) | set(flat_b)
        changes = {}
        for k in all_keys:
            va = flat_a.get(k)
            vb = flat_b.get(k)
            if va != vb:
                changes[k] = {"before": va, "after": vb}
        return changes
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False


# Monkey-patch Evaluator to add time-travel methods
def _patch_evaluator_for_timetravel(evaluator, runtime: TimeTravelRuntime):
    """Add time-travel methods and auto-checkpoint to evaluator."""
    
    original_call = evaluator._eval_call
    
    def wrapped_call(expr):
        if runtime._enabled and "call" in runtime._auto_checkpoint_on:
            runtime.checkpoint(f"call")
        return original_call(expr)
    
    evaluator._eval_call = wrapped_call
    
    # Add helper methods to evaluator
    evaluator.checkpoint = runtime.checkpoint
    evaluator.rewind = runtime.rewind
    evaluator.query = runtime.query
    evaluator.timeline = runtime.timeline
    evaluator.diff = runtime.diff


def make_timetravel_runtime(evaluator, max_snapshots=1000) -> TimeTravelRuntime:
    """Factory: wrap an evaluator with time-travel."""
    runtime = TimeTravelRuntime(evaluator, max_snapshots)
    _patch_evaluator_for_timetravel(evaluator, runtime)
    return runtime