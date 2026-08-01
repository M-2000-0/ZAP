"""
Intent-Based Runtime for ZPX.

Core idea: Developers declare WHAT they want (intent), the runtime + AI figures out HOW.
The runtime continuously optimizes, profiles, and rewrites hot paths.

Architecture:
1. @intent decorator captures declarative specifications
2. IntentCompiler uses AI (or built-in strategies) to generate optimized implementations
3. TimeTravelRuntime profiles execution, feeds back to compiler
4. CapabilityRuntime sandboxes generated code
5. Hot paths are JIT-compiled to WASM/native via bytecode

Example:
    @intent("user can checkout in <200ms", budget_ms=200)
    fn checkout(cart, user):
        # AI synthesizes: cache user, async payment, fallback, retries
        pass

    # Runtime auto-profiles, rewrites hot path to WASM, explains decisions
"""

import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Set
from enum import Enum
from abc import ABC, abstractmethod
from functools import wraps
from contextlib import contextmanager

from src.runtime.timetravel import TimeTravelRuntime
from src.runtime.capability import CapabilityRuntime, Capability
from src.values import ZpxDict, ZpxList, ZpxFunction, ZpxBuiltin
from src.evaluator import Evaluator


# =============================================================================
# Intent Specification
# =============================================================================

class IntentType(Enum):
    PERFORMANCE = "performance"      # latency, throughput, budget
    RELIABILITY = "reliability"      # retries, fallbacks, circuit breakers
    SECURITY = "security"            # capabilities, sandboxing, audit
    COST = "cost"                    # API call budget, token budget
    CORRECTNESS = "correctness"      # contracts, invariants, tests


@dataclass
class Intent:
    """Declarative intent specification."""
    name: str
    target: str                    # function/module name
    intent_type: Optional[IntentType] = None
    spec: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1              # higher = more important
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def hash(self) -> str:
        content = f"{self.name}:{self.intent_type.value if self.intent_type else 'unknown'}:{json.dumps(self.spec, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class PerformanceIntent(Intent):
    """Performance budget intent."""
    budget_ms: float = 100
    percentile: float = 0.95       # p95 latency budget
    throughput_rps: Optional[float] = None
    warmup_runs: int = 10
    
    def __post_init__(self):
        self.intent_type = IntentType.PERFORMANCE
        self.spec = {
            "budget_ms": self.budget_ms,
            "percentile": self.percentile,
            "throughput_rps": self.throughput_rps,
        }


@dataclass
class ReliabilityIntent(Intent):
    """Reliability intent with retries, fallbacks, circuit breakers."""
    max_retries: int = 3
    base_delay_ms: float = 100
    max_delay_ms: float = 5000
    fallback: Optional[str] = None      # function name to call on failure
    circuit_breaker_threshold: int = 5  # failures before opening
    circuit_breaker_timeout_s: float = 30
    
    def __post_init__(self):
        self.intent_type = IntentType.RELIABILITY
        self.spec = {
            "max_retries": self.max_retries,
            "base_delay_ms": self.base_delay_ms,
            "fallback": self.fallback,
            "circuit_breaker": {
                "threshold": self.circuit_breaker_threshold,
                "timeout_s": self.circuit_breaker_timeout_s,
            }
        }


@dataclass
class SecurityIntent(Intent):
    """Security/capability intent."""
    capabilities: List[str] = field(default_factory=list)  # capability names
    deny_by_default: bool = True
    audit_log: bool = True
    max_memory_mb: Optional[int] = None
    max_cpu_ms: Optional[int] = None
    
    def __post_init__(self):
        self.intent_type = IntentType.SECURITY
        self.spec = {
            "capabilities": self.capabilities,
            "deny_by_default": self.deny_by_default,
            "audit_log": self.audit_log,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_ms": self.max_cpu_ms,
        }


@dataclass
class CostIntent(Intent):
    """Cost/token budget intent."""
    max_tokens: int = 10000
    max_api_calls: int = 100
    max_cost_usd: float = 0.01
    track_per_user: bool = True
    
    def __post_init__(self):
        self.intent_type = IntentType.COST
        self.spec = {
            "max_tokens": self.max_tokens,
            "max_api_calls": self.max_api_calls,
            "max_cost_usd": self.max_cost_usd,
        }


# =============================================================================
# Intent Registry & Compiler
# =============================================================================

class Strategy(ABC):
    """Optimization strategy for an intent."""
    
    @abstractmethod
    def apply(self, fn: Callable, intent: Intent, runtime: 'IntentRuntime') -> Callable:
        """Return optimized version of fn."""
        pass
    
    @abstractmethod
    def name(self) -> str:
        pass


