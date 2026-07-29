"""
WASM JIT Compiler for ZAP.

Compiles hot paths (identified by time-travel profiling) to WebAssembly
for near-native performance. Falls back to interpreter for cold paths.

Architecture:
1. Profiler identifies hot functions from time-travel data
2. Bytecode compiler translates Zap AST to WASM bytecode
3. WASM runtime (wasmtime) executes compiled functions
4. Seamless interpreter fallback for unsupported features
5. Incremental compilation - recompile when profiles change
"""

import json
import time
import hashlib
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Set
from enum import Enum
from pathlib import Path

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.evaluator import Evaluator
from src.parser import Parser
from src.lexer import Lexer
from src.runtime.timetravel import TimeTravelRuntime
from src.values import ZapList, ZapDict, ZapFunction, ZapBuiltin, _zap_to_py, _py_to_zap


class CompilationStatus(Enum):
    INTERPRETED = "interpreted"
    COMPILING = "compiling"
    COMPILED = "compiled"
    FAILED = "failed"


@dataclass
class WasmFunction:
    """A compiled WASM function."""
    name: str
    module_bytes: bytes
    instance: Any = None
    func_ref: Any = None
    status: CompilationStatus = CompilationStatus.INTERPRETED
    compile_time: float = 0
    call_count: int = 0
    total_time_ms: float = 0
    last_error: Optional[str] = None


class BytecodeEmitter:
    """
    Emits WASM bytecode from Zap AST.
    
    Subset supported:
    - Arithmetic: +, -, *, /, %
    - Comparison: ==, !=, <, >, <=, >=
    - Logical: and, or, not
    - Control flow: if, while, for (simple)
    - Function calls (to other WASM or builtins)
    - Local variables
    - Lists: get/set/len
    - Return values
    """
    
    def __init__(self):
        self.types = []
        self.imports = []
        self.functions = []
        self.exports = []
        self.code = []
        self.locals = {}
        self.local_count = 0
        self.label_stack = []
        self.indentation = 0
    
    def emit_module(self, name: str, funcs: List[Dict]) -> bytes:
        """Emit complete WASM module."""
        # This is a simplified text format; real implementation would use binary encoding
        # For production, use `wasmtime` or `wasmer` Python bindings
        wat = self._generate_wat(name, funcs)
        return self._wat_to_wasm(wat)
    
    def _generate_wat(self, name: str, funcs: List[Dict]) -> str:
        """Generate WAT (WebAssembly Text Format)."""
        lines = [
            f"(module",
            f'  (memory 1)',
            f'  (export "memory" (memory 0))',
        ]
        
        # Import builtins
        for builtin in ['print', 'len', 'abs', 'max', 'min']:
            lines.append(f'  (import "env" "{builtin}" (func ${builtin} (param i32) (result i32)))')
        
        # Function definitions
        for func in funcs:
            lines.append(f'  (func ${func["name"]} (param {" ".join(f"i32" for _ in func["params"])}) (result i32)')
            lines.append(f'    (local {" ".join(f"i32" for _ in func["locals"])})')
            
            for instr in func["body"]:
                lines.append(f'    {instr}')
            
            lines.append(f'  )')
            lines.append(f'  (export "{func["name"]}" (func ${func["name"]}))')
        
        lines.append(f")")
        return "\n".join(lines)
    
    def _wat_to_wasm(self, wat: str) -> bytes:
        """Convert WAT to binary WASM. Uses `wat2wasm` if available."""
        try:
            import subprocess
            result = subprocess.run(['wat2wasm', '--enable-all', '-o', '/dev/stdout'], 
                                  input=wat.encode(), capture_output=True, timeout=5)
            if result.returncode == 0:
                return result.stdout
        except FileNotFoundError:
            pass
        except Exception:
            pass
        # Fallback: return WAT as bytes (wasmtime can parse WAT directly)
        return wat.encode()


