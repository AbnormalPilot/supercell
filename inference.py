#!/usr/bin/env python3
"""
SUPERCELL — ATC Emergency Triage
OpenEnv Hackathon inference script.

Mandatory env vars:
    API_BASE_URL        LLM endpoint  (default: https://router.huggingface.co/v1)
    MODEL_NAME          Model ID      (default: Qwen/Qwen2.5-72B-Instruct)
    HF_TOKEN            API key
    LOCAL_IMAGE_NAME    Docker image name (starts container if set)

Optional:
    ENV_URL             Environment URL if already running (default: http://localhost:7860)
    SUPERCELL_TASK      Task to run: easy | medium | hard  (default: hard)

Stdout format (required by hackathon):
    [START] task=<task> env=supercell model=<model>
    [STEP]  step=<n> action=<str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...>
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from typing import List, Optional

import httpx
from openai import OpenAI

# ── Configuration ────────────────────────────────────────────────────────────
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME")
API_KEY          = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
API_BASE_URL     = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME       = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
TASK_NAME        = os.getenv("SUPERCELL_TASK", "hard")
BENCHMARK        = "supercell"
ENV_URL          = os.getenv("ENV_URL", "http://localhost:7860")
MAX_STEPS        = 70
SUCCESS_THRESHOLD = 0.4


# ── Logging helpers ───────────────────────────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── Docker startup ────────────────────────────────────────────────────────────
def _wait_for_health(url: str, timeout: int = 60) -> bool:
    """Poll /health until the server responds or timeout is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{url}/health", timeout=3.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def start_docker_container(image: str) -> tuple[subprocess.Popen, str]:
    """Start the SUPERCELL docker container and return (process, url)."""
    port = 7860
    url = f"http://localhost:{port}"
    proc = subprocess.Popen(
        ["docker", "run", "--rm", "-p", f"{port}:{port}", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    ok = _wait_for_health(url, timeout=90)
    if not ok:
        proc.terminate()
        raise RuntimeError(f"Environment container did not become healthy within 90s (image={image})")
    return proc, url


# ── LLM prompt builder ────────────────────────────────────────────────────────
def build_prompt(obs: dict) -> str:
    flights = obs.get("flights", [])
    weather = obs.get("weather", {})
    lines = [
        "You are an expert air traffic controller. Decide which flight to clear for landing next.",
        "",
        "=== WEATHER ===",
        (
            f"Visibility: {weather.get('visibility_nm', '?')} nm | "
            f"Wind: {weather.get('wind_knots', '?')} kt | "
            f"Crosswind: {weather.get('crosswind_knots', '?')} kt | "
            f"Precipitation: {weather.get('precipitation', 'none')} | "
            f"Trend: {weather.get('trend', 'stable')}"
        ),
        "",
        (
            f"=== RUNWAY ===  free_in={obs.get('runway_free_in_steps', 0)} steps | "
            f"time={obs.get('time_step', 0)}/{obs.get('max_time_steps', '?')} | "
            f"landed={obs.get('landed_safely', 0)} crashed={obs.get('crashed', 0)}"
        ),
        "",
        "=== PENDING FLIGHTS ===",
    ]

    for f in flights:
        flags = []
        if f.get("emergency") == "MAYDAY":
            flags.append("*** MAYDAY ***")
        elif f.get("emergency") == "PAN_PAN":
            flags.append("** PAN-PAN **")
        if f.get("medical_onboard"):
            flags.append("[MEDICAL]")
        fuel = f.get("fuel_minutes", 999)
        if fuel < 10:
            flags.append(f"[FUEL CRITICAL: {fuel}min]")
        if not f.get("can_land_now", True):
            flags.append("[BLOCKED - weather below minimums]")
        status = " ".join(flags) if flags else "normal"
        lines.append(
            f"  [{f['index']}] {f.get('callsign','')} ({f.get('aircraft_type','')}) — "
            f"emergency={f.get('emergency','NONE')} fuel={fuel}min "
            f"pax={f.get('passengers','?')} vis_min={f.get('min_visibility_nm','?')}nm "
            f"wake={f.get('wake_category','?')} | {status}"
        )

    lines += [
        "",
        "RULES:",
        "- MAYDAY flights are in immediate danger — prioritize by fuel remaining",
        "- Flights with <10 min fuel will crash soon (all waiting flights burn 1 min/separation-step)",
        "- Flights marked BLOCKED cannot land in current weather — skip them unless weather improves",
        "- Each landing takes 2-4 separation steps; use that time wisely",
        "",
        'Respond with ONLY JSON: {"flight_index": <index>}',
    ]
    return "\n".join(lines)


def parse_action(text: str) -> Optional[int]:
    """Extract flight_index from LLM response."""
    text = text.strip()
    try:
        start, end = text.find("{"), text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            if "flight_index" in data:
                return int(data["flight_index"])
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    m = re.search(r"flight_index[\"'\s:]+(\d+)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"\d+", text)
    return int(m.group(0)) if m else None


# ── Environment HTTP helpers ──────────────────────────────────────────────────
def env_reset(http: httpx.Client, task_id: str) -> dict:
    r = http.post("/reset", json={"episode_id": task_id})
    r.raise_for_status()
    return r.json()


def env_step(http: httpx.Client, flight_index: int) -> dict:
    r = http.post("/step", json={"action": {"flight_index": flight_index}})
    r.raise_for_status()
    return r.json()


def env_grade(http: httpx.Client) -> dict:
    r = http.post("/grade")
    r.raise_for_status()
    return r.json()


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    docker_proc = None
    active_url = ENV_URL

    try:
        # Start docker container if image name provided
        if LOCAL_IMAGE_NAME:
            docker_proc, active_url = start_docker_container(LOCAL_IMAGE_NAME)

        llm = OpenAI(base_url=API_BASE_URL, api_key=API_KEY or "no-key")
        http = httpx.Client(base_url=active_url, timeout=30.0)

        # Verify health
        try:
            r = http.get("/health")
            r.raise_for_status()
        except Exception as exc:
            print(f"[DEBUG] Cannot reach environment at {active_url}: {exc}", flush=True)
            log_end(success=False, steps=0, score=0.0, rewards=[])
            return

        log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

        rewards: List[float] = []
        steps_taken = 0
        score = 0.0
        success = False
        last_error: Optional[str] = None

        try:
            obs = env_reset(http, TASK_NAME)
            done = obs.get("done", False)

            for step in range(1, MAX_STEPS + 1):
                if done:
                    break

                # Ask LLM
                action_idx: Optional[int] = None
                for _attempt in range(3):
                    try:
                        completion = llm.chat.completions.create(
                            model=MODEL_NAME,
                            messages=[
                                {
                                    "role": "system",
                                    "content": (
                                        "You are an expert air traffic controller AI. "
                                        "Respond only with JSON."
                                    ),
                                },
                                {"role": "user", "content": build_prompt(obs)},
                            ],
                            temperature=0.0,
                            max_tokens=100,
                        )
                        action_idx = parse_action(completion.choices[0].message.content or "")
                        if action_idx is not None:
                            break
                    except Exception as exc:
                        last_error = str(exc)
                        time.sleep(1)

                if action_idx is None:
                    action_idx = 0
                    last_error = "parse_failed"

                # Step environment
                try:
                    step_result = env_step(http, action_idx)
                    step_obs = step_result.get("observation") or step_result
                    reward = float(step_result.get("reward") or 0.0)
                    done = step_result.get("done", False) or step_obs.get("done", False)
                    obs = step_obs if "flights" in step_obs else obs
                    last_error = step_obs.get("last_action_error") or None
                except Exception as exc:
                    reward = 0.0
                    last_error = str(exc)
                    done = True

                rewards.append(reward)
                steps_taken = step
                action_str = f"flight_index={action_idx}"
                log_step(step=step, action=action_str, reward=reward, done=done, error=last_error)

                if done:
                    break

            # Grade
            try:
                grade = env_grade(http)
                score = float(grade.get("score", 0.0))
            except Exception:
                score = 0.0

            success = score >= SUCCESS_THRESHOLD

        except Exception as exc:
            last_error = str(exc)
            print(f"[DEBUG] Episode error: {exc}", flush=True)

        finally:
            log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
            http.close()

    finally:
        if docker_proc is not None:
            docker_proc.terminate()


if __name__ == "__main__":
    main()
