"""Real LLM benchmark runner - calls actual LLM APIs to generate and test code."""

import os
import json
import asyncio
import time
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import argparse

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class BenchmarkTask:
    id: str
    name: str
    description: str
    spec: str
    tests: List[Dict[str, Any]]
    category: str
    difficulty: str


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
    generated_code: str
    test_output: str
    error: Optional[str] = None


# LLM Provider Abstraction
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, model: str, temperature: float = 0.1) -> Dict[str, Any]:
        """Returns: {'text': str, 'tokens': int, 'cost_usd': float, 'latency_ms': float}"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = None
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            print(f"OpenAI not available: {e}")
    
    @property
    def name(self) -> str:
        return "openai"
    
    async def generate(self, prompt: str, model: str, temperature: float = 0.1) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        
        start = time.time()
        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert programmer. Output ONLY the code, no explanations."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=2000,
        )
        latency = (time.time() - start) * 1000
        
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens
        
        # Rough cost estimation (update with actual pricing)
        pricing = {
            "gpt-4o": {"input": 5.00, "output": 15.00},  # per 1M tokens
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        }
        p = pricing.get(model, {"input": 1.0, "output": 2.0})
        cost = (response.usage.prompt_tokens * p["input"] + response.usage.completion_tokens * p["output"]) / 1_000_000
        
        return {
            "text": text,
            "tokens": tokens,
            "cost_usd": cost,
            "latency_ms": latency,
        }


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.client = None
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        except Exception as e:
            print(f"Anthropic not available: {e}")
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    async def generate(self, prompt: str, model: str, temperature: float = 0.1) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")
        
        start = time.time()
        response = await self.client.messages.create(
            model=model,
            max_tokens=2000,
            temperature=temperature,
            system="You are an expert programmer. Output ONLY the code, no explanations.",
            messages=[{"role": "user", "content": prompt}],
        )
        latency = (time.time() - start) * 1000
        
        text = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens
        
        pricing = {
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        }
        p = pricing.get(model, {"input": 1.0, "output": 3.0})
        cost = (response.usage.input_tokens * p["input"] + response.usage.output_tokens * p["output"]) / 1_000_000
        
        return {
            "text": text,
            "tokens": tokens,
            "cost_usd": cost,
            "latency_ms": latency,
        }


class GoogleProvider(LLMProvider):
    def __init__(self):
        self.client = None
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self.client = genai.GenerativeModel("gemini-1.5-flash")
        except Exception as e:
            print(f"Google not available: {e}")
    
    @property
    def name(self) -> str:
        return "google"
    
    async def generate(self, prompt: str, model: str, temperature: float = 0.1) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Google client not initialized")
        
        start = time.time()
        response = await self.client.generate_content_async(
            prompt,
            generation_config={"temperature": temperature, "max_output_tokens": 2000},
        )
        latency = (time.time() - start) * 1000
        
        text = response.text
        # Google doesn't always return token counts in free tier
        tokens = len(text.split()) * 1.3  # rough estimate
        
        return {
            "text": text,
            "tokens": int(tokens),
            "cost_usd": 0.0,  # Free tier
            "latency_ms": latency,
        }


# Language-specific prompts
LANGUAGE_PROMPTS = {
    "zpx": """Write Zpx code to solve this task. Use Zpx syntax:
- fn for functions, ret for return
- let for variables, el: for else
- |> for pipe operator
- Contracts: @requires, @ensures
- Implicit returns (last expression)
- No semicolons, 2-space indentation

Task: {spec}

Tests to pass:
{tests}

Output ONLY the .zpx code:""",
    
    "python": """Write Python code to solve this task. Use type hints where appropriate.

Task: {spec}

Tests to pass:
{tests}

Output ONLY the .py code:""",
    
    "typescript": """Write TypeScript code to solve this task. Use modern ES features and type safety.

Task: {spec}

Tests to pass:
{tests}