class CacheStrategy(Strategy):
    """Auto-caching for pure functions."""
    
    def name(self) -> str:
        return "auto_cache"
    
    def apply(self, fn: Callable, intent: Intent, runtime: 'IntentRuntime') -> Callable:
        cache = {}
        cache_stats = {"hits": 0, "misses": 0}
        
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            if key in cache:
                cache_stats["hits"] += 1
                return cache[key]
            cache_stats["misses"] += 1
            result = fn(*args, **kwargs)
            cache[key] = result
            return result
        
        wrapper._cache = cache
        wrapper._cache_stats = cache_stats
        return wrapper


class RetryStrategy(Strategy):
    """Exponential backoff retry with circuit breaker."""
    
    def name(self) -> str:
        return "retry_circuit_breaker"
    
    def apply(self, fn: Callable, intent: Intent, runtime: 'IntentRuntime') -> Callable:
        spec = intent.spec
        max_retries = spec.get("max_retries", 3)
        base_delay = spec.get("base_delay_ms", 100) / 1000
        max_delay = spec.get("max_delay_ms", 5000) / 1000
        fallback_name = spec.get("fallback")
        cb = spec.get("circuit_breaker", {})
        cb_threshold = cb.get("threshold", 5)
        cb_timeout = cb.get("timeout_s", 30)
        
        failure_count = 0
        circuit_open = False
        circuit_open_time = 0
        
        def get_fallback():
            if fallback_name and hasattr(runtime, 'get_function'):
                return runtime.get_function(fallback_name)
            return None
        
        @wraps(fn)
        def wrapper(*args, **kwargs):
            nonlocal failure_count, circuit_open, circuit_open_time
            
            # Check circuit breaker
            if circuit_open:
                if time.time() - circuit_open_time > cb_timeout:
                    circuit_open = False
                    failure_count = 0
                else:
                    fb = get_fallback()
                    if fb:
                        return fb(*args, **kwargs)
                    raise RuntimeError("Circuit breaker open")
            
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    result = fn(*args, **kwargs)
                    failure_count = 0
                    return result
                except Exception as e:
                    last_error = e
                    failure_count += 1
                    
                    if failure_count >= cb_threshold:
                        circuit_open = True
                        circuit_open_time = time.time()
                    
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        time.sleep(delay)
                    else:
                        fb = get_fallback()
                        if fb:
                            return fb(*args, **kwargs)
                        raise
            
            raise last_error
        
        return wrapper


class ParallelStrategy(Strategy):
    """Parallelize independent operations."""
    
    def name(self) -> str:
        return "parallelize"
    
    def apply(self, fn: Callable, intent: Intent, runtime: 'IntentRuntime') -> Callable:
        # This would need AST analysis to find parallelizable sections
        # For now, return original
        return fn


class WasmCompileStrategy(Strategy):
    """Compile hot functions to WASM."""
    
    def name(self) -> str:
        return "wasm_compile"
    
    def apply(self, fn: Callable, intent: Intent, runtime: 'IntentRuntime') -> Callable:
        # Placeholder - would integrate with wasmtime or similar
        # For now, mark as compilable
        fn._wasm_compilable = True
        return fn


class IntentCompiler:
    """
    Compiles intents into optimized implementations using strategies.
    
    Pipeline:
    1. Parse intent specs
    2. Select applicable strategies
    3. Chain strategies (retry -> cache -> parallel -> wasm)
    4. Generate optimized function
    5. Register with runtime for hot-path monitoring
    """
    
    def __init__(self):
        self.strategies: Dict[IntentType, List[Strategy]] = {
            IntentType.PERFORMANCE: [CacheStrategy(), ParallelStrategy(), WasmCompileStrategy()],
            IntentType.RELIABILITY: [RetryStrategy()],
            IntentType.SECURITY: [],  # Handled by CapabilityRuntime
            IntentType.COST: [],
        }
        self.compiled: Dict[str, Callable] = {}
    
    def register_strategy(self, intent_type: IntentType, strategy: Strategy):
        if intent_type not in self.strategies:
            self.strategies[intent_type] = []
        self.strategies[intent_type].append(strategy)
    
    def compile(self, fn: Callable, intent: Intent, runtime: 'IntentRuntime') -> Callable:
        """Apply all applicable strategies to fn."""
        key = f"{intent.target}:{intent.hash()}"
        
        if key in self.compiled:
            return self.compiled[key]
        
        strategies = self.strategies.get(intent.intent_type, [])
        optimized = fn
        
        for strategy in strategies:
            try:
                optimized = strategy.apply(optimized, intent, runtime)
            except Exception as e:
                print(f"Strategy {strategy.name()} failed: {e}")
        
        self.compiled[key] = optimized
        return optimized
    
    def get_compiled(self, intent: Intent) -> Optional[Callable]:
        key = f"{intent.target}:{intent.hash()}"
        return self.compiled.get(key)


