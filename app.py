"""SUPERCELL — Simplified Hackathon Submission.

Unified FastAPI + Gradio application for Meta PyTorch Hackathon.
Pure Python, single-directory structure for maximum simplicity.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any
from dataclasses import asdict

import gradio as gr
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
# Gradio UI Functions
# =============================================================================

def format_observation(obs: ATCObservation) -> Dict:
    """Format observation for Gradio display."""
    # Header
    header = f"""## {obs.task_name}
**Step:** {obs.time_step}/{obs.max_time_steps} | **Status:** {'✅ DONE' if obs.done else '🟢 ACTIVE'}
**Landed:** {obs.landed_safely} | **Crashed:** {obs.crashed} | **Remaining:** {len(obs.flights)}
"""
    if obs.done:
        header += f"\n### 🎯 Final Score: {obs.episode_reward:.2f}"
    
    # Weather
    w = obs.weather
    weather_md = f"""### 🌤️ Weather
- **Visibility:** {w.visibility_nm:.1f} nm
- **Wind:** {w.wind_knots:.0f} kt | **Crosswind:** {w.crosswind_knots:.0f} kt
- **Ceiling:** {w.ceiling_feet:.0f} ft
- **Precipitation:** {w.precipitation}
- **Trend:** {w.trend}
"""
    
    # Flights table
    if obs.flights:
        flights_md = "### ✈️ Active Flights\n\n"
        flights_md += "| Idx | Callsign | Type | Emergency | Fuel | PAX | Min Vis | Can Land |\n"
        flights_md += "|-----|----------|------|-----------|------|-----|---------|----------|\n"
        for f in obs.flights:
            emj = "🔴" if f.emergency == "MAYDAY" else "🟡" if f.emergency == "PAN_PAN" else "⚪"
            med = " 🏥" if f.medical_onboard else ""
            can = "✅" if f.can_land_now else "❌"
            flights_md += f"| {f.index} | {emj} {f.callsign} | {f.aircraft_type} | {f.emergency}{med} | {f.fuel_minutes:.0f}m | {f.passengers} | {f.min_visibility_nm:.1f}nm | {can} |\n"
    else:
        flights_md = "### ✈️ No Active Flights\n"
    
    # Log
    log_text = ""
    if env.state.landing_log:
        log_text += "**LANDINGS:**\n"
        for entry in env.state.landing_log[-10:]:
            status = "✅" if entry.get('landed_safely') else "❌"
            log_text += f"T+{entry.get('step', 0)}: {status} {entry.get('callsign', 'Unknown')}\n"
    
    if env.state.crash_log:
        log_text += "\n**CRASHES:**\n"
        for entry in env.state.crash_log[-5:]:
            log_text += f"❌ T+{entry.get('step', 0)}: {entry.get('callsign', 'Unknown')} - {entry.get('reason', 'Unknown')}\n"
    
    return {
        "header": header,
        "weather": weather_md,
        "flights": flights_md,
        "log": log_text or "No events yet.",
    }


def ui_reset_task(task_id: str) -> tuple:
    """Reset task for Gradio UI."""
    global _initialized
    obs = env.reset(episode_id=task_id)
    _initialized = True
    fmt = format_observation(obs)
    return fmt["header"], fmt["weather"], fmt["flights"], fmt["log"]


def ui_step(flight_index: int) -> tuple:
    """Take a step for Gradio UI."""
    global _initialized
    if not _initialized:
        return "Error: Reset first", "", "*No flights*", ""
    
    action = ATCAction(flight_index=int(flight_index))
    obs = env.step(action)
    fmt = format_observation(obs)
    return fmt["header"], fmt["weather"], fmt["flights"], fmt["log"]


def ui_auto() -> tuple:
    """Auto-select and land next flight."""
    global _initialized
    if not _initialized or not env.state.flights:
        return ui_reset_task("easy")
    
    # Simple priority: MAYDAY > PAN_PAN > NONE, then by fuel
    priority = {"MAYDAY": 0, "PAN_PAN": 1, "NONE": 2}
    sorted_flights = sorted(
        enumerate(env.state.flights),
        key=lambda x: (priority.get(x[1].emergency.name, 2), x[1].fuel_minutes)
    )
    
    if sorted_flights:
        idx, _ = sorted_flights[0]
        return ui_step(idx)
    
    return format_observation(env._get_observation()).values()


def ui_grade() -> str:
    """Grade current episode."""
    if not _initialized:
        return "Error: No episode to grade"
    
    score = env.grade()
    return f"""## Grade Result