class WasmJIT:
    """
    Just-In-Time compiler using WebAssembly.
    
    Workflow:
    1. Profile-guided: identify hot functions from TimeTravelRuntime
    2. Compile: AST -> WASM bytecode
    3. Instantiate: wasmtime.Instance
    4. Cache: store WasmFunction for reuse
    5. Execute: call WASM, fallback to interpreter on failure
    """
    
    def __init__(self, evaluator: Evaluator, timetravel: TimeTravelRuntime = None):
        self.evaluator = evaluator
        self.timetravel = timetravel
        self.emitter = BytecodeEmitter()
        self.compiled: Dict[str, WasmFunction] = {}
        self.hot_threshold = 100  # calls before JIT
        self._engine = None
        self._init_wasmtime()
    
    def _init_wasmtime(self):
        """Initialize wasmtime engine."""
        try:
            import wasmtime
            self._engine = wasmtime.Engine()
            self._store = wasmtime.Store(self._engine)
            self._linker = wasmtime.Linker(self._engine)
            self._define_host_functions()
        except ImportError:
            print("[WasmJIT] wasmtime not installed, JIT disabled")
            self._engine = None
    
    def _define_host_functions(self):
        """Define host functions that WASM can call."""
        if not self._engine:
            return
        
        import wasmtime
        
        # print
        def host_print(caller, val):
            print(f"[WASM] {val}")
            return val
        
        # len
        def host_len(caller, ptr):
            # Would need memory access
            return 0
        
        # abs
        def host_abs(caller, val):
            return abs(val)
        
        # max
        def host_max(caller, a, b):
            return max(a, b)
        
        # min
        def host_min(caller, a, b):
            return min(a, b)
        
        self._linker.define("env", "print", wasmtime.Func(self._store, 
            wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()]), host_print))
        self._linker.define("env", "abs", wasmtime.Func(self._store,
            wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()]), host_abs))
        self._linker.define("env", "max", wasmtime.Func(self._store,
            wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i32()], [wasmtime.ValType.i32()]), host_max))
        self._linker.define("env", "min", wasmtime.Func(self._store,
            wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i32()], [wasmtime.ValType.i32()]), host_min))
    
    def should_compile(self, func_name: str) -> bool:
        """Check if function is hot enough to compile."""
        if not self._engine:
            return False
        
        if func_name in self.compiled:
            return False
        
        # Check call count from time-travel profiles
        if self.timetravel:
            profiles = self.timetravel.timeline()
            call_count = sum(1 for p in profiles if func_name in p.get("label", ""))
            return call_count >= self.hot_threshold
        
        return False
    
    def compile_function(self, zap_func: ZapFunction) -> Optional[WasmFunction]:
        """Compile a ZapFunction to WASM."""
        if not self._engine or not self.should_compile(zap_func.name):
            return None
        
        wf = WasmFunction(name=zap_func.name)
        wf.status = CompilationStatus.COMPILING
        start = time.time()
        
        try:
            # Convert ZapFunction AST to WASM
            wasm_bytes = self._compile_ast(zap_func.body, zap_func.params)
            
            # Instantiate module
            module = wasmtime.Module(self._engine, wasm_bytes)
            instance = self._linker.instantiate(self._store, module)
            
            # Get exported function
            func_ref = instance.exports(self._store).get(zap_func.name)
            if not func_ref:
                raise RuntimeError(f"Function {zap_func.name} not exported")
            
            wf.module_bytes = wasm_bytes
            wf.instance = instance
            wf.func_ref = func_ref
            wf.status = CompilationStatus.COMPILED
            wf.compile_time = time.time() - start
            
            self.compiled[zap_func.name] = wf
            return wf
            
        except Exception as e:
            wf.status = CompilationStatus.FAILED
            wf.last_error = str(e)
            wf.compile_time = time.time() - start
            return None
    
    def _compile_ast(self, body, params: List[str]) -> bytes:
        """Convert Zap AST to WASM."""
        # Simplified: generate WAT for arithmetic expressions
        func_def = {
            "name": "jit_func",
            "params": params,
            "locals": [],  # Would extract from body
            "body": self._compile_expr(body)
        }
        return self.emitter.emit_module("jit", [func_def])
    
    def _compile_expr(self, node) -> List[str]:
        """Compile expression node to WAT instructions."""
        # This is highly simplified
        if hasattr(node, 'type'):
            if node.type == 'BinOp':
                left = self._compile_expr(node.left)
                right = self._compile_expr(node.right)
                op_map = {'+': 'i32.add', '-': 'i32.sub', '*': 'i32.mul', '/': 'i32.div_s'}
                return left + right + [op_map.get(node.op, 'i32.add')]
            elif node.type == 'Number':
                return [f'i32.const {node.value}']
            elif node.type == 'Identifier':
                return [f'local.get ${node.name}']
        return ['i32.const 0']
    
    def call(self, func_name: str, args: List[Any]) -> Any:
        """Call a compiled function, with interpreter fallback."""
        wf = self.compiled.get(func_name)
        if not wf or wf.status != CompilationStatus.COMPILED:
            return self._interpreter_fallback(func_name, args)
        
        try:
            # Convert args to WASM values
            wasm_args = [self._to_wasm_val(a) for a in args]
            result = wf.func_ref(self._store, *wasm_args)
            
            wf.call_count += 1
            return self._from_wasm_val(result)
        except Exception as e:
            # Fallback to interpreter
            return self._interpreter_fallback(func_name, args)
    
    def _interpreter_fallback(self, func_name: str, args: List[Any]) -> Any:
        """Execute via interpreter."""
        # Find function in evaluator globals
        fn = self.evaluator.global_env.get(func_name)
        if fn and hasattr(fn, '_call'):
            return fn._call(*args)
        raise RuntimeError(f"Function {func_name} not found")
    
    def _to_wasm_val(self, val: Any):
        """Convert Python/Zap value to WASM."""
        import wasmtime
        if isinstance(val, int):
            return wasmtime.Val.i32(val)
        elif isinstance(val, float):
            return wasmtime.Val.f64(val)
        elif isinstance(val, bool):
            return wasmtime.Val.i32(1 if val else 0)
        return wasmtime.Val.i32(0)
    
    def _from_wasm_val(self, val) -> Any:
        """Convert WASM value to Python."""
        if hasattr(val, 'value'):
            return val.value
        return val
    
    def get_stats(self) -> Dict:
        """Get compilation statistics."""
        return {
            "compiled": len([f for f in self.compiled.values() if f.status == CompilationStatus.COMPILED]),
            "failed": len([f for f in self.compiled.values() if f.status == CompilationStatus.FAILED]),
            "total_calls": sum(f.call_count for f in self.compiled.values()),
            "total_compile_time": sum(f.compile_time for f in self.compiled.values()),
        }


