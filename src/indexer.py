import json
import os
import time
from .analysis import extract_file as extract_zap, build_dependency_graph
from .adapters import extract_file as extract_any, get_adapter

INDEX_FILE = '.zapindex'

class ProjectIndex:
    def __init__(self, root='.'):
        self.root = os.path.abspath(root)
        self.files = {}
        self.file_hashes = {}
        self.dep_graph = {}

    SUPPORTED_EXTS = {'.zap', '.py', '.js', '.jsx', '.ts', '.tsx'}

    def scan(self):
        new_files = {}
        for dirpath, _, filenames in os.walk(self.root):
            if '.zapcontext' in dirpath or '.zapindex' in dirpath:
                for skip in ('node_modules', '__pycache__', '.git', '.venv', 'venv', 'env'):
                    if skip in dirpath.split(os.sep):
                        break
                else:
                    continue
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in self.SUPPORTED_EXTS:
                    path = os.path.join(dirpath, fn)
                    self._index_file(path, new_files)
        self.files = new_files
        self.dep_graph = build_dependency_graph(list(self.files.values()))

    def _index_file(self, path, store):
        try:
            h = self._hash_file(path)
            if self.file_hashes.get(path) == h:
                store[path] = self.files.get(path, {})
                return
            ext = os.path.splitext(path)[1].lower()
            if ext == '.zap':
                idx = extract_zap(path)
            else:
                idx = extract_any(path) or extract_zap(path)
            store[path] = idx
            self.file_hashes[path] = h
        except Exception as e:
            pass

    def _hash_file(self, path):
        st = os.stat(path)
        return f"{st.st_mtime}:{st.st_size}"

    def watch(self, interval=2.0):
        self.scan()
        self.save()
        while True:
            time.sleep(interval)
            changed = False
            for dirpath, _, filenames in os.walk(self.root):
                for fn in filenames:
                    if fn.endswith('.zap'):
                        path = os.path.join(dirpath, fn)
                        h = self._hash_file(path)
                        if self.file_hashes.get(path) != h:
                            self._index_file(path, self.files)
                            changed = True
                            print(f"[zap index] updated: {path}")
            removed = [p for p in self.files if not os.path.exists(p)]
            for p in removed:
                del self.files[p]
                del self.file_hashes[p]
                changed = True
                print(f"[zap index] removed: {p}")
            if changed:
                self.dep_graph = build_dependency_graph(list(self.files.values()))
                self.save()

    def save(self, path=None):
        path = path or os.path.join(self.root, INDEX_FILE)
        data = {
            'root': self.root,
            'files': {},
            'dep_graph': self.dep_graph,
        }
        for filepath, idx in self.files.items():
            rel = os.path.relpath(filepath, self.root)
            data['files'][rel] = {
                'symbols': idx['symbols'],
                'calls': idx['calls'],
                'imports': idx['imports'],
            }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self, path=None):
        path = path or os.path.join(self.root, INDEX_FILE)
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            for rel, idx in data.get('files', {}).items():
                abspath = os.path.join(self.root, rel)
                self.files[abspath] = {**idx, 'file': abspath}
            self.dep_graph = data.get('dep_graph', {})

    def query_symbol(self, name):
        results = []
        for filepath, idx in self.files.items():
            for sym in idx['symbols']:
                if sym['name'] == name:
                    results.append({**sym, 'file': filepath})
        return results

    def query_calls_to(self, name):
        results = []
        for filepath, idx in self.files.items():
            for c in idx['calls']:
                if c['callee'] == name:
                    results.append({**c, 'file': filepath})
        return results

    def query_calls_from(self, scope):
        results = []
        for filepath, idx in self.files.items():
            for c in idx['calls']:
                if c['from_scope'] == scope:
                    results.append({**c, 'file': filepath})
        return results
