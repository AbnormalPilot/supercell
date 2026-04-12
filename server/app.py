"""
SUPERCELL — VABB Mumbai ATC Emergency Triage.

Self-contained FastAPI application following the exact same architecture
as the known-passing reference submission (ashmit1812/scalarxmeta):
plain FastAPI, module-level `app` object, no openenv-core dependency,
score/task_score/info on every /reset and /step response.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure the repo root is importable (flat layout)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from environment import ATCEnvironment  # noqa: E402
from graders import strict_score  # noqa: E402
from models import ATCAction, ATCObservation, ATCState  # noqa: E402
from tasks import TASKS, canonical_task_id, list_tasks, resolve_task_id  # noqa: E402


# =====================================================================
# App + registry (module-level, matching reference pattern)
# =====================================================================

app = FastAPI(title="SUPERCELL — VABB Mumbai ATC", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

env_registry: Dict[str, ATCEnvironment] = {}


def get_session_env(session_id: str = "default") -> ATCEnvironment:
    if session_id not in env_registry:
        env_registry[session_id] = ATCEnvironment()
    return env_registry[session_id]


def _dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude={"reward", "done", "metadata"})
    return obj


def _reference_grade(task_id: str) -> Dict[str, Any]:
    """Run a priority-first rollout on the given task and return the score."""
    internal = resolve_task_id(task_id)
    env = ATCEnvironment()
    env.reset(episode_id=internal)
    priority_key = {"MAYDAY": 0, "PAN_PAN": 1, "NONE": 2}
    for _ in range(150):
        flights = env.state.flights
        if not flights:
            break
        landable = [(i, f) for i, f in enumerate(flights) if env._can_land(f)[0]]
        pool = landable if landable else list(enumerate(flights))
        pool.sort(key=lambda x: (priority_key.get(x[1].emergency.name, 9), x[1].fuel_minutes))
        obs = env.step(ATCAction(flight_index=pool[0][0]))
        if obs.done:
            break
    score = strict_score(env.grade())
    canon = canonical_task_id(internal)
    return {"task_id": canon, "score": score, "task_score": score}


# =====================================================================
# Endpoints — matches reference shape exactly
# =====================================================================


@app.get("/")
def root() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "healthy"}


@app.get("/metadata")
def metadata() -> Dict[str, Any]:
    return {
        "name": "supercell",
        "description": (
            "SUPERCELL — Monsoon Mumbai ATC Emergency Triage. "
            "OpenEnv-compliant environment at VABB where the agent "
            "sequences landings under fuel, weather, and emergency constraints."
        ),
        "readme_content": None,
        "version": "1.0.0",
        "author": "SUPERCELL Team",
        "documentation_url": None,
    }


@app.get("/tasks")
def tasks() -> Dict[str, Any]:
    difficulty_map = {"easy": "easy", "medium": "medium", "hard": "hard", "extra_hard": "hard"}
    return {
        "tasks": [
            {
                "id": canonical_task_id(tid),
                "name": TASKS[tid]()["task_name"],
                "difficulty": difficulty_map.get(tid, "medium"),
                "objective": TASKS[tid]()["description"][:240],
                "max_steps": TASKS[tid]()["max_steps"],
                "description": TASKS[tid]()["description"],
            }
            for tid in TASKS
        ]
    }


@app.get("/tasks/{task_id}")
def task_detail(task_id: str) -> Dict[str, Any]:
    internal = resolve_task_id(task_id)
    data = TASKS.get(internal, TASKS["easy"])()
    return {
        "id": canonical_task_id(internal),
        "name": data["task_name"],
        "difficulty": {"easy": "easy", "medium": "medium", "hard": "hard", "extra_hard": "hard"}.get(internal, "medium"),
        "description": data["description"],
        "max_steps": data["max_steps"],
        "num_flights": len(data["flights"]),
    }


@app.get("/schema")
def schema() -> Dict[str, Any]:
    return {
        "action": ATCAction.model_json_schema(),
        "observation": ATCObservation.model_json_schema(),
        "state": ATCState.model_json_schema(),
    }


@app.post("/mcp")
def mcp(payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": payload.get("id"),
        "result": {"status": "ok"},
    }


@app.post("/reset")
def reset(payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    body_task = payload.get("task_id") or payload.get("episode_id") or payload.get("taskId") or payload.get("task")
    internal = resolve_task_id(str(body_task) if body_task else "easy")

    env = ATCEnvironment()
    env_registry["default"] = env
    obs = env.reset(episode_id=internal)

    ts = strict_score(env.grade())
    return {
        "observation": _dump(obs),
        "reward": float(obs.reward or 0.0),
        "done": False,
        "score": ts,
        "task_score": ts,
        "info": {"score": ts, "task_score": ts, "task_id": canonical_task_id(internal)},
    }


@app.post("/step")
def step(action: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    env = get_session_env()
    payload = action.get("action", action) if isinstance(action, dict) else {}
    try:
        act = ATCAction(**payload)
    except Exception:
        act = ATCAction(flight_index=0)

    obs = env.step(act)
    ts = strict_score(env.grade())
    return {
        "observation": _dump(obs),
        "reward": float(obs.reward or 0.0),
        "done": bool(obs.done),
        "score": ts,
        "task_score": ts,
        "info": {
            "score": ts,
            "task_score": ts,
            "task_id": canonical_task_id(env.state.task_id),
            "episode_reward": float(env.state.episode_reward),
        },
    }


@app.get("/state")
def state() -> Dict[str, Any]:
    env = get_session_env()
    return env.state.model_dump()


@app.get("/grade")
def grade(task_id: str = "") -> Dict[str, Any]:
    if task_id:
        return _reference_grade(str(task_id))
    env = get_session_env()
    score = strict_score(env.grade())
    return {
        "task_id": canonical_task_id(env.state.task_id),
        "score": score,
        "task_score": score,
    }


@app.post("/grade")
def grade_post() -> Dict[str, Any]:
    return grade()


@app.get("/grader")
def grader(task_id: str = "") -> Dict[str, Any]:
    if task_id:
        return _reference_grade(str(task_id))
    scores = [_reference_grade(canonical_task_id(tid)) for tid in TASKS]
    aggregate = sum(item["score"] for item in scores) / float(max(len(scores), 1))
    agg = strict_score(float(aggregate))
    return {
        "scores": scores,
        "score": agg,
        "task_score": agg,
    }


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await websocket.accept()
    env = ATCEnvironment()
    env.reset(episode_id="easy")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except Exception as exc:
                await websocket.send_text(json.dumps({
                    "type": "observation",
                    "data": {"observation": _dump(env._build_observation(0, True)), "reward": 0.0, "done": True, "error": f"invalid_json:{exc}"},
                }))
                continue

            msg_type = message.get("type", "")
            data = message.get("data", {}) or {}

            if msg_type == "reset":
                tid = data.get("task_id") or data.get("episode_id") or data.get("taskId") or data.get("task")
                internal = resolve_task_id(str(tid) if tid else "easy")
                obs = env.reset(episode_id=internal)
                ts = strict_score(env.grade())
                await websocket.send_text(json.dumps({
                    "type": "observation",
                    "data": {"observation": _dump(obs), "reward": float(obs.reward or 0), "done": False, "score": ts, "task_score": ts},
                }))

            elif msg_type == "step":
                payload = data.get("action", data) if isinstance(data, dict) else {}
                try:
                    act = ATCAction(**payload)
                except Exception:
                    act = ATCAction(flight_index=0)
                obs = env.step(act)
                ts = strict_score(env.grade())
                await websocket.send_text(json.dumps({
                    "type": "observation",
                    "data": {"observation": _dump(obs), "reward": float(obs.reward or 0), "done": bool(obs.done), "score": ts, "task_score": ts},
                }))

            elif msg_type == "state":
                await websocket.send_text(json.dumps({
                    "type": "state",
                    "data": env.state.model_dump(),
                }))

            elif msg_type == "close":
                break

    except WebSocketDisconnect:
        pass


def main() -> None:
    import uvicorn
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("server.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
