import os
from .base import LanguageAdapter
from .python_adapter import PythonAdapter
from .js_adapter import JSAdapter

_registry = {}

_ALIASES = {
    'javascript': ['typescript'],
}

def register(adapter):
    _registry[adapter.language] = adapter
    for alias in _ALIASES.get(adapter.language, []):
        _registry[alias] = adapter

_EXT_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'javascript',
    '.tsx': 'javascript',
    '.zap': 'zap',
}

def get_adapter(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    lang = _EXT_MAP.get(ext)
    return _registry.get(lang)

def all_adapters():
    return list(_registry.values())

def extract_file(filepath):
    adapter = get_adapter(filepath)
    if adapter:
        return adapter.extract(filepath)
    return None

# Register built-in adapters
register(PythonAdapter())
register(JSAdapter())
