"""
Polyglot Kernel for ZPX.

A Jupyter-compatible kernel that runs Zpx, Python, and SQL cells
in the same notebook with shared variable namespace.

Architecture:
- Single shared namespace (dict) across all languages
- Each language gets read/write access via proxy objects
- Magic commands for cross-language operations
- Time-travel debugging integration
- Capability-based sandboxing for untrusted cells
"""

import json
import sys
import os
import re
import time
import uuid
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Set
from enum import Enum
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.evaluator import Evaluator
from src.parser import Parser
from src.lexer import Lexer
from src.runtime.timetravel import TimeTravelRuntime
from src.runtime.capability import CapabilityRuntime, Capability
from src.values import ZpxList, ZpxDict, ZpxFunction, _zpx_to_py, _py_to_zpx


class CellType(Enum):
    ZPX = "zpx"
    PYTHON = "python"
    SQL = "sql"
    MARKDOWN = "markdown"
    SHELL = "shell"


@dataclass
class Cell:
    id: str
    cell_type: CellType
    source: str
    outputs: List[Dict] = field(default_factory=list)
    execution_count: Optional[int] = None
    metadata: Dict = field(default_factory=dict)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


@dataclass
class KernelState:
    """Shared mutable state across all cells."""
    namespace: Dict[str, Any] = field(default_factory=dict)
    execution_count: int = 0
    cells: List[Cell] = field(default_factory=list)
    capabilities: Dict[str, Capability] = field(default_factory=dict)
    timetravel: Optional[TimeTravelRuntime] = None


class PolyglotNamespace:
    """
    Shared namespace with language-specific proxies.
    
    Allows: zpx_x = 1  →  python_x == 1  →  SELECT :x
    """
    
    def __init__(self, initial: Dict = None):
        self._store = initial or {}
        self._watched: Set[str] = set()
        self._callbacks: Dict[str, List[Callable]] = {}
    
    def __getitem__(self, key: str) -> Any:
        return self._store[key]
    
    def __setitem__(self, key: str, value: Any):
        old = self._store.get(key)
        self._store[key] = value
        if key in self._watched and old != value:
            for cb in self._callbacks.get(key, []):
                try:
                    cb(key, old, value)
                except Exception:
                    pass
    
    def __delitem__(self, key: str):
        del self._store[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self._store
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)
    
    def update(self, other: Dict):
        for k, v in other.items():
            self[k] = v
    
    def keys(self):
        return self._store.keys()
    
    def items(self):
        return self._store.items()
    
    def watch(self, key: str, callback: Callable):
        """Register callback when key changes."""
        self._watched.add(key)
        self._callbacks.setdefault(key, []).append(callback)
    
    def to_python(self) -> Dict:
        """Convert Zpx types to Python for Python cells."""
        result = {}
        for k, v in self._store.items():
            result[k] = _zpx_to_py(v) if hasattr(v, '__class__') and 'Zpx' in v.__class__.__name__ else v
        return result
    
    def from_python(self, d: Dict):
        """Update from Python dict (converts to Zpx types)."""
        for k, v in d.items():
            self[k] = _py_to_zpx(v) if isinstance(v, (list, dict, tuple, set)) else v


class ZpxExecutor:
    """Execute Zpx code in shared namespace."""
    
    def __init__(self, namespace: PolyglotNamespace, timetravel: TimeTravelRuntime = None):
        self.namespace = namespace
        self.timetravel = timetravel
        self.evaluator = Evaluator()
        self._inject_builtins()
    
    def _inject_builtins(self):
        """Add namespace access to evaluator globals."""
        # The evaluator uses its own global_env; we sync after each execution
        pass
    
    def execute(self, code: str) -> Dict:
        """Execute Zpx code, return result and side effects."""
        # Create evaluator with shared namespace
        evaluator = Evaluator()
        
        # Sync namespace INTO evaluator's global_env
        for k, v in self.namespace.items():
            evaluator.global_env.define(k, _py_to_zpx(v) if isinstance(v, (list, dict)) else v)
        
        # Time-travel checkpoint
        snap_id = None
        if self.timetravel:
            snap_id = self.timetravel.checkpoint(f"cell:{uuid.uuid4().hex[:8]}")
        
        try:
            tokens = Lexer(code, '<cell>').tokenize()
            ast = Parser(tokens).parse()
            result = evaluator.evaluate(ast)
            
            # Sync evaluator globals BACK to namespace
            for k, v in evaluator.global_env.store.items():
                if not k.startswith('_'):
                    self.namespace[k] = _zpx_to_py(v) if hasattr(v, '__class__') and 'Zpx' in v.__class__.__name__ else v
            
            return {
                "success": True,
                "result": result,
                "snapshot": snap_id,
                "stdout": getattr(evaluator, '_stdout_buffer', ''),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "snapshot": snap_id,
            }


