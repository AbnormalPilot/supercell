"""SUPERCELL — CSIA Mumbai ATC with Custom UI.

FastAPI backend with custom Mumbai Airport themed HTML/JS frontend.
No Gradio — pure custom radar simulation.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from models import ATCAction, ATCObservation, EmergencyLevel
from environment import ATCEnvironment
from tasks import list_tasks, TASKS
from graders import GRADERS

# =============================================================================
# Global State
# =============================================================================

env = ATCEnvironment()
_initialized = False

# =============================================================================
# Pydantic Models for API
# =============================================================================

class ResetRequest(BaseModel):
    seed: Optional[int] = None
    episode_id: Optional[str] = None
    task_id: Optional[str] = None

class StepRequest(BaseModel):
    action: Dict[str, Any]

class GradeResponse(BaseModel):
    task_id: str
    score: float
    landing_log: List[Dict]
    crash_log: List[Dict]
    steps_used: int
    episode_reward: float

# =============================================================================
# FastAPI App
# =============================================================================

def create_app() -> FastAPI:
    """Create FastAPI app with custom Mumbai Airport UI."""
    
    app = FastAPI(
        title="SUPERCELL - CSIA Mumbai ATC",
        description="Mumbai Airport ATC Emergency Triage Simulation",
        version="1.0.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Serve static files (CSS, JS)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Serve custom UI at root
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return FileResponse("static/index.html")
    
    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy", "airport": "CSIA Mumbai", "icao": "VABB"}
    
    # List tasks
    @app.get("/tasks")
    async def tasks():
        return {"tasks": list_tasks(), "count": len(TASKS)}
    
    # List graders
    @app.get("/graders")
    async def graders():
        return {
            "graders": [
                {
                    "task_id": task_id,
                    "id": task_id,
                    "type": "deterministic",
                    "endpoint": "/grade",
                    "scoring_range": [0.0, 1.0],
                }
                for task_id in GRADERS.keys()
            ],
            "count": len(GRADERS),
        }
    
    # Reset
    @app.post("/reset")
    async def reset(req: Optional[ResetRequest] = None):
        global _initialized
        task_id = req.task_id if req else (req.episode_id if req else "easy")
        obs = env.reset(episode_id=task_id)
        _initialized = True
        return {
            "observation": asdict(obs),
            "reward": obs.reward,
            "done": obs.done,
        }
    
    # Step
    @app.post("/step")
    async def step(req: StepRequest):
        global _initialized
        if not _initialized:
            raise HTTPException(status_code=400, detail="Call /reset first")
        
        action = ATCAction(**req.action)
        obs = env.step(action)
        return {
            "observation": asdict(obs),
            "reward": obs.reward,
            "done": obs.done,
        }
    
    # State
    @app.get("/state")
    async def state():
        global _initialized
        if not _initialized:
            raise HTTPException(status_code=400, detail="Call /reset first")
        return asdict(env._get_observation())
    
    # Grade
    @app.post("/grade", response_model=GradeResponse)
    async def grade():
        global _initialized
        if not _initialized:
            raise HTTPException(status_code=400, detail="Call /reset first")
        
        score = env.grade()
        return GradeResponse(
            task_id=env.state.task_id,
            score=score,
            landing_log=env.state.landing_log,
            crash_log=env.state.crash_log,
            steps_used=env.state.time_step,
            episode_reward=env.state.episode_reward,
        )
    
    return app

# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
