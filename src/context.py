"""
.zapcontext — structured project context shared between the interpreter
and AI agents.

The file is JSON. Top-level shape:

  {
    "project": { "name": str, "description": str, "version": str },
    "intents":   [ { "text": str, "status": "pending" | "done" | "wontfix" } ],
    "decisions": [ str, ... ],
    "conventions": [ str, ... ],
    "apis":      [ { "name": str, "description": str, "endpoints": [str, ...] } ],
    "schemas":   [ { "name": str, "fields": [ { "name": str, "type": str } ] } ],
    "services":  [ { "name": str, "version": str, "expose": [str] } ],
    "author": str
  }

The previous implementation appended without dedup, which is how the
sample .zapcontext ended up with the same intent 16 times. The current
implementation treats each list as a set keyed on the natural identity of
the entry (text for intents/decisions/conventions, name for apis/schemas/
services). Re-adding an existing entry is a no-op; updating an entry
overwrites it.
"""

import json
import os

DEFAULT_FILE = '.zapcontext'


class ZapContext:
    def __init__(self):
        self.data = {
            'project': {'name': '', 'description': '', 'version': '0.2'},
            'intents': [],
            'decisions': [],
            'conventions': [],
            'apis': [],
            'schemas': [],
            'services': [],
        }

    @classmethod
    def load(cls, path=None):
        path = path or DEFAULT_FILE
        ctx = cls()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    loaded = json.load(f)
                # Be tolerant: merge in any missing top-level keys, drop
                # unknown ones. The context file may have been written by
                # an older or newer version of Zap.
                if isinstance(loaded, dict):
                    for k, v in loaded.items():
                        if k in ctx.data:
                            ctx.data[k] = v
            except (json.JSONDecodeError, IOError):
                pass
        return ctx

    def save(self, path=None):
        path = path or DEFAULT_FILE
        try:
            with open(path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError:
            pass

    def set(self, key, value):
        parts = key.split('.')
        d = self.data
        for p in parts[:-1]:
            if p not in d or not isinstance(d[p], dict):
                d[p] = {}
            d = d[p]
        d[parts[-1]] = value

    def get(self, key, default=None):
        parts = key.split('.')
        d = self.data
        for p in parts:
            if isinstance(d, dict) and p in d:
                d = d[p]
            else:
                return default
        return d

    # ── intents ────────────────────────────────────────────────────────

    def add_intent(self, intent, *, status='pending'):
        """Idempotent: re-adding the same intent text is a no-op unless the
        status changes, in which case the entry is updated."""
        for entry in self.data.setdefault('intents', []):
            if entry.get('text') == intent:
                entry['status'] = status
                return
        self.data['intents'].append({'text': intent, 'status': status})

    def mark_intent(self, intent, status):
        self.add_intent(intent, status=status)

    # ── decisions / conventions (string lists, deduped by value) ───────

    def add_decision(self, decision):
        self._deduped_append('decisions', decision)

    def add_convention(self, convention):
        self._deduped_append('conventions', convention)

    # ── apis (deduped by name) ─────────────────────────────────────────

    def add_api(self, name, description='', endpoints=None):
        self._deduped_replace(
            'apis', name,
            {'name': name, 'description': description,
             'endpoints': list(endpoints or [])},
        )

    def add_endpoint(self, api_name, endpoint):
        """Add an endpoint to an existing service, or create the service."""
        for entry in self.data.setdefault('apis', []):
            if entry.get('name') == api_name:
                eps = entry.setdefault('endpoints', [])
                if endpoint not in eps:
                    eps.append(endpoint)
                return
        self.data['apis'].append({
            'name': api_name,
            'description': '',
            'endpoints': [endpoint],
        })

    # ── schemas / services (deduped by name) ───────────────────────────

    def add_schema(self, name, fields):
        self._deduped_replace(
            'schemas', name,
            {'name': name, 'fields': list(fields or [])},
        )

    def add_service(self, name, *, version=None, expose=None):
        existing = None
        for entry in self.data.setdefault('services', []):
            if entry.get('name') == name:
                existing = entry
                break
        if existing is None:
            existing = {'name': name, 'version': version, 'expose': list(expose or [])}
            self.data['services'].append(existing)
        else:
            if version is not None:
                existing['version'] = version
            for e in expose or []:
                if e not in existing['expose']:
                    existing['expose'].append(e)

    # ── dedup helpers ──────────────────────────────────────────────────

    def _deduped_append(self, key, value):
        if value not in self.data.setdefault(key, []):
            self.data[key].append(value)

    def _deduped_replace(self, key, name, entry):
        for i, existing in enumerate(self.data.setdefault(key, [])):
            if existing.get('name') == name:
                self.data[key][i] = entry
                return
        self.data[key].append(entry)

    # ── migration helper ───────────────────────────────────────────────

    def dedupe(self):
        """Run all the dedup rules over whatever is already on disk. Safe
        to call repeatedly. Used by the fix-zapcontext command and once
        at the start of any save to clean up legacy duplicated files."""
        self.data['intents'] = _dedupe_by(
            self.data.get('intents', []),
            key=lambda e: e.get('text') if isinstance(e, dict) else str(e),
            merge=lambda prev, curr: {**prev, **curr},
        )
        self.data['decisions'] = list(dict.fromkeys(self.data.get('decisions', [])))
        self.data['conventions'] = list(dict.fromkeys(self.data.get('conventions', [])))
        self.data['apis'] = _dedupe_by(
            self.data.get('apis', []),
            key=lambda e: e.get('name'),
            merge=lambda prev, curr: {**prev, **curr},
        )
        self.data['schemas'] = _dedupe_by(
            self.data.get('schemas', []),
            key=lambda e: e.get('name'),
            merge=lambda prev, curr: {**prev, **curr},
        )
        self.data['services'] = _dedupe_by(
            self.data.get('services', []),
            key=lambda e: e.get('name'),
            merge=lambda prev, curr: {**prev, **curr},
        )

    @classmethod
    def load_and_dedupe(cls, path=None):
        """Convenience for one-shot migration of a legacy file."""
        ctx = cls.load(path)
        ctx.dedupe()
        return ctx


def _dedupe_by(items, *, key, merge):
    """Dedupe a list of dicts by `key(item)`, merging duplicates with `merge`."""
    seen: dict = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        k = key(item)
        if k in seen:
            seen[k] = merge(seen[k], item)
        else:
            seen[k] = item
    return list(seen.values())


# ── module-level singleton (lazy) ─────────────────────────────────────


_context_instance = None


def get_context():
    global _context_instance
    if _context_instance is None:
        _context_instance = ZapContext.load()
        # One-time dedup in case the file on disk is from a buggy
        # version. After this, in-memory operations stay deduped.
        _context_instance.dedupe()
    return _context_instance


def save_context():
    ctx = get_context()
    ctx.dedupe()
    ctx.save()


def reset_context_singleton():
    """Drop the cached singleton. Tests use this to avoid cross-test pollution."""
    global _context_instance
    _context_instance = None
