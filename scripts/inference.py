#!/usr/bin/env python3
"""Baseline inference script for ATC-Triage-v1.

Uses the OpenAI API client to run an LLM agent against all three tasks
and reports reproducible scores.

Required environment variables:
    API_BASE_URL  — LLM API endpoint (e.g. https://api.openai.com/v1)
    MODEL_NAME    — model identifier (e.g. gpt-4o)
    HF_TOKEN      — Hugging Face / API key (used as fallback for OPENAI_API_KEY)
"""

from __future__ import annotations

import json
import os
import sys
import time

# Ensure apps/api is importable (models, client live there)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "apps", "api"))

from openai import OpenAI

from client import ATCClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o")
API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("HF_TOKEN", "")
ENV_URL = os.environ.get("ENV_URL", "http://localhost:8000")

TASKS = ["easy", "medium", "hard"]
MAX_RETRIES = 3  # retries per LLM call on parse failure


def build_prompt(observation: dict) -> str:
    """Convert an ATC observation dict into a prompt for the LLM."""
    obs = observation.get("observation", observation)
    flights = obs.get("flights", [])
    weather = obs.get("weather", {})

    lines = [
        "You are an expert air traffic controller. You must decide which flight to clear for landing next.",
        "",
        f"=== WEATHER ===",
        f"Visibility: {weather.get('visibility_nm', '?')} nm | "
        f"Wind: {weather.get('wind_knots', '?')} kt | "
        f"Crosswind: {weather.get('crosswind_knots', '?')} kt | "
        f"Precipitation: {weather.get('precipitation', 'none')} | "
        f"Trend: {weather.get('trend', 'stable')}",
        "",
        f"=== RUNWAY ===",
        f"Free in: {obs.get('runway_free_in_steps', 0)} steps | "
        f"Time step: {obs.get('time_step', 0)}/{obs.get('max_time_steps', '?')} | "
        f"Landed: {obs.get('landed_safely', 0)} | "
        f"Crashed: {obs.get('crashed', 0)} | "
        f"Total: {obs.get('total_flights', '?')}",
        "",
        "=== PENDING FLIGHTS ===",
    ]

    for f in flights:
        status_parts = []
        if f.get("emergency") == "MAYDAY":
            status_parts.append("*** MAYDAY ***")
        elif f.get("emergency") == "PAN_PAN":
            status_parts.append("** PAN-PAN **")
        if f.get("medical_onboard"):
            status_parts.append("[MEDICAL]")
        if f.get("fuel_minutes", 999) < 10:
            status_parts.append(f"[FUEL CRITICAL: {f['fuel_minutes']} min]")
        if not f.get("can_land_now", True):
            status_parts.append("[CANNOT LAND - weather below minimums]")
        status = " ".join(status_parts) if status_parts else "normal"

        lines.append(
            f"  [{f['index']}] {f['callsign']} ({f['aircraft_type']}) — "
            f"Emergency: {f.get('emergency','NONE')} | "
            f"Fuel: {f.get('fuel_minutes','?')} min | "
            f"Pax: {f.get('passengers','?')} | "
            f"Vis min: {f.get('min_visibility_nm','?')} nm | "
            f"Wake: {f.get('wake_category','?')} | "
            f"Status: {status}"
        )

    lines.extend([
        "",
        "RULES:",
        "- MAYDAY flights are in immediate danger — prioritize by fuel remaining",
        "- Flights with <10 min fuel will crash if not landed soon (fuel burns ~1 min per separation step)",
        "- PAN-PAN / medical passengers are urgent but not immediately life-threatening",
        "- Flights that 'CANNOT LAND' in current weather should be deferred unless weather is improving",
        "- Each landing uses 2-4 steps of separation time; all waiting flights burn fuel",
        "- More passengers = higher stakes",
        "",
        "Respond with ONLY a JSON object: {\"flight_index\": <index>}",
    ])

    return "\n".join(lines)


