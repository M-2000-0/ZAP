import json
import os
from .analysis import SymbolExtractor, extract_file, build_dependency_graph
from .lexer import Lexer
from .parser import Parser
from .ast_nodes import *

class SemanticGraph:
    def __init__(self, root_dir):
        self.root_dir = os.path.abspath(root_dir)
        self.files = {}
        self.symbols = {}
        self.dependencies = {}
        self.type_hierarchy = {}
        self.ecs_graph = {
            'entities': {},
            'components': {},
            'systems': {},
            'scenes': {},
        }

    def scan(self):
        for dirpath, _, filenames in os.walk(self.root_dir):
            for fn in filenames:
                if fn.endswith('.zpx'):
                    filepath = os.path.join(dirpath, fn)
                    try:
                        idx = extract_file(filepath)
                        self.files[filepath] = idx
                        for sym in idx['symbols']:
                            key = f"{sym['scope']}.{sym['name']}"
                            self.symbols[key] = {**sym, 'file': filepath}
                            self._index_ecs(sym, filepath)
                    except Exception as e:
                        pass
        self.dependencies = build_dependency_graph(list(self.files.values()))
        self._build_type_hierarchy()
        return self

    def _index_ecs(self, sym, filepath):
        kind = sym.get('kind')
        name = sym.get('name')
        if kind == 'entity':
            self.ecs_graph['entities'][name] = {
                'file': filepath,
                'components': sym.get('components', []),
                'used_by_systems': [],
            }
        elif kind == 'component':
            self.ecs_graph['components'][name] = {
                'file': filepath,
                'fields': sym.get('fields', []),
                'used_by_entities': [],
                'used_by_systems': [],
            }
        elif kind == 'system':
            self.ecs_graph['systems'][name] = {
                'file': filepath,
                'requires': sym.get('requires', []),
            }
        elif kind == 'scene':
            self.ecs_graph['scenes'][name] = {
                'file': filepath,
                'inherit': sym.get('inherit'),
                'entities': sym.get('entities', []),
            }

    def _build_type_hierarchy(self):
        for sym_key, sym in self.symbols.items():
            kind = sym.get('kind')
            if kind == 'component':
                comp_name = sym['name']
                for ek, ev in self.ecs_graph['entities'].items():
                    if comp_name in ev.get('components', []):
                        ev['used_by_systems'] = ev.get('used_by_systems', [])
                for sk, sv in self.ecs_graph['systems'].items():
                    if comp_name in sv.get('requires', []):
                        if comp_name not in self.ecs_graph['components']:
                            continue
                        comp_info = self.ecs_graph['components'][comp_name]
                        comp_info.setdefault('used_by_systems', []).append(sk)
                for ek, ev in self.ecs_graph['entities'].items():
                    if comp_name in ev.get('components', []):
                        comp_info = self.ecs_graph['components'][comp_name]
                        comp_info.setdefault('used_by_entities', []).append(ek)

    def query(self, qtype=None, name=None, scope=None):
        results = []
        for sym_key, sym in self.symbols.items():
            if qtype and sym.get('kind') != qtype:
                continue
            if name and name not in sym.get('name', ''):
                continue
            if scope and not sym_key.startswith(scope):
                continue
            results.append(sym)
        return results

    def get_entity_components(self, entity_name):
        entity = self.ecs_graph['entities'].get(entity_name)
        if not entity:
            return []
        comps = []
        for cname in entity.get('components', []):
            cinfo = self.ecs_graph['components'].get(cname)
            if cinfo:
                comps.append({'name': cname, 'fields': cinfo.get('fields', [])})
        return comps

    def get_system_dependencies(self, system_name):
        system = self.ecs_graph['systems'].get(system_name)
        if not system:
            return []
        deps = []
        for comp_name in system.get('requires', []):
            cinfo = self.ecs_graph['components'].get(comp_name)
            if cinfo:
                deps.append({
                    'component': comp_name,
                    'fields': cinfo.get('fields', []),
                    'used_by_entities': cinfo.get('used_by_entities', []),
                })
        return deps

    def get_cross_file_references(self, symbol_name):
        refs = []
        for filepath, idx in self.files.items():
            for c in idx.get('calls', []):
                if c['callee'] == symbol_name or c['callee'].endswith(f'.{symbol_name}'):
                    refs.append({'file': filepath, 'line': c['line'], 'scope': c['from_scope']})
        return refs

    def to_json(self, pretty=True):
        result = {
            'root': self.root_dir,
            'file_count': len(self.files),
            'symbol_count': len(self.symbols),
            'files': {},
            'dependencies': {},
            'ecs': self.ecs_graph,
        }
        for filepath, idx in self.files.items():
            rel = os.path.relpath(filepath, self.root_dir)
            result['files'][rel] = {
                'imports': idx.get('imports', []),
                'symbols': idx.get('symbols', []),
                'calls': idx.get('calls', []),
            }
        for filepath, info in self.dependencies.items():
            rel = os.path.relpath(filepath, self.root_dir)
            result['dependencies'][rel] = {
                'provides': info.get('provides', []),
                'depends_on': [os.path.relpath(d, self.root_dir) for d in info.get('depends_on', [])],
            }
        if pretty:
            return json.dumps(result, indent=2)
        return json.dumps(result)

    def summarize_for_ai(self):
        lines = [f"Project: {self.root_dir}", f"Files: {len(self.files)}", f"Symbols: {len(self.symbols)}", ""]
        if self.ecs_graph['entities']:
            lines.append("=== Entities ===")
            for name, info in self.ecs_graph['entities'].items():
                comps = ', '.join(info['components'])
                lines.append(f"  {name}({comps})")
            lines.append("")
        if self.ecs_graph['components']:
            lines.append("=== Components ===")
            for name, info in self.ecs_graph['components'].items():
                fields = ', '.join(f"{f['name']}: {f['type']}" for f in info['fields'])
                lines.append(f"  {name} {{{fields}}}")
            lines.append("")
        if self.ecs_graph['systems']:
            lines.append("=== Systems ===")
            for name, info in self.ecs_graph['systems'].items():
                reqs = ', '.join(info['requires'])
                lines.append(f"  {name}({reqs})")
            lines.append("")
        if self.ecs_graph['scenes']:
            lines.append("=== Scenes ===")
            for name, info in self.ecs_graph['scenes'].items():
                ents = ', '.join(f"{e['var']}: {e['type']}" for e in info['entities'])
                lines.append(f"  {name} -> {ents}")
            lines.append("")
        functions = self.query(qtype='function')
        if functions:
            lines.append("=== Functions ===")
            for fn in functions[:20]:
                params = ', '.join(fn.get('params', []))
                lines.append(f"  {fn['name']}({params}) -> {fn.get('return_type', 'any')}")
            lines.append("")
        return '\n'.join(lines)
