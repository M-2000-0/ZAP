# Zap Completion Plan

This document captures the roadmap and implementation plan for making Zap a complete, launch-ready programming language.

## Vision

Zap aims to be a modern, AI-native programming language that can build:

- interactive frontend and visual applications
- production-ready backend services
- secure, auditable systems
- AI-first development workflows and tooling
- a strong open-source ecosystem

## What "finished" means for Zap

Zap is finished when it has:

1. A stable, documented core language with predictable runtime behavior.
2. A full-featured CLI and developer workflow.
3. A frontend visual/runtime target for UI and graphics.
4. A backend service platform with networking, data, and auth.
5. A security model for safe execution and permissions.
6. AI-native language constructs, diagnostics, and test support.
7. Packages, docs, examples, and editor integration.

## Current strengths in this repo

- Working CLI scaffold for `run`, `check`, `build`, `test`, `compile`, `repl`, `version`, `diag`
- Interpreter and parser architecture in `src/`
- Diagnostics and version/grammar validation logic
- Test runner proof-of-concept in `src/test_runner.py`
- Example Zap programs in `examples/`

## High-level implementation areas

### 1. Core language and runtime
- Finalize syntax for functions, control flow, data structures, modules, classes, `expect`, and `check`
- Harden evaluator semantics for return values, scope, errors, and concurrency
- Add runtime features for async, promises/futures, and effect management
- Build formal language docs and grammar reference

### 2. CLI and developer tooling
- Complete and test CLI commands:
  - `zap run`
  - `zap check`
  - `zap build`
  - `zap test`
  - `zap compile`
  - `zap repl`
  - `zap version`
  - `zap diag`
- Add formatter, linter, and language server integration
- Implement package/story support if needed for module resolution

### 3. Frontend / visuals
- Define a frontend runtime or browser compilation target
- Add core visual primitives for UI, layout, and drawing
- Ship a minimal sample app that renders in a browser or GUI runtime
- Integrate standard interactivity and event handling

### 4. Backend / services
- Add HTTP routing and API endpoint support
- Add database access and modeling primitives
- Add authentication/authorization and permission declarations
- Add job scheduling, messaging, and background execution

### 5. Security and permissions
- Design a permission model for filesystem, network, external API, and host access
- Enforce safe defaults for sandboxed execution
- Add auditing, logging, and runtime policy checks

### 6. AI-first features
- Add intent and contract syntax such as `intend`, `requires`, `ensures`, and `expect`
- Build model integration primitives for prompt-driven workflows
- Improve diagnostics for AI-generated code and semantic failures
- Add test-generation and validation helpers for generated code

### 7. Ecosystem and launch readiness
- Produce core package structure and documentation
- Add starter templates and examples for frontend/backend/AI
- Create onboarding guides and quickstart tutorials
- Publish release notes, changelog, and roadmap

## Concrete milestones

### Milestone 1: Stable language core
- [ ] Finish interpreter semantics for return, block, function, and control-flow execution
- [ ] Add formal grammar and parser coverage for new keywords
- [ ] Stabilize `src/version.py` and grammar pragma handling
- [ ] Expand unit tests for parser, evaluator, and CLI

### Milestone 2: Reliable CLI + tests
- [ ] Finalize `src/test_runner.py` and CLI `zap test`
- [ ] Add JSON output support for test and diagnostics
- [ ] Expand `pytest` coverage to include CLI commands and sample program checks
- [ ] Add `tests/conftest.py` and CLI fixtures for isolation

### Milestone 3: Compiler and runtime packaging
- [ ] Harden `src/compiler.py` or replace with a real compile backend
- [ ] Add support for caching or compiled output with safe invalidation
- [ ] Ensure `zap compile` works reliably across examples

### Milestone 4: Frontend/visual runtime
- [ ] Define a visual runtime target or browser backend
- [ ] Implement core UI primitives or a DOM-like API
- [ ] Ship a demo visual app in `examples/`

### Milestone 5: Backend features
- [ ] Add HTTP/API and service abstractions
- [ ] Add database and persistence integration
- [ ] Add permission and auth primitives for backend code

### Milestone 6: Security and AI tooling
- [ ] Add runtime permission enforcement
- [ ] Add secure defaults and sandboxing helpers
- [ ] Add AI coding helpers and diagnostics support

### Milestone 7: Release and ecosystem
- [ ] Write docs and examples
- [ ] Add packaging and install instructions
- [ ] Publish release notes and roadmap

## Immediate implementation plan

Start with these concrete tasks in the repo:

1. Review and finalize `src/test_runner.py` behavior for all supported assertion forms.
2. Harden `src/evaluator.py` return propagation and block handling.
3. Add more tests for CLI commands and example Zap programs.
4. Improve `src/compiler.py` to emit stable, reusable output and to avoid generated artifacts in source.
5. Define `instructions.md` as the authoritative launch checklist.

## How we use this file

- Treat this document as the master launch checklist.
- Update it after each milestone with progress and new requirements.
- Use it to prioritize repo development and GitHub issues.
