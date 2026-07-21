import time
import threading
from collections import defaultdict, deque

EVENT_TYPES = (
    'call_start', 'call_end', 'assign', 'lookup',
    'eval_expr', 'eval_stmt', 'builtin', 'error',
    'retry', 'fallback', 'distributed_start', 'distributed_end',
    'contract_check',
)

class TraceEvent:
    __slots__ = ('type', 'ts', 'thread_id', 'scope', 'payload')

    def __init__(self, type_, scope='', payload=None):
        assert type_ in EVENT_TYPES, f"Unknown trace event type: {type_}"
        self.type = type_
        self.ts = time.time()
        self.thread_id = threading.current_thread().name
        self.scope = scope
        self.payload = payload or {}

    def to_dict(self):
        return {
            'type': self.type,
            'ts': self.ts,
            'thread_id': self.thread_id,
            'scope': self.scope,
            'payload': self.payload,
        }


class Tracer:
    def __init__(self, max_events=10000):
        self._events = deque(maxlen=max_events)
        self._lock = threading.Lock()
        self._enabled = True

    @property
    def enabled(self):
        return self._enabled

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def clear(self):
        with self._lock:
            self._events.clear()

    def emit(self, type_, scope='', payload=None):
        if not self._enabled:
            return
        event = TraceEvent(type_, scope, payload)
        with self._lock:
            self._events.append(event)

    def events(self, type_=None, limit=100, offset=0):
        with self._lock:
            all_events = list(self._events)
        if type_:
            all_events = [e for e in all_events if e.type == type_]
        return [e.to_dict() for e in all_events[offset:offset + limit]]

    def query(self, type_=None, scope_contains=None, min_duration=None, limit=50):
        result = []
        with self._lock:
            events = list(self._events)
        for e in events:
            if type_ and e.type != type_:
                continue
            if scope_contains and scope_contains not in e.scope:
                continue
            entry = e.to_dict()
            if min_duration is not None and 'duration' in e.payload:
                if e.payload['duration'] < min_duration:
                    continue
            result.append(entry)
            if len(result) >= limit:
                break
        return result

    def slow_calls(self, threshold=0.1, limit=20):
        return self.query(type_='call_end', min_duration=threshold, limit=limit)

    def errors(self, limit=20):
        return self.query(type_='error', limit=limit)

    def stats(self):
        counts = defaultdict(int)
        with self._lock:
            for e in self._events:
                counts[e.type] += 1
        return dict(counts)

    def to_dict(self):
        return {
            'total_events': len(self._events),
            'stats': self.stats(),
        }


# Global tracer instance
_global_tracer = Tracer()

def get_tracer():
    return _global_tracer

def trace(type_, scope='', payload=None):
    _global_tracer.emit(type_, scope, payload)