**Score:** {score:.4f} / 1.0

**Task:** {env.state.task_id}
**Landed:** {len(env.state.landing_log)} / {env.state.total_flights}
**Crashed:** {len(env.state.crash_log)}
**Steps Used:** {env.state.time_step} / {env.state.max_steps}
"""


# =============================================================================
# Gradio App
# =============================================================================

def create_gradio_ui() -> gr.Blocks:
    """Create Gradio UI."""
    
    with gr.Blocks(title="SUPERCELL ATC") as demo:
        gr.Markdown("""# 🎯 SUPERCELL — ATC Emergency Triage
AI-powered air traffic control for emergency landings.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 🎮 Controls")
                
                task_dropdown = gr.Dropdown(
                    choices=[("Easy (4 flights)", "easy"), ("Medium (7 flights)", "medium"), 
                             ("Hard (12 flights)", "hard"), ("Extra Hard (20 flights)", "extra_hard")],
                    value="easy",
                    label="Select Task"
                )
                
                reset_btn = gr.Button("🔄 Reset Task", variant="primary")
                
                flight_index = gr.Number(value=0, label="Flight Index to Land", precision=0)
                land_btn = gr.Button("🛬 Land Flight", variant="secondary")
                auto_btn = gr.Button("🤖 Auto Land (Smart)", variant="secondary")
                
                grade_btn = gr.Button("📊 Grade Episode")
                grade_output = gr.Markdown()
                
            with gr.Column(scale=2):
                header_output = gr.Markdown("Select a task to begin")
                weather_output = gr.Markdown()
                
                with gr.Accordion("✈️ Active Flights", open=True):
                    flights_output = gr.Markdown("*No flights*")
                
                with gr.Accordion("📋 Event Log", open=False):
                    log_output = gr.Markdown()
        
        # Event handlers
        reset_btn.click(
            fn=ui_reset_task,
            inputs=[task_dropdown],
            outputs=[header_output, weather_output, flights_output, log_output]
        )
        
        land_btn.click(
            fn=ui_step,
            inputs=[flight_index],
            outputs=[header_output, weather_output, flights_output, log_output]
        )
        
        auto_btn.click(
            fn=ui_auto,
            outputs=[header_output, weather_output, flights_output, log_output]
        )
        
        grade_btn.click(fn=ui_grade, outputs=[grade_output])
        
        gr.Markdown("""
---
**Quick Guide:**
- 🔴 **MAYDAY** = Critical emergency, land ASAP
- 🟡 **PAN-PAN** = Urgent but stable
- ⚪ **NONE** = Normal priority
- 🏥 = Medical emergency onboard
- **Can Land** = ✅ if weather permits, ❌ if weather below minimums
        """)
    
    return demo


# =============================================================================
# FastAPI App
# =============================================================================

def create_app() -> FastAPI:
    """Create FastAPI app with Gradio mounted."""
    
    app = FastAPI(
        title="SUPERCELL",
        description="Simplified ATC Triage for Meta PyTorch Hackathon",
        version="1.0.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
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
        task_id = req.task_id if req else "easy"
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
    
    # Mount Gradio
    demo = create_gradio_ui()
    demo.queue()
    app = gr.mount_gradio_app(app, demo, path="/")
    
    return app


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    # Local development
    demo = create_gradio_ui()
    port = int(os.getenv("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
