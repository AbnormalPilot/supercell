---
title: SUPERCELL — ATC Emergency Triage
emoji: ✈️
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: true
license: mit
tags:
  - openenv
  - reinforcement-learning
  - agent-evaluation
  - pytorch
---

# SUPERCELL — ATC Emergency Triage Environment

> **OpenEnv-compliant reinforcement learning environment** where an AI agent prioritizes landing order for incoming flights under fuel, weather, and emergency constraints.

Built for the **Meta PyTorch OpenEnv Hackathon**.

[![Tests](https://img.shields.io/badge/tests-213%20passing-brightgreen)](#testing)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-v1%20compliant-blue)](#api-endpoints)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

---

## Evaluator Quick Start

```bash
# 1. Install deps
pip install -r requirements.txt          # or: uv sync

# 2. Start the server
python apps/api/main.py                  # → http://localhost:8000

# 3. Run the heuristic demo (no API key needed)
python demo.py

# 4. Run the hackathon inference script (OpenEnv format)
export HF_TOKEN="hf_..."
ENV_URL=http://localhost:8000 SUPERCELL_TASK=hard python inference.py

# 5. Run tests
python -m pytest apps/api/tests/ -q     # 213 tests
```

The API is fully documented at **http://localhost:8000/docs** (Swagger UI).

---

## The Problem

Air traffic controllers make life-or-death triage decisions every day — which flight lands first when three are declaring emergencies, two are running out of fuel, and a thunderstorm is closing in?

**SUPERCELL** models that exact problem as an OpenEnv-compliant RL environment:

- **Real-world task**: FAA-style emergency prioritization with realistic flight parameters
- **Multi-objective optimization**: balance safety, urgency, fuel state, passenger count, weather windows, and wake turbulence separation
- **Cascading failures**: wrong decisions compound — delayed flights burn fuel, weather deteriorates, crashes cascade
- **Genuine difficulty**: frontier models (GPT-4o) score ~0.45 on the hard task; perfect score requires sophisticated multi-constraint reasoning

---

## Quick Start

```bash
# Install Python dependencies
uv sync

# Start the environment server
uv run python apps/api/main.py

# Start the dashboard (in another terminal)
pnpm install && pnpm dev
```

Open **http://localhost:3000** for the dashboard, **http://localhost:8000/docs** for the API.

### Run Inference

```bash
# Heuristic agent (no API key needed, deterministic)
python demo.py

# OpenAI baseline (GPT-4o)
export OPENAI_API_KEY="sk-..."
uv run python scripts/inference.py

# PyTorch / Llama baseline (Meta models via HF Inference API)
export HF_TOKEN="hf_..."
uv run python scripts/inference_hf.py

# Local PyTorch inference (requires GPU)
USE_LOCAL=true HF_TOKEN="hf_..." uv run python scripts/inference_hf.py

# Train a PyTorch DQN agent directly against the environment
uv run python scripts/train_dqn.py --task all --episodes 2000
```

### Docker

```bash
# Build production image (includes Next.js static UI + Python API)
docker build -t supercell .

# Run (port 7860 = HF Spaces default)
docker run -p 7860:7860 supercell

# API available at http://localhost:7860/docs
# Dashboard at http://localhost:7860/web/
```

---

## Dashboard

The SUPERCELL dashboard is a professional aviation-grade ATC workstation:

- **Radar Scope** — SVG radar with sweep animation, range rings, compass rose, color-coded flight blips
- **Flight Strip Board** — ATC-style strips with emergency badges, fuel bars, medical indicators, pulse animations
- **Weather Panel** — METAR display with visibility bars, wind, crosswind, ceiling, precipitation, trend
- **Control Tower** — Task selection, time progress, stats, reward tracking, AI auto-play with speed control
- **Event Log** — Color-coded timeline of landings, crashes, weather changes, AI decisions
- **Score Breakdown** — Mission report with performance bar, landing/crash logs

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `Space` / `Enter` | Clear selected flight for landing |
| `Arrow Up/Down` | Navigate between flights |
| `A` | Toggle AI auto-play |
| `1` / `2` / `3` | Switch to Easy / Medium / Hard scenario |

### AI Auto-Play

Press **A** or click the AI Agent button to activate intelligent auto-play. The built-in agent prioritizes:
1. MAYDAY emergencies first (by fuel)
2. Lowest fuel among same priority
3. Flights that can land in current weather

---

## Environment Specification

### Observation Space

| Field | Type | Description |
|---|---|---|
| `flights` | `list[FlightInfo]` | All pending flights with full attributes |
| `weather` | `WeatherInfo` | Current visibility, wind, precipitation, trend |
| `runway_free_in_steps` | `int` | Steps until runway is available |
| `time_step` / `max_time_steps` | `int` | Current time / episode limit |
| `landed_safely` / `crashed` | `int` | Running safety counters |
| `total_flights` | `int` | Total flights in scenario |
| `task_id` | `str` | Current task (`easy`, `medium`, `hard`) |
| `instructions` | `str` | Human-readable task guidance |
| `done` | `bool` | Episode terminated |
| `reward` | `float` | Step reward (dense signal) |

**FlightInfo fields**: `index`, `callsign`, `aircraft_type`, `emergency` (`NONE`/`PAN_PAN`/`MAYDAY`), `fuel_minutes`, `passengers`, `distance_nm`, `medical_onboard`, `min_visibility_nm`, `wake_category` (`LIGHT`/`MEDIUM`/`HEAVY`/`SUPER`), `can_land_now`

### Action Space

```json
{ "flight_index": 0 }
```

Single integer — the index into the current `flights` list. Invalid indices and weather-blocked flights are penalized but don't crash the episode.

### Reward Function (Dense Signal)

| Event | Reward | Notes |
|---|---|---|
| Safe landing | `+10` to `+60` | Scaled by emergency type, passenger count, fuel urgency |
| MAYDAY handled | `+25` bonus | On top of base landing reward |
| PAN-PAN handled | `+12` bonus | Urgency reward |
| Medical emergency | `+10` bonus | Humanitarian priority |
| Near-crash save (<5 min fuel) | `+15` | Critical fuel save |
| Low fuel save (<10 min fuel) | `+5` | Proactive fuel management |
| Holding cost | `−0.5 × pending_count` | Per landing step (time pressure) |
| Weather-blocked attempt | `−3.0` | Flight below visibility minimums |
| Invalid action (index OOB) | `−5.0` | Agent error |
| Fuel exhaustion crash | `−100.0` | Safety violation |
| All flights landed, zero crashes | `+50.0` | Episode completion bonus |

The reward is dense and multi-dimensional: it signals partial progress throughout the episode, not just at termination.

### Episode Mechanics

- **Fuel burn**: Every time-step, all pending flights (except the one landing) burn 1 min of fuel
- **Separation**: Each landing advances simulation time by 2–4 steps (wake turbulence matrix; HEAVY/SUPER leaders cause longer delays)
- **Weather**: Step-triggered timeline changes affect visibility in real time
- **Crash detection**: Flights with ≤0 fuel are removed and scored as crashes
- **Episode ends**: All flights resolved (landed/crashed), `time_step ≥ max_steps`, or all flights exhausted

---

## Tasks

### Easy: Clear Skies Priority (4 flights, 15 steps max)

```
DAL892  MAYDAY  4 min fuel    → must land immediately
AAL217  PAN-PAN 30 min fuel   → medical passenger on board
UAL441  NONE    45 min fuel   → normal
SWA103  NONE    50 min fuel   → normal
```

Clear skies (10 nm visibility), stable weather. The correct priority order is unambiguous. Even a naive greedy agent should score well if it handles the MAYDAY correctly.

**Grading**: 40% safety + 40% priority ordering + 20% efficiency

---

### Medium: Storm Window (7 flights, 30 steps max)

```
BAW119  MAYDAY  6 min fuel    B777   → fuel-critical large widebody
AFR882  NONE    8 min fuel    A220   → low fuel, no emergency
JBU562  PAN-PAN 20 min fuel   A321   → medical passenger
SKW3341 PAN-PAN 10 min fuel   CRJ700 → min 2.0 nm visibility
NKS447  NONE    12 min fuel   A320   → min 1.5 nm visibility
DLH401  NONE    35 min fuel   A340   → min 3.0 nm, heavy wake
UAE205  NONE    55 min fuel   A380   → min 2.0 nm, SUPER wake
```

Weather deteriorates from 8 nm → 1 nm visibility over ~20 steps (thunderstorm). Heavy aircraft must land before the ceiling closes. Low-fuel flights race the clock. The optimal agent must balance fuel urgency against the shrinking weather window.

**Grading**: 30% safety + 25% priority + 15% medical + 15% fuel management + 15% efficiency

---

### Hard: Mass Diversion Crisis (12 flights, 50 steps max)

**Opening weather: 2.0 nm (thunderstorm)** — blocks 3 aircraft from landing at episode start.

| Flight | Type | Emergency | Fuel | Min Vis | Trap |
|---|---|---|---|---|---|
| UAL921 | B787 | MAYDAY | 5 min | 1.5 nm | medical |
| DAL550 | A330 | MAYDAY | 7 min | 1.5 nm | — |
| AAL018 | B777 | MAYDAY | 14 min | **4.0 nm** | **WEATHER-BLOCKED at start** |
| SWA655 | B737 | PAN-PAN | 10 min | 1.0 nm | medical |
| JBU788 | A321 | PAN-PAN | 14 min | 1.0 nm | — |
| NKS221 | A320 | NONE | **4 min** | 1.0 nm | **fuel trap** |
| SKW4412 | E175 | NONE | **6 min** | 2.5 nm | blocked + fuel trap |
| EJA742 | CL-350 | NONE | 12 min | 3.0 nm | VFR-only, blocked |
| FDX801 | B767F | NONE | 18 min | 1.5 nm | cargo |
| AFR991 | B787 | NONE | 15 min | 1.5 nm | — |
| DLH470 | A350 | NONE | 25 min | 1.5 nm | — |
| BAW287 | A380 | NONE | 40 min | 2.0 nm | **SUPER wake** |

**Weather window:** visibility drops to 1.0 nm at step 5, opens to 4.5 nm at step 10 (enabling AAL018, SKW4412, EJA742), then closes again at step 14.

**The traps:**
1. AAL018 is MAYDAY but weather-blocked — agents that try MAYDAY-first get −3 penalty and waste time steps
2. NKS221 has only 4 min fuel with no emergency declaration — must land before some MAYDAYs
3. BAW287 (SUPER wake) creates 4-step separation cascades if sequenced poorly
4. The optimal strategy requires fuel-first sequencing that overrides emergency-label heuristics

**Grading**: 30% safety + 20% priority + 10% medical + 20% fuel management + 10% efficiency + 10% perfect-run bonus

---

## Baseline Scores

### Heuristic Agent (deterministic, no API key required)

The heuristic prioritizes: MAYDAY by fuel → PAN-PAN by fuel → NONE by fuel, skipping weather-blocked flights.

| Task | Score | Landed | Crashed | Reward |
|---|---|---|---|---|
| Easy | **1.0000** | 4/4 | 0 | +151.4 |
| Medium | **0.8990** | 7/7 | 0 | +256.8 |
| Hard | **0.7370** | 9/12 | 3 | +389.8 |
| **Average** | **0.8787** | 20/23 | 3 | +266.0 |

Run with: `python demo.py`

### PyTorch DQN Agent

Train a DQN agent directly against `ATCEnvironment` (no HTTP overhead) using masked Q-learning for the variable-action space:

```bash
uv run python scripts/train_dqn.py --task all --episodes 2000
```

| Task | DQN Score (2000 eps) | Heuristic | Random |
|---|---|---|---|
| Easy | ~0.92 | 1.0000 | ~0.25 |
| Medium | ~0.75 | 0.8990 | ~0.18 |
| Hard | ~0.52 | 0.7370 | ~0.12 |

DQN converges on easy within ~300 episodes and shows clear improvement on hard by episode 1000. The hard task's weather-blocked MAYDAY and fuel traps create a genuinely non-greedy optimization surface where RL agents can learn to outperform naive heuristics. Training: ~3 min on CPU, ~45s on GPU.

### LLM Baselines (approximate, temperature=0)

| Model | Easy | Medium | Hard | Notes |
|---|---|---|---|---|
| GPT-4o | ~0.97 | ~0.72 | ~0.48 | Via `scripts/inference.py` |
| Llama-3.2-3B (HF API) | ~0.85 | ~0.58 | ~0.32 | Via `scripts/inference_hf.py` |

The hard task is designed to challenge frontier models — correct solution requires simultaneously reasoning about fuel urgency, weather timing windows, wake turbulence sequence effects, and the NKS221 fuel-trap.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/reset` | Start episode: `{"episode_id": "easy"}` or `{"task_id": "easy"}` |
| `POST` | `/step` | Take action: `{"action": {"flight_index": 0}}` |
| `GET` | `/state` | Current episode state |
| `POST` | `/grade` | Grade completed episode → `score ∈ [0.0, 1.0]` |
| `GET` | `/health` | Health check |
| `GET` | `/metadata` | Environment name, description, version |
| `GET` | `/schema` | JSON schemas for action/observation/state |
| `GET` | `/tasks` | List all 3 tasks with descriptions |
| `POST` | `/ai/step` | Bonus: Llama-powered decision (requires `HF_TOKEN`) |

Full Swagger UI at `/docs`.

### Example Session

```bash
# Reset to hard task
curl -s -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"episode_id": "hard"}' | python -m json.tool

# Take an action
curl -s -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"flight_index": 0}}' | python -m json.tool

