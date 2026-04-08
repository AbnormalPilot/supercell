# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

SUPERCELL is an OpenEnv-compliant reinforcement learning environment where an AI agent prioritizes landing order for incoming flights under fuel, weather, and emergency constraints. It consists of a Python FastAPI backend (the RL environment) and a Next.js dashboard (visualization).

## Commands

### Python (uv)
```bash
uv sync                              # Install dependencies
uv run python -m server.app          # Start environment server on :8000
uv run python -m pytest tests/ -v    # Run all tests
uv run python -m pytest tests/test_server.py::TestStepEndpoint::test_step_returns_200 -v  # Single test
uv run python inference.py           # Run baseline LLM inference (needs OPENAI_API_KEY)
```

### Node.js (pnpm + Turborepo)
```bash
pnpm install                         # Install monorepo dependencies
pnpm dev:web                         # Start Next.js dashboard on :3000 (Turbopack)
pnpm build:web                       # Static export to apps/web/out/
```

### Docker
```bash
docker compose up                    # Dev mode: API :8000 + Web :3000, hot reload
docker build -t atc-triage-v1 .      # Production build for HF Spaces
```

## Architecture

**Python backend** implements the OpenEnv spec. The request flow is:

`HTTP request` -> `server/app.py` (FastAPI endpoints) -> `server/atc_environment.py` (ATCEnvironment) -> returns ATCObservation

- `models.py` — All Pydantic v2 models (ATCAction, ATCObservation, ATCState, Flight, Weather). These are the wire format. Has fallback base classes if `openenv-core` is not installed.
- `server/atc_environment.py` — Core simulation. Manages flight queue, fuel burn (1 min/step for waiting flights), wake-turbulence separation matrix, weather timeline updates, crash detection. Single method `step()` always results in one landing attempt.
- `server/tasks.py` — Three deterministic scenarios (easy=4 flights, medium=7, hard=12) with weather timelines. `get_task_scenario(task_id)` returns a `Scenario` dataclass.
- `server/graders.py` — Deterministic scoring functions per task. Each returns 0.0-1.0 using weighted components (safety, priority ordering, medical handling, fuel management, efficiency). Called via `grade_episode()`.
- `server/app.py` — FastAPI app factory. Endpoints: `/reset`, `/step`, `/state`, `/health`, `/metadata`, `/schema`, `/tasks`, `/grade`. Single-session (no concurrent env instances).
- `client.py` — Thin httpx wrapper for calling the server programmatically.
- `inference.py` — Baseline agent using OpenAI API client. Builds structured prompts from observations, parses JSON actions from LLM responses.

**Next.js dashboard** (`apps/web/`) is a "use client" React 19 app with Tailwind v4. All state lives in `page.tsx`. Components (`radar-display`, `flight-table`, `weather-panel`, `control-panel`) receive props. API calls go through `src/lib/api.ts` which hits the Python server directly or via Next.js rewrites in dev.

**Connection pattern:** In dev, Next.js rewrites `/api/*` to the Python server. In Docker Compose, the web container uses `NEXT_PUBLIC_API_URL=http://api:8000`. For HF Spaces production, Python serves static Next.js build from `apps/web/out/`.

## Key Mechanics

- **Task selection:** Pass `episode_id="easy"|"medium"|"hard"` to `/reset`. Also accepts `"task:easy"` prefix format.
- **Fuel burn:** Each landing advances time by separation steps (2-4 based on wake turbulence matrix). During that time, all other pending flights lose 1 min fuel per step. The landing flight does not burn fuel.
- **Weather:** Medium and hard tasks have weather timelines — visibility changes at specific time steps. Flights with `min_visibility_nm` above current visibility cannot land (returns -3.0 penalty).
- **Episode ends** when: all flights landed/crashed, time exceeds max_time_steps, or step count exceeds max_time_steps. Remaining flights at timeout count as crashes.

## Test Structure

Tests are in `tests/` using pytest. Key fixture pattern: `@pytest.fixture` creates `easy_env`, `medium_env`, `hard_env` by calling `env.reset(episode_id=...)`. Files are organized by module: `test_models.py`, `test_environment.py`, `test_graders.py`, `test_tasks.py`, `test_server.py` (uses FastAPI TestClient), `test_inference.py`, `test_integration.py` (full episode runs with strategy comparison).

## Import Pattern

Python files use `sys.path.insert(0, project_root)` for imports since this runs both as a package and standalone. Imports are flat: `from models import ...`, `from server.tasks import ...`.
