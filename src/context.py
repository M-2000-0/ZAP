import json
import os

DEFAULT_FILE = '.zapcontext'

class ZapContext:
    def __init__(self):
        self.data = {
            'project': {'name': '', 'description': '', 'version': '0.1'},
            'intents': [],
            'decisions': [],
            'conventions': [],
            'apis': [],
        }

    @classmethod
    def load(cls, path=None):
        path = path or DEFAULT_FILE
        ctx = cls()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    loaded = json.load(f)
                    ctx.data.update(loaded)
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

    def add_intent(self, intent):
        self.data.setdefault('intents', []).append({
            'text': intent,
            'status': 'pending',
        })

    def add_decision(self, decision):
        self.data.setdefault('decisions', []).append(decision)

    def add_convention(self, convention):
        self.data.setdefault('conventions', []).append(convention)

    def add_api(self, name, description, endpoints=None):
        self.data.setdefault('apis', []).append({
            'name': name,
            'description': description,
            'endpoints': endpoints or [],
        })

_context_instance = None

def get_context():
    global _context_instance
    if _context_instance is None:
        _context_instance = ZapContext.load()
    return _context_instance

def save_context():
    ctx = get_context()
    ctx.save()