def parse_action(response_text: str) -> int | None:
    """Extract flight_index from LLM response."""
    text = response_text.strip()
    # Try JSON parse
    try:
        # Find JSON object in response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            if "flight_index" in data:
                return int(data["flight_index"])
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fallback: look for a bare number
    import re
    match = re.search(r"flight_index[\"'\s:]+(\d+)", text)
    if match:
        return int(match.group(1))

    # Last resort: first digit
    match = re.search(r"\d+", text)
    if match:
        return int(match.group(0))

    return None


def run_task(
    llm: OpenAI,
    env: ATCClient,
    task_id: str,
) -> dict:
    """Run a single task episode and return results."""
    print(f"\n{'='*60}")
    print(f"  Task: {task_id}")
    print(f"{'='*60}")

    reset_resp = env.reset(task_id=task_id)
    obs = reset_resp
    done = obs.get("done", False)
    step_num = 0

    while not done:
        prompt = build_prompt(obs)

        # Call LLM with retries
        action_idx = None
        for attempt in range(MAX_RETRIES):
            try:
                completion = llm.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert air traffic controller AI. Respond only with JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    max_tokens=100,
                )
                response_text = completion.choices[0].message.content or ""
                action_idx = parse_action(response_text)
                if action_idx is not None:
                    break
            except Exception as e:
                print(f"  LLM error (attempt {attempt+1}): {e}")
                time.sleep(1)

        if action_idx is None:
            action_idx = 0  # fallback: pick first flight
            print(f"  Step {step_num}: Failed to parse LLM response, defaulting to index 0")

        # Step environment
        step_resp = env.step(action_idx)
        obs = step_resp
        step_obs = obs.get("observation", obs)
        done = obs.get("done", False) or step_obs.get("done", False)
        reward = obs.get("reward", 0)
        step_num += 1

        # Progress display
        n_flights = len(step_obs.get("flights", []))
        print(
            f"  Step {step_num}: landed flight_index={action_idx} | "
            f"reward={reward} | remaining={n_flights} | done={done}"
        )

    # Grade
    grade_resp = env.grade()
    score = grade_resp.get("score", 0.0)
    print(f"\n  Final score: {score:.4f}")
    print(f"  Landed: {grade_resp.get('landing_log', [])}")
    if grade_resp.get("crash_log"):
        print(f"  Crashed: {grade_resp['crash_log']}")

    return {
        "task_id": task_id,
        "score": score,
        "steps": step_num,
        "episode_reward": grade_resp.get("episode_reward", 0),
        "landed": len(grade_resp.get("landing_log", [])),
        "crashed": len(grade_resp.get("crash_log", [])),
    }


def main():
    print("=" * 60)
    print("  ATC-Triage-v1  —  Baseline Inference")
    print("=" * 60)
    print(f"  API: {API_BASE_URL}")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Environment: {ENV_URL}")
    print()

    if not API_KEY:
        print("ERROR: Set OPENAI_API_KEY or HF_TOKEN environment variable.")
        sys.exit(1)

    llm = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = ATCClient(base_url=ENV_URL)

    # Verify server health
    try:
        h = env.health()
        print(f"  Server health: {h['status']}")
    except Exception as e:
        print(f"ERROR: Cannot reach environment server at {ENV_URL}: {e}")
        print("Start the server first: uv run python -m server.app")
        sys.exit(1)

    results = []
    for task_id in TASKS:
        result = run_task(llm, env, task_id)
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    print(f"  {'Task':<10} {'Score':>8} {'Steps':>6} {'Landed':>7} {'Crashed':>8} {'Reward':>10}")
    print(f"  {'-'*10} {'-'*8} {'-'*6} {'-'*7} {'-'*8} {'-'*10}")
    total_score = 0.0
    for r in results:
        print(
            f"  {r['task_id']:<10} {r['score']:>8.4f} {r['steps']:>6d} "
            f"{r['landed']:>7d} {r['crashed']:>8d} {r['episode_reward']:>10.2f}"
        )
        total_score += r["score"]
    avg = total_score / len(results) if results else 0
    print(f"\n  Average score: {avg:.4f}")
    print()

    env.close()
    return results


if __name__ == "__main__":
    main()
