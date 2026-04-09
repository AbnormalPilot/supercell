"""SUPERCELL — Pure Python Gradio UI + FastAPI Backend.

Single-file application combining Gradio UI with the ATC environment.
No Node.js/Next.js required — pure Python from frontend to backend.
"""

from __future__ import annotations

import sys
import os
import asyncio
import json
from typing import Optional
from dataclasses import asdict

# Add apps/api to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps", "api"))

import gradio as gr
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import ATCAction, EmergencyLevel
from server.atc_environment import ATCEnvironment
from server.tasks import list_tasks, TASKS
from server.graders import GRADERS

# ---------------------------------------------------------------------------
# Environment State
# ---------------------------------------------------------------------------

env = ATCEnvironment()
_initialized = False

# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def reset_task(task_id: str, seed: Optional[int] = None) -> tuple:
    """Reset environment with selected task."""
    global _initialized
    obs = env.reset(seed=seed, episode_id=task_id)
    _initialized = True
    return format_state(obs)


def step_action(flight_callsign: str) -> tuple:
    """Take a step to land a flight."""
    global _initialized
    if not _initialized:
        return "Error: Please reset environment first", "", "", "", ""
    
    action = ATCAction(flight_to_land=flight_callsign)
    obs = env.step(action)
    return format_state(obs)


def auto_step() -> tuple:
    """Auto-select next flight to land (simple priority heuristic)."""
    global _initialized
    if not _initialized:
        return "Error: Please reset environment first", "", "", "", ""
    
    # Simple heuristic: land by priority (mayday > panpan > normal, then by fuel)
    flights = env.state.flights
    if not flights:
        return format_state(env.state)
    
    # Sort by emergency level and fuel
    priority = {"MAYDAY": 0, "PAN_PAN": 1, "NONE": 2}
    sorted_flights = sorted(
        flights,
        key=lambda f: (priority.get(f.emergency.value, 2), f.fuel_minutes)
    )
    
    next_flight = sorted_flights[0]
    action = ATCAction(flight_to_land=next_flight.callsign)
    obs = env.step(action)
    return format_state(obs)


def format_state(obs) -> tuple:
    """Format observation into UI components."""
    
    # Header info
    header = f"""
**Task:** {obs.task_name} | **Step:** {obs.time_step}/{obs.max_time_steps} | **Status:** {'DONE' if obs.done else 'ACTIVE'}

**Landed:** {obs.landed_safely} | **Crashed:** {obs.crashed} | **Remaining:** {len(obs.flights)}
"""
    
    if obs.done:
        header += f"\n### 🎯 Episode Complete! Final Score: {obs.episode_reward:.2f}"
    
    # Weather display
    weather = obs.weather
    weather_info = f"""
**Visibility:** {weather.visibility_nm:.1f} nm
**Wind:** {weather.wind_knots:.0f} kt
**Crosswind:** {weather.crosswind_knots:.0f} kt
**Ceiling:** {weather.ceiling_feet:.0f} ft
**Precipitation:** {weather.precipitation}
**Trend:** {weather.trend}
"""
    
    # Flights table
    if obs.flights:
        flights_data = []
        for f in obs.flights:
            emj = "🔴" if f.emergency.value == "MAYDAY" else "🟡" if f.emergency.value == "PAN_PAN" else "⚪"
            med = " 🏥" if f.medical_onboard else ""
            flights_data.append([
                f"{emj} {f.callsign}",
                f.aircraft_type,
                f.emergency.value,
                f"{f.fuel_minutes:.0f} min",
                f"{f.distance_nm:.0f} nm",
                f.passengers,
                f"{f.min_visibility_nm:.1f} nm{med}"
            ])
        
        flights_md = "| Callsign | Type | Emergency | Fuel | Distance | PAX | Min Vis |\n"
        flights_md += "|----------|------|-----------|------|----------|-----|----------|\n"
        for row in flights_data:
            flights_md += f"| {' | '.join(map(str, row))} |\n"
    else:
        flights_md = "*No active flights*"
    
    # Log
    log_text = ""
    for entry in env.state.landing_log[-10:]:  # Last 10 entries
        status = "✅ LANDED" if entry.get('landed_safely') else "❌ CRASH"
        log_text += f"T+{entry.get('step', 0)}: {entry.get('callsign', 'Unknown')} - {status}\n"
    
    if obs.crash_log:
        log_text += "\n**CRASHES:**\n"
        for entry in obs.crash_log[-5:]:
            log_text += f"❌ {entry.get('callsign', 'Unknown')}: {entry.get('reason', 'Unknown')}\n"
    
    # Score breakdown if done
    score_info = ""
    if obs.done:
        score_info = f"""
### Score Breakdown
- **Total Score:** {obs.episode_reward:.2f}
- **Landed Safely:** {obs.landed_safely}/{obs.total_flights}
- **Crashed:** {obs.crashed}
- **Steps Used:** {env.state.step_count}/{obs.max_time_steps}
"""
    
    return header, weather_info, flights_md, log_text, score_info


