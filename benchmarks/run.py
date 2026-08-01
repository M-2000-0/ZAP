#!/usr/bin/env python3
"""
LLM Code Generation Benchmark Runner

Runs coding tasks across multiple languages and measures:
- Token count (prompt + completion)
- Correctness (passes tests)
- Latency
- Cost estimate
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import yaml
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib


@dataclass
class BenchmarkResult:
    task_id: str
    language: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    passed: bool
    output: str
    error: Optional[str] = None
    cost_usd: float = 0.0


@dataclass
class Task:
    id: str
    name: str
    description: str
    category: str
    difficulty: str
    spec: str
    tests: List[Dict[str, Any]]


class BenchmarkRunner:
    def __init__(self, config_path: str = "benchmarks/tasks.yaml"):
        with open(config_path) as f:
            data = yaml.safe_load(f)
        self.tasks = [Task(**t) for t in data["tasks"]]
        self.results: List[BenchmarkResult] = []
        
    def build_prompt(self, task: Task, language: str) -> str:
        """Build the prompt for a specific task and language."""
        lang_configs = {
            "zpx": {
                "ext": ".zpx",
                "runner": "python -m src.cli run",
                "style": "Use ZPX syntax: fn, ret, el, let, requires/ensures contracts, concurrent blocks, check blocks, expect assertions",
            },
            "python": {
                "ext": ".py",
                "runner": "python",
                "style": "Use Python 3.11+ with type hints. Include if __name__ == '__main__': block.",
            },
            "typescript": {
                "ext": ".ts",
                "runner": "npx tsx",
                "style": "Use TypeScript with strict types. Include async/await. Run with tsx.",
            },
        }
        
        cfg = lang_configs.get(language, lang_configs["python"])
        
        return f"""You are an expert {language} programmer. Write a complete, runnable {language} program that solves this task.

TASK: {task.name}
DESCRIPTION: {task.description}
SPECIFICATION:
{task.spec}

REQUIREMENTS:
- Language: {language}
- Style: {cfg['style']}
- The code must be a single file that runs with: {cfg['runner']} <filename>
- Include all necessary imports
- Handle errors appropriately
- Add a main entry point that demonstrates the functionality