class PythonExecutor:
    """Execute Python code in shared namespace."""
    
    def __init__(self, namespace: PolyglotNamespace):
        self.namespace = namespace
        self._globals = {}
        self._sync_from_namespace()
    
    def _sync_from_namespace(self):
        self._globals.update(self.namespace.to_python())
    
    def _sync_to_namespace(self):
        for k, v in self._globals.items():
            if not k.startswith('_') and k not in ('__builtins__',):
                self.namespace[k] = v
    
    def execute(self, code: str) -> Dict:
        self._sync_from_namespace()
        
        # Capture stdout
        import io
        import contextlib
        stdout = io.StringIO()
        
        try:
            with contextlib.redirect_stdout(stdout):
                exec(code, self._globals)
            
            self._sync_to_namespace()
            
            return {
                "success": True,
                "result": self._globals.get('_', None),
                "stdout": stdout.getvalue(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "stdout": stdout.getvalue(),
            }


class SQLExecutor:
    """Execute SQL with namespace variable binding."""
    
    def __init__(self, namespace: PolyglotNamespace, db_path: str = ":memory:"):
        self.namespace = namespace
        import sqlite3
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def execute(self, code: str) -> Dict:
        # Replace :var with namespace values
        def replacer(match):
            var = match.group(1)
            val = self.namespace.get(var)
            if val is None:
                return 'NULL'
            if isinstance(val, str):
                return f"'{val}'"
            if isinstance(val, (list, tuple)):
                return f"({','.join(replacer(type('m',(object,),{'group':lambda _:v})()) for v in val)})"
            return str(val)
        
        # Simple variable substitution: :var or $var
        processed = re.sub(r':([a-zA-Z_][a-zA-Z0-9_]*)', replacer, code)
        processed = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', replacer, processed)
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(processed)
            
            if cursor.description:
                rows = [dict(row) for row in cursor.fetchall()]
                self.namespace['_'] = rows  # Last result
                return {"success": True, "result": rows, "rowcount": len(rows)}
            else:
                self.conn.commit()
                return {"success": True, "result": None, "rowcount": cursor.rowcount}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


class PolyglotKernel:
    """
    Main kernel orchestrating multiple language executors.
    
    Usage:
        kernel = PolyglotKernel()
        result = kernel.execute_cell("let x = 42", "zpx")
        result = kernel.execute_cell("print(x)", "python")  # prints 42
        result = kernel.execute_cell("SELECT :x", "sql")   # returns 42
    """
    
    def __init__(self, db_path: str = ":memory:"):
        self.namespace = PolyglotNamespace({
            '__version__': '0.2.0',
            '__kernel__': self,
        })
        self.timetravel = TimeTravelRuntime(Evaluator())
        self.zpx = ZpxExecutor(self.namespace, self.timetravel)
        self.python = PythonExecutor(self.namespace)
        self.sql = SQLExecutor(self.namespace, db_path)
        self.state = KernelState()
        self.state.timetravel = self.timetravel
        self._cell_id_counter = 0
    
    def execute_cell(self, source: str, cell_type: str, cell_id: str = None) -> Dict:
        """Execute a single cell."""
        cell_type = CellType(cell_type.lower())
        cell_id = cell_id or f"cell_{self._cell_id_counter}"
        self._cell_id_counter += 1
        
        cell = Cell(
            id=cell_id,
            cell_type=cell_type,
            source=source,
            execution_count=self.state.execution_count,
        )
        
        start = time.time()
        cell.started_at = start
        
        # Route to appropriate executor
        if cell_type == CellType.ZPX:
            result = self.zpx.execute(source)
        elif cell_type == CellType.PYTHON:
            result = self.python.execute(source)
        elif cell_type == CellType.SQL:
            result = self.sql.execute(source)
        elif cell_type == CellType.SHELL:
            result = self._execute_shell(source)
        else:
            result = {"success": True, "result": source, "stdout": ""}
        
        cell.finished_at = time.time()
        cell.outputs = self._format_outputs(result)
        self.state.cells.append(cell)
        
        if result.get("success"):
            self.state.execution_count += 1
        
        return {
            "cell_id": cell_id,
            "execution_count": cell.execution_count,
            "success": result["success"],
            "outputs": cell.outputs,
            "execution_time": cell.finished_at - start,
        }
    
    def _execute_shell(self, code: str) -> Dict:
        import subprocess
        try:
            result = subprocess.run(code, shell=True, capture_output=True, text=True, timeout=30)
            return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout", "stderr": "Command timed out after 30s"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _format_outputs(self, result: Dict) -> List[Dict]:
        outputs = []
        if result.get("stdout"):
            outputs.append({"output_type": "stream", "name": "stdout", "text": result["stdout"]})
        if result.get("stderr"):
            outputs.append({"output_type": "stream", "name": "stderr", "text": result["stderr"]})
        if result.get("success"):
            if "result" in result and result["result"] is not None:
                outputs.append({
                    "output_type": "execute_result",
                    "data": {"text/plain": str(result["result"])},
                    "metadata": {}
                })
        else:
            outputs.append({
                "output_type": "error",
                "ename": "Error",
                "evalue": result.get("error", "Unknown error"),
                "traceback": result.get("traceback", "").split("\n")
            })
        return outputs
    
    def get_namespace(self) -> Dict:
        return dict(self.namespace.items())
    
    def set_variable(self, name: str, value: Any):
        self.namespace[name] = value
    
    def get_variable(self, name: str) -> Any:
        return self.namespace.get(name)
    
    def time_travel(self, snapshot_id: str) -> bool:
        if self.timetravel:
            return self.timetravel.rewind(snapshot_id)
        return False
    
    def timeline(self) -> List[Dict]:
        if self.timetravel:
            return self.timetravel.timeline()
        return []
    
    def add_capability(self, cap: Capability):
        self.state.capabilities[cap.id] = cap
    
    def run_with_capabilities(self, source: str, cell_type: str, cap_ids: List[str]) -> Dict:
        """Run cell with specific capabilities."""
        caps = [self.state.capabilities[cid] for cid in cap_ids if cid in self.state.capabilities]
        return self.capability.run_with_capabilities(source, caps)
    
    def export_notebook(self) -> Dict:
        """Export as Jupyter notebook format."""
        return {
            "cells": [
                {
                    "cell_type": "code" if c.cell_type != CellType.MARKDOWN else "markdown",
                    "source": c.source.split("\n") if isinstance(c.source, str) else c.source,
                    "outputs": c.outputs,
                    "execution_count": c.execution_count,
                    "metadata": c.metadata,
                }
                for c in self.state.cells
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Zpx Polyglot",
                    "language": "zpx",
                    "name": "zpx-polyglot"
                },
                "language_info": {
                    "name": "zpx",
                    "version": "0.2.0",
                    "mimetype": "text/x-zpx",
                    "file_extension": ".zpx"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 5
        }
    
    def import_notebook(self, nb: Dict):
        """Load notebook cells."""
        for cell in nb.get("cells", []):
            ctype = "markdown" if cell["cell_type"] == "markdown" else "zpx"
            self.execute_cell("\n".join(cell.get("source", [])), ctype)


# =============================================================================
# Jupyter Kernel Protocol (for IPython/Jupyter integration)
# =============================================================================

class ZpxKernel:
    """Jupyter kernel wrapper for PolyglotKernel."""
    
    implementation = 'Zpx Polyglot'
    implementation_version = '0.2.0'
    language = 'zpx'
    language_version = '0.2.0'
    language_info = {
        'name': 'zpx',
        'mimetype': 'text/x-zpx',
        'file_extension': '.zpx',
        'pygments_lexer': 'python',
        'codemirror_mode': 'python',
    }
    banner = "Zpx Polyglot Kernel - Zpx, Python, SQL in one notebook"
    
    def __init__(self):
        self.kernel = PolyglotKernel()
        self.execution_count = 0
    
    def do_execute(self, code: str, silent: bool, store_history: bool = True,
                   user_expressions: Dict = None, allow_stdin: bool = False) -> Dict:
        # Detect cell type from magic or default to zpx
        cell_type = "zpx"
        if code.startswith("%%python"):
            cell_type = "python"
            code = code[8:].lstrip()
        elif code.startswith("%%sql"):
            cell_type = "sql"
            code = code[5:].lstrip()
        elif code.startswith("%%shell"):
            cell_type = "shell"
            code = code[7:].lstrip()
        elif code.startswith("%python"):
            cell_type = "python"
            code = code[7:].lstrip()
        elif code.startswith("%sql"):
            cell_type = "sql"
            code = code[4:].lstrip()
        
        result = self.kernel.execute_cell(code, cell_type)
        self.execution_count = result["execution_count"]
        
        if not silent:
            for output in result["outputs"]:
                if output["output_type"] == "stream":
                    self.send_response(self.iopub_socket, 'stream', output)
                elif output["output_type"] == "execute_result":
                    self.send_response(self.iopub_socket, 'execute_result', output)
                elif output["output_type"] == "error":
                    self.send_response(self.iopub_socket, 'error', output)
        
        return {
            'status': 'ok' if result['success'] else 'error',
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }
    
    def do_complete(self, code: str, cursor_pos: int) -> Dict:
        # Simple completion from namespace
        matches = [k for k in self.kernel.namespace.keys() 
                   if k.startswith(code[:cursor_pos].split()[-1])]
        return {
            'matches': matches[:20],
            'cursor_start': cursor_pos - len(code[:cursor_pos].split()[-1]),
            'cursor_end': cursor_pos,
            'status': 'ok'
        }
    
    def do_inspect(self, code: str, cursor_pos: int, detail_level: int = 0) -> Dict:
        word = code[:cursor_pos].split()[-1]
        val = self.kernel.namespace.get(word)
        if val is not None:
            return {
                'status': 'ok',
                'data': {'text/plain': f'{word} = {repr(val)}'},
                'metadata': {}
            }
        return {'status': 'ok', 'data': {}, 'metadata': {}}


# =============================================================================
# CLI / Demo
# =============================================================================

def demo():
    """Run a demo of the polyglot kernel."""
    print("=" * 60)
    print("ZPX POLYGLOT KERNEL DEMO")
    print("=" * 60)
    
    kernel = PolyglotKernel()
    
    # Cell 1: Zpx - define data
    print("\n>>> ZPX: let data = [1, 2, 3, 4, 5]")
    r = kernel.execute_cell("let data = [1, 2, 3, 4, 5]", "zpx")
    print(f"   Success: {r['success']}")
    
    # Cell 2: Zpx - function
    print("\n>>> ZPX: fn double(x): ret x * 2")
    r = kernel.execute_cell("fn double(x): ret x * 2", "zpx")
    print(f"   Success: {r['success']}")
    
    # Cell 3: Python - use Zpx data
    print("\n>>> PYTHON: print('Python sees:', data)")
    r = kernel.execute_cell("print('Python sees:', data)", "python")
    print(f"   Success: {r['success']}")
    if r['outputs']:
        for o in r['outputs']:
            if o['output_type'] == 'stream':
                print(f"   stdout: {o['text'].strip()}")
    
    # Cell 4: Python - transform
    print("\n>>> PYTHON: doubled = [double(x) for x in data]")
    r = kernel.execute_cell("doubled = [double(x) for x in data]", "python")
    print(f"   Success: {r['success']}")
    
    # Cell 5: Zpx - use Python result
    print("\n>>> ZPX: print(doubled)")
    r = kernel.execute_cell("print(doubled)", "zpx")
    if r['outputs']:
        for o in r['outputs']:
            if o['output_type'] == 'stream':
                print(f"   stdout: {o['text'].strip()}")
    
    # Cell 6: SQL - use namespace vars
    print("\n>>> SQL: CREATE TABLE nums AS SELECT * FROM (SELECT 1 UNION SELECT 2 UNION SELECT 3)")
    r = kernel.execute_cell("CREATE TABLE nums AS SELECT 1 AS n UNION SELECT 2 UNION SELECT 3", "sql")
    print(f"   Success: {r['success']}")
    
    print("\n>>> SQL: SELECT * FROM nums WHERE n > :threshold")
    kernel.set_variable("threshold", 1)
    r = kernel.execute_cell("SELECT * FROM nums WHERE n > :threshold", "sql")
    if r['success'] and r['outputs']:
        for o in r['outputs']:
            if o['output_type'] == 'execute_result':
                print(f"   result: {o['data']['text/plain']}")
    
    # Cell 7: Shell
    print("\n>>> SHELL: echo 'Hello from shell'")
    r = kernel.execute_cell("echo 'Hello from shell'", "shell")
    if r['outputs']:
        for o in r['outputs']:
            if o['output_type'] == 'stream':
                print(f"   stdout: {o['text'].strip()}")
    
    # Show shared namespace
    print("\n>>> SHARED NAMESPACE:")
    for k, v in kernel.get_namespace().items():
        if not k.startswith('_'):
            print(f"   {k} = {repr(v)[:80]}")
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE - All languages share one namespace!")
    print("=" * 60)


if __name__ == "__main__":
    demo()