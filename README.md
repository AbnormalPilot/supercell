---
title: SUPERCELL — VABB Mumbai ATC
emoji: 🛬
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: true
license: mit
tags:
  - openenv
  - reinforcement-learning
  - agent-evaluation
  - atc
  - aviation
---

# SUPERCELL — Monsoon Mumbai ATC Emergency Triage

> **OpenEnv v1-compliant** reinforcement-learning environment where an
> agent plays the Tower Controller at **VABB / Chhatrapati Shivaji
> International Airport, Mumbai** during monsoon operations — sequencing
> landings on a single active runway under fuel, weather, wake
> turbulence, and emergency constraints.

Built for the **Meta PyTorch OpenEnv Hackathon**.

VABB is the world's busiest single-runway airport in real life
(~950 movements/day), bracketed by a city that crowds the fence line
and a monsoon that routinely drops visibility below 800 m. SUPERCELL
models that environment as an RL task. No other submission is set at
an Indian airport — no other submission will have the same problem
surface.

---

## Quick Start

```bash
# 1. Install deps (uv recommended; pip works too)
uv sync

# 2. Start the environment + UI (port 7860, HF Space default)
uv run python app.py          # → http://localhost:7860

# 3. Run the hackathon baseline inference script
export HF_TOKEN="hf_..."
export SUPERCELL_TASK=hard
uv run python inference.py    # emits [START] / [STEP] / [END] to stdout
```

Open `http://localhost:7860` for the **Monsoon Mumbai Tower** UI (phosphor-CRT
radar scope, NOTAM ticker, real Indian airline callsigns, ATC voice log),
or `http://localhost:7860/docs` for the Swagger API.

---

## File Layout

```
.
├── app.py              # FastAPI app factory (OpenEnv routes + UI)
├── models.py           # Pydantic v2 models (Action / Observation / State)
├── environment.py      # ATCEnvironment — reset / step / grade
├── tasks.py            # 4 scenarios (easy, medium, hard, extra_hard)
├── graders.py          # Deterministic [0.0, 1.0] graders
├── inference.py        # OpenAI-client baseline, hackathon stdout format
├── openenv.yaml        # OpenEnv v1 manifest
├── Dockerfile          # HF Space build
├── pyproject.toml      # Python deps
└── static/             # Monsoon Mumbai ATC UI (HTML + CSS + canvas JS)
    ├── index.html
    ├── style.css
    └── radar.js
```

Everything lives at the repo root — no `apps/`, no monorepo, no build step.

---

## The Task

Three graded scenarios + one hidden bonus. All share the same
`ATCAction { flight_index: int }` / `ATCObservation` contract. The
agent's job: at every step, pick which inbound flight to clear for
landing.

### Easy · "Winter Haze"
Calm November dawn. **4 inbounds**, clear skies, one MAYDAY and one
medical PAN-PAN. The correct priority is unambiguous. Even a naive
policy should score well if it lands the MAYDAY first.

```
AIC852    B777-300ER  MAYDAY   fuel 8m   (Air India)
IGO6E227  A320neo     PAN-PAN  med/15m   (IndiGo)
VTI995    A321neo     -        25m       (Vistara)
SEJ144    B737-800    -        30m       (SpiceJet)
```

### Medium · "Pre-Monsoon Squall"
May afternoon, Arabian Sea squall line rolling in.
**7 inbounds**. Visibility deteriorates from 8 nm → 1 nm over ~14 steps,
then eases. `BAW139` (3 nm minima) and `UAE504` (SUPER wake A380) must
land in the open window, while `AIC132` MAYDAY and low-fuel `AXB471`
race the clock.

### Hard · "Mumbai Monsoon Surge"
July afternoon, peak monsoon. **12 diverted aircraft**, 3 MAYDAYs,
2 PAN-PANs, and traps everywhere:

