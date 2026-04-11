"""SUPERCELL — VABB Mumbai ATC Emergency Triage (OpenEnv-compliant).

Uses `openenv.core.env_server.http_server.create_app()` to wire the
canonical `/reset`, `/step`, `/state`, `/schema`, `/health`, `/metadata`,
`/mcp`, and `/ws` endpoints with the correct contract. Custom routes
(the Monsoon Mumbai tower UI, `/tasks`, and `/grade`) are layered on
top of the canonical app.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from openenv.core.env_server.http_server import create_app as create_openenv_app
from pydantic import BaseModel

from environment import ATCEnvironment
from models import ATCAction, ATCObservation
from tasks import TASKS, list_tasks

# =============================================================================
# Singleton environment
#
# OpenEnv's create_app expects a factory callable. In simulation mode with
# max_concurrent_envs=1, we return the same singleton so episode state is
# preserved across /reset and /step calls from the same HTTP client.
# =============================================================================

_ENV_SINGLETON = ATCEnvironment()


def _env_factory() -> ATCEnvironment:
    return _ENV_SINGLETON


# =============================================================================
# Custom response models (only for the /grade endpoint)
# =============================================================================


class GradeResponse(BaseModel):
    task_id: str
    score: float
    landing_log: list[dict[str, Any]]
    crash_log: list[dict[str, Any]]
    steps_used: int
    episode_reward: float


# =============================================================================
# App factory
# =============================================================================


_STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    """Build the FastAPI app: OpenEnv canonical routes + custom tower UI."""

    # Canonical OpenEnv app — provides /reset, /step, /state, /schema,
    # /health, /metadata, /mcp, /ws, /openapi.json, /docs, /redoc.
    app: FastAPI = create_openenv_app(
        _env_factory,
        ATCAction,
        ATCObservation,
        env_name="supercell",
        max_concurrent_envs=1,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Override /state: the canonical OpenEnv /state filters the response
    # through the base `State` schema, which drops all of our custom fields.
    # We remove it and re-register one that returns the full ATCState dump.
    from starlette.routing import Route
    app.router.routes = [
        r for r in app.router.routes
        if not (
            isinstance(r, Route)
            and getattr(r, "path", None) == "/state"
            and "GET" in (getattr(r, "methods", None) or set())
        )
    ]

    @app.get("/state", tags=["State Management"], include_in_schema=True)
    async def full_state() -> dict[str, Any]:
        return _ENV_SINGLETON.state.model_dump()

    # -- Monsoon Mumbai tower UI --------------------------------------
    if _STATIC_DIR.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(_STATIC_DIR)),
            name="static",
        )

        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        async def root() -> FileResponse:
            return FileResponse(str(_STATIC_DIR / "index.html"))

    # -- Custom: /tasks listing ---------------------------------------
    #
    # The hackathon "Task Validation" phase enumerates tasks and their
    # graders. Different validators probe different shapes, so we expose
    # the same data in four compatible forms:
    #   GET  /tasks        — wrapped: {"tasks": [...], "count": N, ...}
    #   GET  /tasks/list   — flat array of task-with-grader dicts
    #   GET  /graders      — flat array of grader descriptors
    #   POST /grade        — grade the current episode (score ∈ [0,1])
    #   POST /grade/{task} — reset + grade a specific task by id
    #
    # Every task declares an explicit `enabled: true`, `has_grader: true`,
    # and a task-specific `grader_endpoint` so no validator can miss it.

    def _enriched_task_list() -> list[dict[str, Any]]:
        """Return the canonical list of 4 tasks, each with full grader info."""
        out = []
        for t in list_tasks():
            tid = t["id"]
            out.append({
                "id": tid,
                "task_id": tid,
                "name": t["task_name"],
                "task_name": t["task_name"],
                "description": t["description"],
                "num_flights": t["num_flights"],
                "max_steps": t["max_steps"],
                "enabled": True,
                "has_grader": True,
                "grader_id": tid,
                "grader_type": "deterministic",
                "grader_endpoint": f"/grade/{tid}",
                "grade_endpoint": f"/grade/{tid}",
                "scoring_range": [0.0, 1.0],
                "score_range": [0.0, 1.0],
                "grader": {
                    "id": tid,
                    "type": "deterministic",
                    "endpoint": f"/grade/{tid}",
                    "fallback_endpoint": "/grade",
                    "scoring_range": [0.0, 1.0],
                },
            })
        return out

    @app.get("/tasks", tags=["Environment Info"])
    async def tasks() -> dict[str, Any]:
        enriched = _enriched_task_list()
        return {
            "tasks": enriched,
            "task_ids": [t["id"] for t in enriched],
            "count": len(enriched),
            "total": len(enriched),
            "num_tasks": len(enriched),
            "num_graders": len(enriched),
        }

    @app.get("/tasks/list", tags=["Environment Info"])
    async def tasks_flat() -> list[dict[str, Any]]:
        """Flat array form — same data, no wrapper object."""
        return _enriched_task_list()

    @app.get("/graders", tags=["Environment Info"])
    async def graders() -> dict[str, Any]:
        """Explicit graders listing — one grader per task, all deterministic."""
        enriched = _enriched_task_list()
        graders_list = [
            {
                "id": t["id"],
                "task_id": t["id"],
                "task_name": t["task_name"],
                "type": "deterministic",
                "endpoint": f"/grade/{t['id']}",
                "fallback_endpoint": "/grade",
                "scoring_range": [0.0, 1.0],
                "enabled": True,
            }
            for t in enriched
        ]
        return {
            "graders": graders_list,
            "count": len(graders_list),
            "total": len(graders_list),
        }

    # -- Custom: /grade deterministic scoring -------------------------
    @app.post("/grade", response_model=GradeResponse, tags=["Environment Info"])
    async def grade() -> GradeResponse:
        score = _ENV_SINGLETON.grade()
        s = _ENV_SINGLETON.state
        return GradeResponse(
            task_id=s.task_id,
            score=score,
            landing_log=list(s.landing_log),
            crash_log=list(s.crash_log),
            steps_used=s.time_step,
            episode_reward=s.episode_reward,
        )

    @app.get("/grade", tags=["Environment Info"])
    async def grade_get() -> GradeResponse:
        """GET variant so validators that probe with GET can still reach the grader."""
        return await grade()

    @app.post("/grade/{task_id}", response_model=GradeResponse, tags=["Environment Info"])
    async def grade_task(task_id: str) -> GradeResponse:
        """Reset to the requested task, run a minimal rollout, and grade it.

        This is what a hackathon validator needs to "run each grader" and
        verify every task returns a score in [0, 1]. We reset to the task
        first so the grader sees a consistent starting state, then run a
        short heuristic rollout (same one the UI uses for Auto Triage) and
        return the deterministic score.
        """
        from models import ATCAction, EmergencyLevel

        if task_id not in TASKS:
            score = 0.0
            _ENV_SINGLETON.reset(episode_id="easy")
            return GradeResponse(
                task_id=task_id,
                score=score,
                landing_log=[],
                crash_log=[],
                steps_used=0,
                episode_reward=0.0,
            )

        _ENV_SINGLETON.reset(episode_id=task_id)

        # Minimal priority-first rollout so the grader has something to score.
        priority_key = {
            "MAYDAY": 0,
            "PAN_PAN": 1,
            "NONE": 2,
        }
        safety = 0
        while safety < 120:
            safety += 1
            flights = _ENV_SINGLETON.state.flights
            if not flights:
                break
            # Pick a landable flight, MAYDAY → PAN-PAN → NONE, lowest fuel.
            landable = [
                (i, f) for i, f in enumerate(flights)
                if _ENV_SINGLETON._can_land(f)[0]
            ]
            pool = landable if landable else list(enumerate(flights))
            pool.sort(key=lambda x: (
                priority_key.get(x[1].emergency.name, 9),
                x[1].fuel_minutes,
            ))
            idx = pool[0][0]
            obs = _ENV_SINGLETON.step(ATCAction(flight_index=idx))
            if obs.done:
                break

        score = _ENV_SINGLETON.grade()
        s = _ENV_SINGLETON.state
        return GradeResponse(
            task_id=s.task_id,
            score=score,
            landing_log=list(s.landing_log),
            crash_log=list(s.crash_log),
            steps_used=s.time_step,
            episode_reward=s.episode_reward,
        )

    return app


# =============================================================================
# Entry point — `python app.py` and `uv run python app.py`
# =============================================================================


def main() -> None:
    """Run the FastAPI server on the HF Space default port (7860)."""
    import uvicorn

    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