Output ONLY the .ts code:""",
}

# Test runners for each language
LANGUAGE_RUNNERS = {
    "zpx": ["python", "-m", "src.cli", "run"],
    "python": ["python"],
    "typescript": ["tsx"],  # or npx ts-node
}

LANGUAGE_EXTENSIONS = {
    "zpx": ".zpx",
    "python": ".py",
    "typescript": ".ts",
}


def load_tasks() -> List[BenchmarkTask]:
    """Load benchmark tasks from YAML."""
    import yaml
    tasks_path = Path(__file__).parent / "tasks.yaml"
    with open(tasks_path) as f:
        data = yaml.safe_load(f)
    
    tasks = []
    for t in data.get("tasks", []):
        tasks.append(BenchmarkTask(
            id=t["id"],
            name=t["name"],
            description=t["description"],
            spec=t["spec"],
            tests=t["tests"],
            category=t.get("category", "general"),
            difficulty=t.get("difficulty", "medium"),
        ))
    return tasks


def format_tests(tests: List[Dict]) -> str:
    """Format tests for prompt."""
    lines = []
    for i, test in enumerate(tests):
        if "input" in test and "expected" in test:
            lines.append(f"  Test {i+1}: {test['input']} => {test['expected']}")
        elif "code" in test:
            lines.append(f"  Test {i+1}: {test['code']}")
    return "\n".join(lines)


async def run_task(
    task: BenchmarkTask,
    language: str,
    model: str,
    provider: LLMProvider,
    run: int,
) -> BenchmarkResult:
    """Run a single benchmark task."""
    # Build prompt
    prompt = LANGUAGE_PROMPTS[language].format(
        spec=task.spec,
        tests=format_tests(task.tests),
    )
    
    # Generate code
    try:
        gen_result = await provider.generate(prompt, model)
        code = gen_result["text"].strip()
        
        # Clean up markdown code blocks if present
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            code = "\n".join(lines)
        
    except Exception as e:
        return BenchmarkResult(
            task_id=task.id,
            language=language,
            model=model,
            run=run,
            passed=False,
            total_tokens=0,
            latency_ms=0,
            cost_usd=0,
            generated_code="",
            test_output="",
            error=f"Generation failed: {e}",
        )
    
    # Write code to temp file and run tests
    passed = False
    test_output = ""
    
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=LANGUAGE_EXTENSIONS[language],
            delete=False,
        ) as f:
            f.write(code)
            temp_path = f.name
        
        # Run the code
        runner = LANGUAGE_RUNNERS[language] + [temp_path]
        result = subprocess.run(
            runner,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent,
        )
        test_output = result.stdout + result.stderr
        
        # Check if tests pass (simplified - look for expected outputs)
        # In practice, you'd run actual test framework
        passed = result.returncode == 0
        for test in task.tests:
            if "expected" in test and test["expected"] not in result.stdout:
                passed = False
                break
                
    except subprocess.TimeoutExpired:
        test_output = "TIMEOUT"
        passed = False
    except Exception as e:
        test_output = f"ERROR: {e}"
        passed = False
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass
    
    return BenchmarkResult(
        task_id=task.id,
        language=language,
        model=model,
        run=run,
        passed=passed,
        total_tokens=gen_result["tokens"],
        latency_ms=gen_result["latency_ms"],
        cost_usd=gen_result["cost_usd"],
        generated_code=code,
        test_output=test_output,
        error=None if passed else "Tests failed",
    )


async def run_benchmarks(
    tasks: List[BenchmarkTask],
    languages: List[str],
    models: Dict[str, List[str]],  # provider -> models
    runs_per_task: int = 3,
) -> List[BenchmarkResult]:
    """Run all benchmarks."""
    providers = {
        "openai": OpenAIProvider(),
        "anthropic": AnthropicProvider(),
        "google": GoogleProvider(),
    }
    
    # Filter available providers
    available_providers = {k: v for k, v in providers.items() if v.client is not None}
    if not available_providers:
        print("No LLM providers available! Set API keys.")
        return []
    
    results = []
    
    for task in tasks:
        for language in languages:
            for provider_name, model_list in models.items():
                if provider_name not in available_providers:
                    print(f"Skipping {provider_name} - not available")
                    continue
                
                provider = available_providers[provider_name]
                for model in model_list:
                    for run in range(runs_per_task):
                        print(f"Running: {task.id} | {language} | {model} | run {run+1}/{runs_per_task}")
                        result = await run_task(task, language, model, provider, run)
                        results.append(result)
                        status = "✓" if result.passed else "✗"
                        print(f"  {status} tokens={result.total_tokens} latency={result.latency_ms:.0f}ms cost=${result.cost_usd:.4f}")
    
    return results


def save_results(results: List[BenchmarkResult], output_path: str):
    """Save results to JSON."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\nResults saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Run LLM code generation benchmarks")
    parser.add_argument("--tasks", nargs="+", help="Task IDs to run")
    parser.add_argument("--languages", nargs="+", default=["zpx", "python", "typescript"])
    parser.add_argument("--models", nargs="+", default=["gpt-4o-mini"])
    parser.add_argument("--provider", default="openai", choices=["openai", "anthropic", "google"])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", default="benchmarks/results.json")
    args = parser.parse_args()
    
    # Load tasks
    all_tasks = load_tasks()
    if args.tasks:
        tasks = [t for t in all_tasks if t.id in args.tasks]
    else:
        tasks = all_tasks
    
    print(f"Loaded {len(tasks)} tasks")
    print(f"Languages: {args.languages}")
    print(f"Models: {args.models} (provider: {args.provider})")
    print(f"Runs per task: {args.runs}")
    print()
    
    # Map models to provider
    models = {args.provider: args.models}
    
    # Run benchmarks
    results = asyncio.run(run_benchmarks(
        tasks=tasks,
        languages=args.languages,
        models=models,
        runs_per_task=args.runs,
    ))
    
    save_results(results, args.output)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    by_lang = {}
    for r in results:
        by_lang.setdefault(r.language, []).append(r)
    
    for lang, res in sorted(by_lang.items()):
        passed = sum(1 for r in res if r.passed)
        total = len(res)
        avg_tokens = sum(r.total_tokens for r in res) / total
        avg_latency = sum(r.latency_ms for r in res) / total
        total_cost = sum(r.cost_usd for r in res)
        print(f"\n{lang.upper()}: {passed}/{total} passed ({100*passed/total:.1f}%)")
        print(f"  Avg tokens: {avg_tokens:.0f}")
        print(f"  Avg latency: {avg_latency:.0f}ms")
        print(f"  Total cost: ${total_cost:.4f}")
    
    # ZPX vs others
    if "zpx" in by_lang and "python" in by_lang:
        zpx_tokens = sum(r.total_tokens for r in by_lang["zpx"]) / len(by_lang["zpx"])
        py_tokens = sum(r.total_tokens for r in by_lang["python"]) / len(by_lang["python"])
        reduction = (1 - zpx_tokens / py_tokens) * 100
        print(f"\n📊 ZPX token reduction vs Python: {reduction:.1f}%")


if __name__ == "__main__":
    main()