| Callsign  | Aircraft   | Status   | Fuel | Min Vis | Trap |
|-----------|-----------|---------|------|---------|------|
| AIC176    | B787-9     | MAYDAY  | 5m   | 1.5 nm  | medical |
| AIC348    | A330-300   | MAYDAY  | 7m   | 1.5 nm  | — |
| IGO6E2043 | A320neo    | MAYDAY  | 14m  | **4.0 nm** | **weather-blocked** |
| SEJ21     | B737-800   | PAN-PAN | 10m  | 1.0 nm  | medical |
| VTI997    | A321neo    | PAN-PAN | 14m  | 1.0 nm  | — |
| IGO6E5393 | A320       | NONE    | **4m** | 1.0 nm | **silent fuel trap** |
| AXB812    | B737-800   | NONE    | 6m   | **2.5 nm** | low fuel + weather-blocked |
| VT-JEX    | Cessna X   | NONE    | 12m  | 3.0 nm  | VFR-only, blocked |
| FDX57     | B767F      | NONE    | 18m  | 1.5 nm  | — |
| QTR554    | B787-9     | NONE    | 15m  | 1.5 nm  | — |
| SIA422    | A350-900   | NONE    | 25m  | 1.5 nm  | — |
| UAE504    | A380-800   | NONE    | 40m  | 2.0 nm  | **SUPER wake** |

**Weather window:** visibility is 2.0 nm at episode start, drops to 1.0 nm
at step 5, then **opens to 4.5 nm for exactly 4 steps** (step 10–13) —
that's the only window the 3+ nm minima flights can land. Miss it and
they're stranded.

The optimal strategy requires **fuel-first sequencing that overrides
emergency-label heuristics** — `IGO6E5393` (NONE, 4 min fuel) must land
before `IGO6E2043` (MAYDAY but weather-blocked) even though MAYDAY has
nominal priority.

### Extra Hard · "Total System Chaos" (hidden bonus)
20 aircraft. Five MAYDAYs with critical fuel. Four medical PAN-PANs.
VFR-only business jets. A SUPER-wake A380. Weather oscillating between
0.5 nm and 6 nm four times over 80 steps. Not required for spec
compliance — included for agents that want to prove they can handle
true chaos.

---

## Observation & Action Spaces

```python
class ATCAction(BaseModel):
    flight_index: int  # 0-based index into observation.flights

class ATCObservation(BaseModel):
    flights: list[FlightInfo]       # full aircraft state
    weather: WeatherInfo            # vis, wind, precip, trend
    runway_free_in_steps: int
    time_step: int
    max_time_steps: int
    landed_safely: int
    crashed: int
    total_flights: int
    task_id: str
    task_name: str
    done: bool
    reward: float
    episode_reward: float
    instructions: str
```

`FlightInfo` per aircraft:

| Field             | Type  | Notes |
|-------------------|-------|-------|
| `index`           | int   | position in current flights list |
| `callsign`        | str   | ICAO callsign (e.g. `AIC176`) |
| `aircraft_type`   | str   | type code (`B787-9`, `A320neo`, …) |
| `emergency`       | str   | `NONE` / `PAN_PAN` / `MAYDAY` |
| `fuel_minutes`    | float | remaining fuel |
| `passengers`      | int   | souls on board |
| `distance_nm`     | float | range from VABB |
| `bearing_deg`     | float | bearing from airport (0=N, 90=E) |
| `approach_fix`    | str   | STAR fix (PARAR/GUDOM/NOMUS/LEKIT) |
| `medical_onboard` | bool  | humanitarian flag |
| `min_visibility_nm` | float | aircraft category minima |
| `wake_category`   | str   | LIGHT/MEDIUM/HEAVY/SUPER |
| `can_land_now`    | bool  | weather + runway check combined |

### Reward Function (dense, partial-progress)

Rewards are shaped to give signal **throughout the episode**, not just
at termination. Representative values:

| Event                             | Reward |
|-----------------------------------|--------|
| Safe landing (base)               | `+10` |
| &nbsp;&nbsp;+ MAYDAY bonus        | `+25` |
| &nbsp;&nbsp;+ PAN-PAN bonus       | `+12` |
| &nbsp;&nbsp;+ medical bonus       | `+10` |
| &nbsp;&nbsp;+ critical-fuel save (<5 min) | `+15` |
| &nbsp;&nbsp;+ low-fuel save (<10 min)      | `+5`  |
| &nbsp;&nbsp;+ passenger-scaled (caps at A380) | up to `+10` |
| Weather-blocked attempt           | `-3`  |
| Runway-blocked attempt            | `-1`  |
| Holding cost (per pending flight) | `-0.5` per step |
| Invalid flight index              | `-5`  |
| Fuel-exhaustion crash             | `-100` per aircraft |
| Perfect episode (all landed, 0 crashed) | `+50` |