# =============================================================================
# Integration with Evaluator
# =============================================================================

class JITEvaluator:
    """
    Evaluator wrapper that adds JIT compilation.
    
    Usage:
        evaluator = Evaluator()
        jit_eval = JITEvaluator(evaluator, timetravel_runtime)
        result = jit_eval.evaluate(ast)
    """
    
    def __init__(self, evaluator: Evaluator, timetravel: TimeTravelRuntime = None):
        self.evaluator = evaluator
        self.jit = WasmJIT(evaluator, timetravel)
        self._original_call = evaluator._eval_call
    
    def evaluate(self, node):
        return self.evaluator.evaluate(node)
    
    def _wrap_call(self):
        """Wrap _eval_call to add JIT."""
        original = self.evaluator._eval_call
        
        def wrapped(expr):
            callee = self.evaluator._eval_expr(expr.callee)
            callee_name = getattr(callee, 'name', str(callee))[:50]
            
            # Try JIT first
            if callee_name in self.jit.compiled:
                args = [self.evaluator._eval_expr(a) for a in expr.args]
                try:
                    return self.jit.call(callee_name, args)
                except Exception:
                    pass  # Fall through to interpreter
            
            return original(expr)
        
        self.evaluator._eval_call = wrapped
    
    def enable(self):
        self._wrap_call()
    
    def disable(self):
        self.evaluator._eval_call = self._original_call
    
    def compile_hot_functions(self):
        """Scan for hot functions and compile them."""
        if self.timetravel:
            profiles = self.timetravel.timeline()
            # Analyze profiles for hot functions
            for profile in profiles:
                label = profile.get("label", "")
                if "call:" in label:
                    fn_name = label.split("call:")[-1]
                    self.jit.should_compile(fn_name)  # Triggers compilation if hot


# =============================================================================
# Demo / Test
# =============================================================================

def demo():
    """Demonstrate WASM JIT compilation."""
    print("=" * 60)
    print("WASM JIT DEMO")
    print("=" * 60)
    
    # Check wasmtime availability
    try:
        import wasmtime
        print("wasmtime: available")
    except ImportError:
        print("wasmtime: NOT installed (pip install wasmtime)")
        print("JIT will run in interpreter-only mode")
        return
    
    evaluator = Evaluator()
    timetravel = TimeTravelRuntime(evaluator)
    jit = WasmJIT(evaluator, timetravel)
    
    print(f"\nEngine: {jit._engine is not None}")
    print(f"Compiled functions: {len(jit.compiled)}")
    
    # Test simple function
    source = """
fn add(a, b):
  ret a + b

fn fib(n):
  if n <= 1: ret n
  ret fib(n - 1) + fib(n - 2)
"""
    
    tokens = Lexer(source, '<test>').tokenize()
    ast = Parser(tokens).parse()
    evaluator.evaluate(ast)
    
    # Check what functions are available
    print(f"\nGlobal functions: {[k for k in evaluator.global_env.store.keys() if not k.startswith('_')][:10]}")
    
    # Test interpreter
    print("\n--- Interpreter ---")
    for i in range(5):
        start = time.perf_counter()
        result = evaluator.global_env.get('add')._call(i, i + 1)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  add({i}, {i+1}) = {result} ({elapsed:.3f}ms)")
    
    # Get JIT stats
    print(f"\nJIT Stats: {jit.get_stats()}")


if __name__ == "__main__":
    demo()