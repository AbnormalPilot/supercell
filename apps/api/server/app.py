"""SUPERCELL — FastAPI application for OpenEnv ATC triage server.

Exposes the standard OpenEnv endpoints:
  POST /reset    — start a new episode
  POST /step     — take an action
  GET  /state    — current episode state
  GET  /health   — health check
  GET  /metadata — environment metadata
  GET  /schema   — action/observation/state schemas
  GET  /tasks    — list available tasks
  POST /grade    — grade a completed episode
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from models import ATCAction, ATCObservation, ATCState
from server.atc_environment import ATCEnvironment
from server.tasks import list_tasks

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ResetRequest(BaseModel):
    seed: Optional[int] = Field(default=None, ge=0)
    episode_id: Optional[str] = Field(default=None, max_length=255)


class StepRequest(BaseModel):
    action: dict[str, Any]
    timeout_s: Optional[float] = Field(default=None, gt=0)
    request_id: Optional[str] = Field(default=None, max_length=255)


class ResetResponse(BaseModel):
    observation: dict[str, Any]
    reward: Optional[float] = None
    done: bool = False


class StepResponse(BaseModel):
    observation: dict[str, Any]
    reward: Optional[float] = None
    done: bool = False


class HealthResponse(BaseModel):
    status: str = "healthy"


class MetadataResponse(BaseModel):
    name: str
    description: str
    version: str


class GradeResponse(BaseModel):
    task_id: str
    score: float
    landing_log: list[dict]
    crash_log: list[dict]
    steps_used: int
    episode_reward: float


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="SUPERCELL",
        description=(
            "SUPERCELL — AI-powered ATC emergency triage environment. "
            "An AI agent manages landing order for incoming flights under "
            "fuel, weather, and emergency constraints."
        ),
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Shared environment instance (single-session server)
    env = ATCEnvironment()
    _initialized = {"value": False}

    # ---- Health / Metadata / Schema ----

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(status="healthy")

    @app.get("/metadata", response_model=MetadataResponse)
    async def metadata():
        return MetadataResponse(
            name="supercell",
            description=(
                "SUPERCELL — ATC emergency triage environment. "
                "Manage landing order for inbound flights under fuel, "
                "weather, and emergency constraints."
            ),
            version="1.0.0",
        )

    @app.get("/schema")
    async def schema():
        return {
            "action": ATCAction.model_json_schema(),
            "observation": ATCObservation.model_json_schema(),
            "state": ATCState.model_json_schema(),
        }

    @app.get("/tasks")
    async def tasks():
        task_list = list_tasks()
        return {
            "tasks": task_list,
            "count": len(task_list),
        }

    # ---- Core OpenEnv endpoints ----

    @app.post("/reset", response_model=ResetResponse)
    async def reset(req: Optional[ResetRequest] = None):
        seed = req.seed if req else None
        episode_id = req.episode_id if req else None
        obs = env.reset(seed=seed, episode_id=episode_id)
        _initialized["value"] = True
        obs_dict = obs.model_dump()
        return ResetResponse(
            observation=obs_dict,
            reward=obs.reward,
            done=obs.done,
        )

    @app.post("/step", response_model=StepResponse)
    async def step(req: StepRequest):
        if not _initialized["value"]:
            raise HTTPException(status_code=400, detail="Call /reset before /step")
        try:
            action = ATCAction(**req.action)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid action: {e}")
        obs = env.step(action)
        obs_dict = obs.model_dump()
        return StepResponse(
            observation=obs_dict,
            reward=obs.reward,
            done=obs.done,
        )

    @app.get("/state")
    async def state():
        if not _initialized["value"]:
            raise HTTPException(status_code=400, detail="Call /reset first")
        return env.state.model_dump()

    @app.post("/grade", response_model=GradeResponse)
    async def grade():
        if not _initialized["value"]:
            raise HTTPException(status_code=400, detail="Call /reset first")
        st = env.state
        score = env.grade()
        return GradeResponse(
            task_id=st.task_id,
            score=score,
            landing_log=st.landing_log,
            crash_log=st.crash_log,
            steps_used=st.step_count,
            episode_reward=st.episode_reward,
        )

    # ---- Serve static Next.js build if present ----
    _api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _repo_root = os.path.dirname(os.path.dirname(_api_root))
    web_dist = os.path.join(_repo_root, "apps", "web", "out")

    @app.get("/")
    async def root():
        if os.path.isdir(web_dist):
            return RedirectResponse(url="/web/")
        return RedirectResponse(url="/docs")

    if os.path.isdir(web_dist):
        next_assets_dir = os.path.join(web_dist, "_next")
        if os.path.isdir(next_assets_dir):
            app.mount("/_next", StaticFiles(directory=next_assets_dir), name="web-next-assets")
        app.mount("/web", StaticFiles(directory=web_dist, html=True), name="web")

    return app


# ---------------------------------------------------------------------------
# ASGI app instance (used by uvicorn / openenv serve)
# ---------------------------------------------------------------------------
app = create_app()


def main(host: str | None = None, port: int | None = None):
    env_host = os.getenv("HOST", "0.0.0.0")
    env_port = os.getenv("PORT", "8000")

    resolved_host = host or env_host
    if port is not None:
        resolved_port = port
    else:
        try:
            resolved_port = int(env_port)
        except ValueError:
            resolved_port = 8000

    uvicorn.run("server.app:app", host=resolved_host, port=resolved_port, reload=False)


if __name__ == "__main__":
    main()