A successful MAYDAY landing with a medical passenger and <5 min fuel
yields **+60 reward in a single step** — enough to be a clear positive
signal even in the middle of a long trajectory. A single crash costs
`-100`, making safety violations dominant negatives.

### Grader (deterministic, [0.0, 1.0])

Each task has its own weighted grader. Higher tasks apply stricter
crash penalties and scale `fuel_ok` thresholds upward:

| Task         | safety | priority | medical | fuel | efficiency | bonus | crash penalty |
|--------------|:------:|:--------:|:-------:|:----:|:----------:|:-----:|:-------------:|
| easy         | 40%    | 40%      | —       | —    | 20%        | —     | 0.50/crashed  |
| medium       | 30%    | 25%      | 15%     | 15%  | 15%        | —     | 0.40/crashed  |
| hard         | 30%    | 20%      | 10%     | 20%  | 10%        | 10%   | 0.35/crashed  |
| extra_hard   | 25%    | 20%      | 15%     | 20%  | 10%        | 10%   | 0.30/crashed  |

Graders are pure functions of `landing_log` + `crash_log`, so identical
episodes always return identical scores (spec requirement).

---

## Baseline Scores (measured)

Priority-first heuristic (MAYDAY → PAN-PAN → NONE, lowest fuel within
each band, skipping weather-blocked flights), run directly against
`ATCEnvironment` — no HTTP, no LLM, deterministic:

| Task         | Score | Landed | Crashed | Steps |
|--------------|:------:|:------:|:-------:|:-----:|
| easy         | **1.000** | 4/4   | 0 | 8   |
| medium       | **0.940** | 7/7   | 0 | 23  |
| hard         | **0.604** | 9/12  | 3 | 23  |
| extra_hard   | **0.418** | 12/20 | 8 | 31  |

Random-policy reference (seed=0):

| Task         | Random Score |
|--------------|:------------:|
| easy         | 1.000        |
| medium       | 0.767        |
| hard         | 0.325        |

The **hard task discriminates** between policies: a priority-first
heuristic reaches ~0.60, random reaches ~0.33, a perfect run reaches
1.0. Frontier models currently score in the 0.40–0.65 band — they
systematically fall into the `IGO6E2043` MAYDAY trap (trying to land a
weather-blocked aircraft) and miss `IGO6E5393`'s silent fuel trap.

---

## API Endpoints (OpenEnv v1)

| Method | Path        | Description |
|--------|-------------|-------------|
| `POST` | `/reset`    | Start episode. Body: `{"episode_id": "hard"}` |
| `POST` | `/step`     | Take action. Body: `{"action": {"flight_index": 0}}` |
| `GET`  | `/state`    | Current observation snapshot |
| `POST` | `/grade`    | Grade episode → `{"score": 0.0..1.0, ...}` |
| `GET`  | `/health`   | Health probe (200 OK) |
| `GET`  | `/metadata` | Environment metadata |
| `GET`  | `/schema`   | JSON schemas for action + observation |
| `GET`  | `/tasks`    | All tasks with descriptions |

Full Swagger UI at `/docs`.

### Example session

```bash
# Reset to hard
curl -s -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"episode_id":"hard"}' | python -m json.tool

# Step
curl -s -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action":{"flight_index":0}}' | python -m json.tool

# Grade
curl -s -X POST http://localhost:7860/grade | python -m json.tool
```

---

## Inference Script

`inference.py` at the repo root uses the **OpenAI client** (required by
the hackathon spec) and reads:

| Variable       | Default                              |
|----------------|--------------------------------------|
| `API_BASE_URL` | `https://router.huggingface.co/v1`   |
| `MODEL_NAME`   | `Qwen/Qwen2.5-72B-Instruct`          |
| `HF_TOKEN`     | *(required)* HuggingFace/API key     |
| `ENV_URL`      | `http://localhost:7860`              |
| `LOCAL_IMAGE_NAME` | *(optional)* Docker image to boot locally |
| `SUPERCELL_TASK` | `hard`                             |