# =============================================================================
# Intent Runtime (Main Integration Point)
# =============================================================================

class IntentRuntime:
    """
    Main runtime that combines:
    - Intent declaration & compilation
    - Time-travel debugging
    - Capability-based security
    - Continuous profiling & optimization
    """
    
    def __init__(self, evaluator: Optional[Evaluator] = None):
        self.evaluator = evaluator or Evaluator()
        self.timetravel = TimeTravelRuntime(self.evaluator)
        self.capability = CapabilityRuntime(self.evaluator)
        self.compiler = IntentCompiler()
        self.intents: Dict[str, Intent] = {}
        self.functions: Dict[str, Callable] = {}
        self.profiles: Dict[str, List[Dict]] = {}
        self._optimization_enabled = True
        
        # Built-in fallback implementations
        self._fallbacks: Dict[str, Callable] = {}
    
    def declare_intent(self, intent: Intent) -> Intent:
        """Register an intent for a target function."""
        self.intents[intent.target] = intent
        return intent
    
    def register_fallback(self, name: str, fn: Callable):
        """Register a fallback implementation."""
        self._fallbacks[name] = fn
    
    def get_function(self, name: str) -> Optional[Callable]:
        return self.functions.get(name) or self._fallbacks.get(name)
    
    def compile_all(self):
        """Compile all declared intents."""
        for intent in self.intents.values():
            if intent.target in self.functions:
                optimized = self.compiler.compile(self.functions[intent.target], intent, self)
                self.functions[intent.target] = optimized
    
    def run(self, source: str, capabilities: Optional[List[Capability]] = None) -> Any:
        """Run code with intent compilation + capability sandboxing."""
        # Parse and evaluate
        from src.parser import Parser
        from src.lexer import Lexer
        
        tokens = Lexer(source, '<intent>').tokenize()
        ast = Parser(tokens).parse()
        
        # Apply capabilities if provided
        if capabilities:
            return self.capability.run_with_capabilities(source, capabilities)
        
        return self.evaluator.evaluate(ast)
    
    def profile(self, fn_name: str, args: tuple, kwargs: dict) -> Dict:
        """Profile a function execution."""
        if not self._optimization_enabled:
            return {}
        
        snap_before = self.timetravel.checkpoint(f"profile:{fn_name}:before")
        start = time.perf_counter()
        
        try:
            fn = self.functions.get(fn_name)
            if fn:
                result = fn(*args, **kwargs)
            else:
                result = None
        except Exception as e:
            raise
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            snap_after = self.timetravel.checkpoint(f"profile:{fn_name}:after")
            
            profile = {
                "fn": fn_name,
                "elapsed_ms": elapsed,
                "timestamp": time.time(),
                "args_hash": hash(str(args)[:100]),
            }
            
            if fn_name not in self.profiles:
                self.profiles[fn_name] = []
            self.profiles[fn_name].append(profile)
            
            # Check if we should re-optimize
            self._maybe_reoptimize(fn_name)
        
        return profile
    
    def _maybe_reoptimize(self, fn_name: str):
        """Check if function needs re-optimization based on profiles."""
        profiles = self.profiles.get(fn_name, [])
        if len(profiles) < 100:
            return
        
        recent = profiles[-100:]
        avg_latency = sum(p["elapsed_ms"] for p in recent) / len(recent)
        p95 = sorted(p["elapsed_ms"] for p in recent)[int(0.95 * len(recent))]
        
        intent = self.intents.get(fn_name)
        if intent and intent.intent_type == IntentType.PERFORMANCE:
            budget = intent.spec.get("budget_ms", 100)
            if p95 > budget * 1.2:  # 20% over budget
                self._trigger_reoptimization(fn_name, intent, p95)
    
    def _trigger_reoptimization(self, fn_name: str, intent: Intent, current_p95: float):
        """Trigger AI-driven re-optimization."""
        print(f"[IntentRuntime] Re-optimizing {fn_name}: p95={current_p95:.1f}ms > budget={intent.spec.get('budget_ms')}ms")
        # In full implementation, this would:
        # 1. Analyze time-travel traces for hot spots
        # 2. Generate alternative implementations
        # 3. A/B test in shadow mode
        # 4. Swap if better
    
    def explain(self, fn_name: str) -> str:
        """Generate natural language explanation of execution."""
        profiles = self.profiles.get(fn_name, [])
        if not profiles:
            return f"No execution data for {fn_name}"
        
        recent = profiles[-10:]
        avg = sum(p["elapsed_ms"] for p in recent) / len(recent)
        intent = self.intents.get(fn_name)
        
        explanation = f"Function '{fn_name}' "
        if intent:
            explanation += f"has intent: {intent.intent_type.value} "
            if intent.intent_type == IntentType.PERFORMANCE:
                explanation += f"(budget: {intent.spec.get('budget_ms')}ms). "
        
        explanation += f"Recent avg: {avg:.1f}ms over {len(recent)} runs. "
        
        if intent and intent.intent_type == IntentType.PERFORMANCE:
            budget = intent.spec.get("budget_ms", 100)
            if avg > budget:
                explanation += f"⚠️ OVER BUDGET by {avg - budget:.1f}ms. "
            else:
                explanation += f"✅ Within budget ({budget}ms). "
        
        return explanation