def grade_episode() -> str:
    """Grade the current episode."""
    if not _initialized:
        return "Error: Please reset and run episode first"
    
    try:
        score = env.grade()
        st = env.state
        return f"""
## Final Grade

**Score:** {score:.4f} / 1.0

**Task:** {st.task_id}
**Landed:** {len(st.landing_log)} / {st.total_flights}
**Crashed:** {len(st.crash_log)}
**Steps Used:** {st.step_count}
"""
    except Exception as e:
        return f"Error grading: {str(e)}"


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

def create_gradio_app() -> gr.Blocks:
    """Create the Gradio UI."""
    
    css = """
    .mayday { color: #ff3333; font-weight: bold; }
    .panpan { color: #ffbf00; font-weight: bold; }
    .normal { color: #00ff41; }
    .header { text-align: center; }
    .flight-table { font-family: monospace; font-size: 12px; }
    """
    
    with gr.Blocks(css=css, title="SUPERCELL ATC") as demo:
        gr.Markdown("""
        # 🎯 SUPERCELL — ATC Emergency Triage
        
        **AI-powered air traffic control environment.** Manage landing order for inbound flights 
        under fuel, weather, and emergency constraints.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Select Task")
                
                task_buttons = []
                tasks = list_tasks()
                
                for task in tasks:
                    task_id = task['id']
                    task_name = task['task_name']
                    num_flights = task['num_flights']
                    
                    btn = gr.Button(
                        f"{task_name}\n({num_flights} flights)",
                        variant="secondary"
                    )
                    task_buttons.append((btn, task_id))
                
                gr.Markdown("---")
                gr.Markdown("### Manual Control")
                
                flight_input = gr.Textbox(
                    label="Flight Callsign to Land",
                    placeholder="e.g., UAL891"
                )
                
                with gr.Row():
                    land_btn = gr.Button("🛬 Land Flight", variant="primary")
                    auto_btn = gr.Button("🤖 Auto Land (Next)", variant="secondary")
                    reset_btn = gr.Button("🔄 Reset Current Task", variant="secondary")
                
                grade_btn = gr.Button("📊 Grade Episode", variant="secondary")
                
            with gr.Column(scale=2):
                # State outputs
                header_output = gr.Markdown("*Select a task to begin*")
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 🌤️ Weather")
                        weather_output = gr.Markdown("*No active weather*")
                    
                    with gr.Column():
                        gr.Markdown("### 📊 Score")
                        score_output = gr.Markdown("")
                
                gr.Markdown("### ✈️ Active Flights")
                flights_output = gr.Markdown("*No flights*", elem_classes=["flight-table"])
                
                gr.Markdown("### 📋 Event Log")
                log_output = gr.Textbox(
                    label="",
                    lines=10,
                    max_lines=20,
                    interactive=False
                )
        
        # Event handlers
        def on_task_click(task_id):
            return reset_task(task_id)
        
        # Bind task buttons
        for btn, task_id in task_buttons:
            btn.click(
                fn=lambda t=task_id: reset_task(t),
                outputs=[header_output, weather_output, flights_output, log_output, score_output]
            )
        
        # Bind control buttons
        land_btn.click(
            fn=step_action,
            inputs=[flight_input],
            outputs=[header_output, weather_output, flights_output, log_output, score_output]
        )
        
        auto_btn.click(
            fn=auto_step,
            outputs=[header_output, weather_output, flights_output, log_output, score_output]
        )
        
        reset_btn.click(
            fn=lambda: reset_task(env.state.task_id if env.state else "easy"),
            outputs=[header_output, weather_output, flights_output, log_output, score_output]
        )
        
        grade_btn.click(
            fn=grade_episode,
            outputs=[score_output]
        )
        
        # Keyboard shortcuts info
        gr.Markdown("""
        ---
        **Tips:**
        - 🔴 **MAYDAY** = Fuel critical, land immediately
        - 🟡 **PAN-PAN** = Urgent but stable
        - ⚪ **Normal** = Standard priority
        - 🏥 = Medical emergency on board
        - Check **Visibility** vs **Min Vis** — don't land in weather worse than aircraft minimums!
        """)
    
    return demo


# ---------------------------------------------------------------------------
# FastAPI Mount (for HF Spaces compatibility)
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create FastAPI app with Gradio mounted."""
    app = FastAPI(
        title="SUPERCELL",
        description="Pure Python ATC Triage Environment with Gradio UI",
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
    
    # Create and mount Gradio UI
    gradio_app = create_gradio_app()
    gradio_app.queue()
    app = gr.mount_gradio_app(app, gradio_app, path="/")
    
    return app


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # For local development
    demo = create_gradio_app()
    demo.launch(server_name="0.0.0.0", server_port=7860)
