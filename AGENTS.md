# AGENTS.md

## Purpose
This repository is a local LLM orchestration project for small models.
Favor stability, simplicity, and debuggability over theoretical elegance.

## Working style
- Prefer small, incremental refactors over large rewrites.
- Do not introduce unnecessary abstractions.
- Remove complexity when possible instead of layering more logic on top.
- Keep the project structure recognizable unless explicitly asked to reorganize it.

## Model / prompt philosophy
- Small local models are fragile.
- Keep SYSTEM prompts extremely short.
- Put most task-specific instructions in USER prompts.
- Prefer fixed-label schemas over markdown-heavy formatting.
- Favor simple output forms such as:
  - `TASK:`
  - `GOAL:`
  - `CONSTRAINTS:`
  - `SCRATCH:`
  - `RESULT:`
- Each stage should do one thing only.

## Current pipeline direction
The preferred main path is:

1. app-side language detection
2. normalize
3. thinking
4. finalize

### Stage responsibilities
- **normalize**: convert Japanese-like input into a compact English task memo
- **thinking**: reasoning only
- **finalize**: produce the final natural Japanese answer

### Avoid
- LLM-based routing for simple deterministic decisions
- overloading a single stage with multiple responsibilities
- prompt pollution with unrelated runtime/tool/platform details
- adding new facts in the finalizer
- exposing scratch reasoning to the final user

## Code change expectations
- Preserve public APIs unless a change is clearly necessary.
- Preserve payload schemas unless explicitly asked to redesign them.
- Do not redesign MCP interfaces unless explicitly requested.
- Do not redesign analyzer features unless explicitly requested.
- Keep baton / stream behavior intact unless explicitly requested to change it.
- Minimize behavior changes outside the target area of the task.

## File-specific guidance
- `src/agents/*.py`
  - prompt builders should stay simple, explicit, and schema-driven
  - avoid long explanatory prompt text
- `src/orchestrator/engine.py`
  - keep orchestration readable
  - prefer small helper methods over one giant function
  - do not add architectural complexity unless explicitly requested

## Verification
After making changes, run:

```bash
python3 -m py_compile src/main.py src/orchestrator/engine.py src/agents/*.py src/agents/__init__.py
````

If a task is specifically about runtime behavior, also run the smallest relevant smoke test instead of broad unnecessary testing.

## Commits

You may create commits when appropriate.

Every commit MUST:

* use a clear and descriptive commit message
* explain what changed
* explain why the change was made

Avoid vague commit messages such as:

* `update`
* `fix`
* `changes`
* `misc`

## When uncertain

If there is a tradeoff between:

* cleaner architecture
* more stable behavior for 1.2B local models

prefer the more stable behavior unless the task explicitly asks for architectural cleanup.

