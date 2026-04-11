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
    @app.get("/tasks", tags=["Environment Info"])
    async def tasks() -> dict[str, Any]:
        return {"tasks": list_tasks(), "count": len(TASKS)}

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