# =============================================================================
# Decorators for Easy Intent Declaration
# =============================================================================

def intent_performance(budget_ms: float = 100, percentile: float = 0.95, **kwargs):
    """Decorator: @intent_performance(budget_ms=200)"""
    def decorator(fn):
        intent = PerformanceIntent(
            name=fn.__name__,
            target=fn.__name__,
            budget_ms=budget_ms,
            percentile=percentile,
            **kwargs
        )
        # Store on function for later registration
        fn._zpx_intent = intent
        return fn
    return decorator


def intent_reliability(max_retries: int = 3, fallback: str = None, **kwargs):
    """Decorator: @intent_reliability(max_retries=5, fallback="safe_checkout")"""
    def decorator(fn):
        intent = ReliabilityIntent(
            name=fn.__name__,
            target=fn.__name__,
            max_retries=max_retries,
            fallback=fallback,
            **kwargs
        )
        fn._zpx_intent = intent
        return fn
    return decorator


def intent_security(capabilities: List[str] = None, **kwargs):
    """Decorator: @intent_security(capabilities=["fs_read", "db_users"])"""
    def decorator(fn):
        intent = SecurityIntent(
            name=fn.__name__,
            target=fn.__name__,
            capabilities=capabilities or [],
            **kwargs
        )
        fn._zpx_intent = intent
        return fn
    return decorator


def intent_cost(max_tokens: int = 10000, max_api_calls: int = 100, **kwargs):
    """Decorator: @intent_cost(max_tokens=5000)"""
    def decorator(fn):
        intent = CostIntent(
            name=fn.__name__,
            target=fn.__name__,
            max_tokens=max_tokens,
            max_api_calls=max_api_calls,
            **kwargs
        )
        fn._zpx_intent = intent
        return fn
    return decorator


# =============================================================================
# Example Usage / Demo
# =============================================================================

def demo():
    """Demonstrate intent-based runtime."""
    rt = IntentRuntime()
    
    # Register some functions
    def checkout(cart, user):
        # Simulate payment processing
        time.sleep(0.05)
        return {"status": "ok", "order_id": "12345"}
    
    def safe_checkout(cart, user):
        # Fallback: queue for manual processing
        return {"status": "queued", "order_id": "queue_12345"}
    
    rt.functions["checkout"] = checkout
    rt.register_fallback("safe_checkout", safe_checkout)
    
    # Declare intents
    perf_intent = PerformanceIntent(
        name="checkout_fast",
        target="checkout",
        budget_ms=50,  # Tight budget!
    )
    rt.declare_intent(perf_intent)
    
    rel_intent = ReliabilityIntent(
        name="checkout_reliable",
        target="checkout",
        max_retries=3,
        fallback="safe_checkout",
    )
    rt.declare_intent(rel_intent)
    
    # Compile (applies retry + cache strategies)
    rt.compile_all()
    
    # Run with profiling
    for i in range(5):
        rt.profile("checkout", ({"item": "widget"}, {"id": "user1"}), {})
    
    print("Explanation:", rt.explain("checkout"))
    print("Compiled:", "checkout" in rt.compiler.compiled)
    
    # Test with capabilities
    fs_cap = rt.capability.capability("filesystem", read=["/tmp"], write=["/tmp"])
    result = rt.run('print("hello from capability sandbox")', capabilities=[fs_cap])
    print("Capability run:", result)


if __name__ == "__main__":
    demo()