OUTPUT FORMAT: Return ONLY the code, no markdown, no explanation."""

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        return len(text) // 4

    async def run_llm_generation(self, prompt: str, model: str) -> tuple[str, int, int, float]:
        """Call LLM API and return (completion, prompt_tokens, completion_tokens, latency_ms)."""
        # This is a placeholder - in real usage, you'd call OpenAI/Anthropic/etc.
        # For now, we'll use a mock or local model
        start = time.time()
        
        # Check if we have API keys
        if model.startswith("gpt-") and os.getenv("OPENAI_API_KEY"):
            return await self._call_openai(prompt, model)
        elif model.startswith("claude-") and os.getenv("ANTHROPIC_API_KEY"):
            return await self._call_anthropic(prompt, model)
        else:
            # Mock for testing without API keys
            await asyncio.sleep(0.1)
            latency = (time.time() - start) * 1000
            return f"# Mock completion for {model}\nprint('hello')", 100, 20, latency

    async def _call_openai(self, prompt: str, model: str) -> tuple[str, int, int, float]:
        import openai
        client = openai.AsyncOpenAI()
        start = time.time()
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4096,
        )
        latency = (time.time() - start) * 1000
        return (
            response.choices[0].message.content or "",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            latency,
        )

    async def _call_anthropic(self, prompt: str, model: str) -> tuple[str, int, int, float]:
        import anthropic
        client = anthropic.AsyncAnthropic()
        start = time.time()
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        latency = (time.time() - start) * 1000
        # Anthropic doesn't return token counts in same way, estimate
        text = response.content[0].text if response.content else ""
        return text, self.estimate_tokens(prompt), self.estimate_tokens(text), latency

    def run_code(self, code: str, language: str, timeout: int = 30) -> tuple[str, bool, Optional[str]]:
        """Execute code and return (output, success, error)."""
        lang_configs = {
            "zpx": {"ext": ".zpx", "cmd": ["python", "-m", "src.cli", "run"]},
            "python": {"ext": ".py", "cmd": ["python"]},
            "typescript": {"ext": ".ts", "cmd": ["npx", "tsx"]},
        }
        cfg = lang_configs.get(language)
        if not cfg:
            return "", False, f"Unknown language: {language}"

        with tempfile.NamedTemporaryFile(mode="w", suffix=cfg["ext"], delete=False) as f:
            f.write(code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                cfg["cmd"] + [tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path(__file__).parent.parent,
            )
            output = result.stdout.strip()
            success = result.returncode == 0
            error = result.stderr.strip() if not success else None
            return output, success, error
        except subprocess.TimeoutExpired:
            return "", False, f"Timeout after {timeout}s"
        except Exception as e:
            return "", False, str(e)
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

    def run_tests(self, code: str, task: Task, language: str) -> bool:
        """Run task-specific tests against the generated code."""
        # For now, just run the code and check it doesn't error
        # In a full implementation, you'd run the specific test cases
        output, success, error = self.run_code(code, language)
        return success

    async def run_task(self, task: Task, language: str, model: str) -> BenchmarkResult:
        """Run a single task-language-model combination."""
        prompt = self.build_prompt(task, language)
        prompt_tokens = self.estimate_tokens(prompt)
        
        completion, actual_prompt_tokens, completion_tokens, latency = await self.run_llm_generation(prompt, model)
        
        passed = False
        error = None
        output = ""
        
        if completion.strip():
            passed = self.run_tests(completion, task, language)
            output, _, error = self.run_code(completion, language)
        
        total_tokens = actual_prompt_tokens + completion_tokens
        cost = self.estimate_cost(model, actual_prompt_tokens, completion_tokens)
        
        return BenchmarkResult(
            task_id=task.id,
            language=language,
            model=model,
            prompt_tokens=actual_prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency,
            passed=passed,
            output=output[:500] if output else "",
            error=error,
            cost_usd=cost,
        )

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost in USD (rough 2024 prices)."""
        pricing = {
            "gpt-4o": (5.00, 15.00),      # per 1M tokens
            "gpt-4o-mini": (0.15, 0.60),
            "claude-3-5-sonnet": (3.00, 15.00),
            "claude-3-haiku": (0.25, 1.25),
        }
        rates = pricing.get(model, (0, 0))
        return (prompt_tokens * rates[0] + completion_tokens * rates[1]) / 1_000_000

    async def run_benchmark(
        self,
        languages: List[str] = ["zpx", "python", "typescript"],
        models: List[str] = ["gpt-4o-mini"],
        tasks_filter: Optional[List[str]] = None,
    ) -> List[BenchmarkResult]:
        """Run full benchmark suite."""
        tasks = self.tasks
        if tasks_filter:
            tasks = [t for t in tasks if t.id in tasks_filter]

        print(f"Running {len(tasks)} tasks x {len(languages)} languages x {len(models)} models")
        
        for task in tasks:
            for lang in languages:
                for model in models:
                    print(f"  {task.id} / lang }/{ model }...", end=" ", flush=True)
                    result = await self.run_task(task, lang, model)
                    self.results.append(result)
                    status = "✓" if result.passed else "✗"
                    print(f"{status} ({result.total_tokens} tokens, {result.latency_ms:.0f}ms)")
        
        return self.results

    def save_results(self, path: str):
        """Save results to JSON."""
        with open(path, "w") as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)

    def print_summary(self):
        """Print benchmark summary."""
        if not self.results:
            print("No results")
            return

        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)
        
        # Group by language
        by_lang: Dict[str, List[BenchmarkResult]] = {}
        for r in self.results:
            by_lang.setdefault(r.language, []).append(r)

        for lang, results in by_lang.items():
            passed = sum(1 for r in results if r.passed)
            total = len(results)
            avg_tokens = sum(r.total_tokens for r in results) / total if total else 0
            avg_latency = sum(r.latency_ms for r in results) / total if total else 0
            total_cost = sum(r.cost_usd for r in results)
            
            print(f"\n{lang.upper()}: {passed}/{total} passed")
            print(f"  Avg tokens: {avg_tokens:.0f}")
            print(f"  Avg latency: {avg_latency:.0f}ms")
            print(f"  Est. cost: ${total_cost:.4f}")

        # Token comparison: ZPX vs others
        if "zpx" in by_lang and "python" in by_lang:
            zpx_tokens = sum(r.total_tokens for r in by_lang["zpx"]) / len(by_lang["zpx"])
            py_tokens = sum(r.total_tokens for r in by_lang["python"]) / len(by_lang["python"])
            if py_tokens > 0:
                reduction = (1 - zpx_tokens / py_tokens) * 100
                print(f"\nZPX vs Python token reduction: {reduction:.1f}%")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run LLM code generation benchmarks")
    parser.add_argument("--languages", nargs="+", default=["zpx", "python", "typescript"])
    parser.add_argument("--models", nargs="+", default=["gpt-4o-mini"])
    parser.add_argument("--tasks", nargs="+", help="Specific task IDs to run")
    parser.add_argument("--output", default="benchmarks/results.json")
    args = parser.parse_args()

    runner = BenchmarkRunner()
    await runner.run_benchmark(
        languages=args.languages,
        models=args.models,
        tasks_filter=args.tasks,
    )
    runner.save_results(args.output)
    runner.print_summary()


if __name__ == "__main__":
    asyncio.run(main())