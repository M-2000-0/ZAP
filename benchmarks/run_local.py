#!/usr/bin/env python3
"""
Simple local benchmark runner - generates mock results to demonstrate the framework.
No API keys required.
"""

import json
import random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict
import argparse


@dataclass
class BenchmarkResult:
    task_id: str
    language: str
    model: str
    run: int
    passed: bool
    total_tokens: int
    latency_ms: float
    cost_usd: float
    generated_code: str = ""
    test_output: str = ""
    error: str = ""


# Realistic mock data based on ZPX design principles
TASKS = {
    "fibonacci": {"desc": "Recursive fibonacci with memoization"},
    "fizzbuzz": {"desc": "Classic FizzBuzz"},
    "rest_api": {"desc": "REST API with CRUD endpoints"},
    "data_pipeline": {"desc": "ETL data processing pipeline"},
    "react_component": {"desc": "React component with hooks"},
    "sql_query": {"desc": "Complex SQL query with joins"},
    "html_rendering": {"desc": "HTML template rendering"},
    "async_concurrent": {"desc": "Async concurrent task processing"},
    "schema_validation": {"desc": "Data validation with schemas"},
    "fullstack_app": {"desc": "Full-stack application"},
}

# Expected token counts per task per language (based on ZPX token efficiency claims)
TOKEN_ESTIMATES = {
    "fibonacci":     {"zpx": 42,  "python": 78,  "typescript": 92},
    "fizzbuzz":      {"zpx": 35,  "python": 58,  "typescript": 68},
    "rest_api":      {"zpx": 115, "python": 265, "typescript": 310},
    "data_pipeline": {"zpx": 88,  "python": 165, "typescript": 195},
    "react_component": {"zpx": 95,  "python": 0,   "typescript": 165},  # Python N/A
    "sql_query":     {"zpx": 62,  "python": 135, "typescript": 155},
    "html_rendering": {"zpx": 78,  "python": 148, "typescript": 135},
    "async_concurrent": {"zpx": 72,  "python": 142, "typescript": 125},
    "schema_validation": {"zpx": 52,  "python": 122, "typescript": 142},
    "fullstack_app": {"zpx": 265, "python": 495, "typescript": 570},
}

# Pass rates per language (ZPX designed for LLM generation)
PASS_RATES = {
    "zpx": 0.88,
    "python": 0.80,
    "typescript": 0.82,
}


def run_mock_benchmarks(
    task_ids: List[str] = None,
    languages: List[str] = None,
    models: List[str] = None,
    runs_per_task: int = 3,
) -> List[BenchmarkResult]:
    """Generate realistic mock benchmark results."""
    
    tasks = task_ids or list(TASKS.keys())
    langs = languages or ["zpx", "python", "typescript"]
    model_list = models or ["gpt-4o-mini", "claude-3-haiku", "gemini-1.5-flash"]
    
    results = []
    
    for task_id in tasks:
        if task_id not in TOKEN_ESTIMATES:
            print(f"Unknown task: {task_id}, skipping")
            continue
            
        task_tokens = TOKEN_ESTIMATES[task_id]
        
        for lang in langs:
            if lang not in task_tokens or task_tokens[lang] == 0:
                continue  # Not applicable (e.g., React in Python)
                
            base_tokens = task_tokens[lang]
            pass_rate = PASS_RATES.get(lang, 0.75)
            
            for model in model_list:
                for run in range(runs_per_task):
                    # Add variance
                    tokens = int(base_tokens * random.uniform(0.85, 1.15))
                    passed = random.random() < pass_rate * random.uniform(0.9, 1.1)
                    latency = random.uniform(800, 4000)
                    
                    # Cost estimation (input: $0.15/M, output: $0.60/M for gpt-4o-mini)
                    cost = (tokens * 0.7 * 0.15 + tokens * 0.3 * 0.60) / 1_000_000
                    
                    result = BenchmarkResult(
                        task_id=task_id,
                        language=lang,
                        model=model,
                        run=run,
                        passed=passed,
                        total_tokens=tokens,
                        latency_ms=latency,
                        cost_usd=cost,
                        generated_code=f"# {lang} code for {task_id}",
                        test_output="PASS" if passed else "FAIL: assertion error",
                        error=None if passed else "Test assertion failed",
                    )
                    results.append(result)
                    
                    status = "PASS" if passed else "FAIL"
                    print(f"  {status} {task_id:20s} [{lang:10s}/{model}] run {run+1}: {tokens:4d} tokens, {latency:6.0f}ms")
    
    return results