# Grade the episode
curl -s -X POST http://localhost:8000/grade | python -m json.tool
```

---

## Architecture

```
HTTP request → FastAPI (app.py) → ATCEnvironment → ATCObservation
                                   ├── reset()   — clean state, load scenario
                                   ├── step()    — validate → land → advance time
                                   │              → burn fuel → check crashes
                                   │              → update weather → check done
                                   └── state     — current episode state snapshot

Graders (deterministic):
  grade_easy()   — safety 40%, priority 40%, efficiency 20%
  grade_medium() — safety 30%, priority 25%, medical 15%, fuel 15%, efficiency 15%
  grade_hard()   — safety 30%, priority 20%, medical 10%, fuel 20%, efficiency 10%, bonus 10%
```

---

## Project Structure

```
supercell/
├── README.md                   # This file (also HF Space card)
├── openenv.yaml                # OpenEnv v1 manifest
├── Dockerfile                  # Production: Next.js static + FastAPI on :7860
├── docker-compose.yml          # Dev: API :8000 + Web :3000 with hot reload
├── pyproject.toml              # Python deps (uv)
├── requirements.txt            # pip-compatible deps list
├── inference.py                # Hackathon inference script ([START]/[STEP]/[END] format)
├── demo.py                     # Heuristic agent — deterministic baseline
│
├── apps/
│   ├── api/                    # Python FastAPI environment
│   │   ├── main.py             # Server entry point (reads PORT env var)
│   │   ├── models.py           # Pydantic v2: ATCAction, ATCObservation, ATCState
│   │   ├── client.py           # Python client for scripted evaluation
│   │   └── server/
│   │       ├── app.py          # FastAPI routes (all OpenEnv endpoints)
│   │       ├── atc_environment.py  # Core simulation engine
│   │       ├── tasks.py        # 3 scenario definitions (easy/medium/hard)
│   │       ├── graders.py      # Deterministic scoring functions
│   │       └── ai_agent.py     # Llama inference via HF Inference API
│   │
│   └── web/                    # Next.js dashboard
│       └── src/
│           ├── app/page.tsx    # Main dashboard with AI auto-play
│           ├── components/     # Radar, strips, weather, controls, score
│           └── lib/            # API client, types, simulation state
│
├── scripts/
│   ├── train_dqn.py            # PyTorch DQN agent (masked Q-learning, trains on env directly)
│   ├── inference.py            # OpenAI API baseline (any model)
│   └── inference_hf.py         # HuggingFace/Llama baseline (local or API)
│
└── apps/api/tests/             # 213 tests across 8 files
    ├── test_server.py          # Endpoint integration tests
    ├── test_environment.py     # Environment mechanics
    ├── test_graders.py         # Scoring function tests
    ├── test_tasks.py           # Scenario validation
    ├── test_models.py          # Pydantic model tests
    └── test_integration.py     # Full episode runs
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Environment** | Python 3.12, FastAPI, Pydantic v2 |
| **Inference** | PyTorch, Transformers, Llama 3.2, OpenAI API |
| **Dashboard** | Next.js 15, React 19, Tailwind CSS v4 |
| **Tooling** | uv, pnpm, Turborepo, Docker |
| **Compliance** | OpenEnv v1 spec, openenv-core |

---

## Testing

```bash
# Python tests (all 213 pass)
uv run python -m pytest apps/api/tests/ -v

# Production web build
pnpm build:web

# Type-check + all tests
pnpm check

# OpenEnv validation
uv run openenv validate openenv.yaml
```

---

Built with PyTorch + OpenEnv for the **Meta PyTorch OpenEnv Hackathon**.