Stdout strictly matches the hackathon grammar:

```
[START] task=hard env=supercell model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=land(0) reward=49.62 done=false error=null
[STEP] step=2 action=land(0) reward=37.68 done=false error=null
...
[END] success=true steps=23 score=0.60 rewards=49.62,37.68,...
```

All rewards and scores are formatted to **2 decimal places**; boolean
fields are lowercase; error is `null` or the raw error string. Exactly
one `[START]` and exactly one `[END]` is emitted per invocation
(verified by repo smoke test).

---

## Docker

```bash
# Build (matches HF Space build)
docker build -t supercell .

# Run (port 7860 = HF Spaces default)
docker run -p 7860:7860 supercell
```

The image is a single-stage Python 3.12-slim, `uv sync --frozen --no-dev`,
~150 MB. No Node, no build step, no GPU required. Runs comfortably
inside the 2 vCPU / 8 GB hackathon infrastructure limit.

---

## The Dashboard

Open `http://localhost:7860` for the **VABB Tower** UI — an Apple-inspired
marketing site for the environment with a live tower embedded inside:

- **Cinematic hero** on pure black with 56-72px SF Pro Display headlines
- **Status strip** showing scenario, step, visibility, wind, MAYDAY count,
  landed, crashed, and running reward
- **Primary surveillance radar scope** (canvas) with real VABB approach-fix
  geometry (PARAR / GUDOM / NOMUS / LEKIT), 09/27 and 14/32 runway symbols,
  60-RPM sweep, Apple Blue for normal traffic, amber for PAN-PAN, red for MAYDAY
- **Flight progress strips** with emergency/medical tags, fuel urgency colouring
- **METAR line** in proper format (`METAR VABB 1430Z 24012KT 2000M RA…`)
- **Tower voice log** with authentic ATC phraseology
  (`AIC176, cleared to land runway 27, wind 240 at 14. Welcome to Mumbai.`)
- **Alternating dark/light sections** covering the three graded scenarios
  and the OpenEnv compliance spec
- **Keyboard shortcuts**: `1/2/3/4` switch scenarios, `Space/Enter`
  clear selected flight, `A` auto-triage, arrow keys navigate strips

The UI follows the Apple design system documented in `DESIGN.md` —
SF Pro typography, a `#000`/`#f5f5f7` binary section rhythm, Apple Blue
(`#0071e3`) as the single accent, and 980px pill CTAs. The UI is
decorative; the environment, models, graders, and inference **do not
depend on it** — `openenv validate` and the baseline inference script
work without the UI ever loading.

---

## Why Mumbai?

This is the creativity lever. Every hackathon submission solves a
different domain — ours is the only one grounded in a real, named,
high-stakes airport that trainees study as a case study in real ATC
schools. Mumbai's monsoon:

- Real visibility events below 500 m
- Real crosswinds exceeding aircraft certification limits
- A single runway that handles a movement every 65 seconds in peak hours
- Real diversion pressure when storm cells park over the approach path

The traps in the `hard` scenario (weather-blocked MAYDAY, silent fuel
trap, SUPER-wake cascade) are abstracted from real incidents. This
isn't generic "ATC simulator" — it's **a simulation of a specific place
on Earth that is genuinely hard to control**.

---

## Testing

```bash
# Smoke-test the environment directly (no HTTP, no LLM)
uv run python -c "
from models import ATCAction
from environment import ATCEnvironment
env = ATCEnvironment()
for t in ['easy','medium','hard','extra_hard']:
    env.reset(episode_id=t)
    print(f'{t}: {env.state.total_flights} flights loaded')
"

# Full round-trip API test
uv run python app.py &
sleep 2
curl -s -X POST http://localhost:7860/reset -d '{\"episode_id\":\"easy\"}' \
  -H 'Content-Type: application/json' | python -m json.tool
```

---

Built with **FastAPI + Pydantic v2 + pure-canvas JS** for the
**Meta PyTorch OpenEnv Hackathon**.