def print_summary(results: List[BenchmarkResult]):
    """Print formatted benchmark summary."""
    if not results:
        print("No results")
        return
        
    # Group by language
    by_lang: Dict[str, List[BenchmarkResult]] = {}
    for r in results:
        by_lang.setdefault(r.language, []).append(r)
    
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"{'Language':<12} {'Pass Rate':>10} {'Avg Tokens':>12} {'Avg Latency':>12} {'Total Cost':>10}")
    print("-" * 70)
    
    for lang, res in sorted(by_lang.items()):
        passed = sum(1 for r in res if r.passed)
        total = len(res)
        pass_rate = 100 * passed / total
        avg_tokens = sum(r.total_tokens for r in res) / total
        avg_latency = sum(r.latency_ms for r in res) / total
        total_cost = sum(r.cost_usd for r in res)
        
        print(f"{lang:<12} {pass_rate:>9.1f}% {avg_tokens:>11.0f} {avg_latency:>11.0f}ms ${total_cost:>9.4f}")
    
    # ZPX vs Python comparison
    if "zpx" in by_lang and "python" in by_lang:
        zpx_tokens = sum(r.total_tokens for r in by_lang["zpx"]) / len(by_lang["zpx"])
        py_tokens = sum(r.total_tokens for r in by_lang["python"]) / len(by_lang["python"])
        reduction = (1 - zpx_tokens / py_tokens) * 100
        print("-" * 70)
        print(f"ZPX token reduction vs Python: {reduction:.1f}%")
        print(f"  ZPX avg: {zpx_tokens:.0f} tokens")
        print(f"  Python avg: {py_tokens:.0f} tokens")
    
    # ZPX vs TypeScript
    if "zpx" in by_lang and "typescript" in by_lang:
        zpx_tokens = sum(r.total_tokens for r in by_lang["zpx"]) / len(by_lang["zpx"])
        ts_tokens = sum(r.total_tokens for r in by_lang["typescript"]) / len(by_lang["typescript"])
        reduction = (1 - zpx_tokens / ts_tokens) * 100
        print(f"ZPX token reduction vs TypeScript: {reduction:.1f}%")
        print(f"  ZPX avg: {zpx_tokens:.0f} tokens")
        print(f"  TypeScript avg: {ts_tokens:.0f} tokens")
    
    # Overall pass rates
    print("-" * 70)
    overall_passed = sum(1 for r in results if r.passed)
    overall_total = len(results)
    print(f"Overall: {overall_passed}/{overall_total} passed ({100*overall_passed/overall_total:.1f}%)")


def save_results(results: List[BenchmarkResult], output: str):
    """Save results to JSON file."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\nResults saved to {output}")


def main():
    parser = argparse.ArgumentParser(description="Run local mock LLM benchmarks")
    parser.add_argument("--tasks", nargs="+", help="Task IDs to run")
    parser.add_argument("--languages", nargs="+", default=["zpx", "python", "typescript"])
    parser.add_argument("--models", nargs="+", default=["gpt-4o-mini", "claude-3-haiku"])
    parser.add_argument("--runs", type=int, default=3, help="Runs per task per language per model")
    parser.add_argument("--output", default="benchmarks/results.json")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()
    
    random.seed(args.seed)
    
    print(f"Running mock benchmarks (seed={args.seed})")
    print(f"Tasks: {args.tasks or 'all'}")
    print(f"Languages: {args.languages}")
    print(f"Models: {args.models}")
    print(f"Runs per combination: {args.runs}")
    print()
    
    results = run_mock_benchmarks(
        task_ids=args.tasks,
        languages=args.languages,
        models=args.models,
        runs_per_task=args.runs,
    )
    
    print_summary(results)
    save_results(results, args.output)


if __name__ == "__main__":
    main()