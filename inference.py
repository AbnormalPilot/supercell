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
    SUPERCELL_TASK      Task to run: easy | medium | hard | extra_hard  (default: hard)

Stdout format (required by hackathon):
    [START] task=<task> env=supercell model=<model>
    [STEP]  step=<n> action=<str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import List, Optional

try:
    from openai import OpenAI
except Exception:
    # Fallback for missing openai package
    class _FallbackMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class _FallbackChoice:
        def __init__(self, content: str) -> None:
            self.message = _FallbackMessage(content)

    class _FallbackCompletion:
        def __init__(self, content: str) -> None:
            self.choices = [_FallbackChoice(content)]

    class _FallbackCompletions:
        def __init__(self, base_url: str, api_key: str) -> None:
            self._base_url = base_url.rstrip("/")
            self._api_key = api_key

        def create(
            self,
            model: str,
            messages: list[dict],
            temperature: float = 0.0,
            max_tokens: int = 100,
        ) -> "_FallbackCompletion":
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            req = urllib.request.Request(
                f"{self._base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = (
                (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
                or '{"flight_index": 0}'
            )
            return _FallbackCompletion(content)

    class _FallbackChat:
        def __init__(self, base_url: str, api_key: str) -> None:
            self.completions = _FallbackCompletions(base_url, api_key)

    class OpenAI:  # type: ignore[override]
        def __init__(self, base_url: str, api_key: str) -> None:
            self.chat = _FallbackChat(base_url, api_key)

# ── Configuration ────────────────────────────────────────────────────────────
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
TASK_NAME = os.getenv("SUPERCELL_TASK", "hard")
BENCHMARK = "supercell"
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
MAX_STEPS = 70
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
            req = urllib.request.Request(f"{url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def start_docker_container(image_name: str) -> tuple:
    """Start the environment Docker container."""
    print(f"[DEBUG] Starting Docker container from image: {image_name}", flush=True)
    
    # Run container
    proc = subprocess.Popen(
        ["docker", "run", "--rm", "-p", "7860:7860", image_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for health check
    url = "http://localhost:7860"
    if _wait_for_health(url, timeout=60):
        print(f"[DEBUG] Container healthy at {url}", flush=True)
        return proc, url
    else:
        print("[DEBUG] Container failed to become healthy", flush=True)
        proc.terminate()
        return proc, url


class EnvClient:
    """Tiny stdlib HTTP client to avoid external runtime deps."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        body = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw.strip():
                return {}
            return json.loads(raw)

    def get(self, path: str) -> dict:
        return self.request("GET", path)

    def post(self, path: str, payload: Optional[dict] = None) -> dict:
        return self.request("POST", path, payload)

    def close(self) -> None:
        return


def env_reset(http: EnvClient, task_id: str) -> dict:
    return http.post("/reset", {"episode_id": task_id})


def env_step(http: EnvClient, flight_index: int) -> dict:
    return http.post("/step", {"action": {"flight_index": flight_index}})


def env_grade(http: EnvClient) -> dict:
    return http.post("/grade")


def build_prompt(obs: dict) -> str:
    """Build prompt for LLM from observation."""
    task_id = obs.get("observation", {}).get("task_id", "unknown")
    task_name = obs.get("observation", {}).get("task_name", "Unknown")
    time_step = obs.get("observation", {}).get("time_step", 0)
    max_steps = obs.get("observation", {}).get("max_time_steps", 50)
    landed = obs.get("observation", {}).get("landed_safely", 0)
    crashed = obs.get("observation", {}).get("crashed", 0)
    runway_free = obs.get("observation", {}).get("runway_free_in_steps", 0)
    
    weather = obs.get("observation", {}).get("weather", {})
    vis = weather.get("visibility_nm", 10.0)
    precip = weather.get("precipitation", "none")
    
    flights = obs.get("observation", {}).get("flights", [])
    
    prompt = f"""You are an expert Air Traffic Controller AI managing emergency landings.

TASK: {task_name} ({task_id})
Time: Step {time_step}/{max_steps} | Runway free in: {runway_free} steps
Weather: {vis} nm visibility, {precip}
Landed: {landed} | Crashed: {crashed}

ACTIVE FLIGHTS:
"""
    
    for f in flights:
        idx = f.get("index", 0)
        callsign = f.get("callsign", "UNK")
        emergency = f.get("emergency", "NONE")
        fuel = f.get("fuel_minutes", 0)
        pax = f.get("passengers", 0)
        med = " 🏥 MEDICAL" if f.get("medical_onboard") else ""
        min_vis = f.get("min_visibility_nm", 1.0)
        can_land = "✅ CAN LAND" if f.get("can_land_now") else "❌ CANNOT LAND"
        
        prompt += f"[{idx}] {callsign} | {emergency}{med} | Fuel: {fuel:.0f}m | Pax: {pax} | MinVis: {min_vis}nm | {can_land}\n"
    
    prompt += """
RULES:
1. Select flight index (0-N) to land next
2. Prioritize: MAYDAY > PAN-PAN > medical > low fuel > high passengers
3. Only land if "CAN LAND" (weather permits)
4. Heavy aircraft need separation time

Respond ONLY with JSON: {"flight_index": N}
"""
    return prompt


def parse_action(content: str) -> Optional[int]:
    """Parse flight_index from LLM response."""
    try:
        # Try to find JSON in the response
        content = content.strip()
        # Extract JSON if wrapped in markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        data = json.loads(content)
        idx = data.get("flight_index")
        if isinstance(idx, int) and idx >= 0:
            return idx
    except Exception:
        pass
    return None


def main() -> None:
    docker_proc = None
    active_url = ENV_URL

    try:
        # Start docker container if image name provided
        if LOCAL_IMAGE_NAME:
            docker_proc, active_url = start_docker_container(LOCAL_IMAGE_NAME)

        if not API_KEY:
            print("[DEBUG] Missing HF_TOKEN/API_KEY environment variable", flush=True)
            log_end(success=False, steps=0, score=0.0, rewards=[])
            return

        llm = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
        http = EnvClient(base_url=active_url, timeout=30.0)

        # Verify health
        try:
            http.get("/health")
        except Exception as e:
            print(f"[DEBUG] Cannot reach environment at {active_url}: {e}", flush=True)
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
            done = obs.get("observation", {}).get("done", False)

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
                                        "Respond only with JSON like {\"flight_index\": 0}"
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
                    except Exception as e:
                        print(f"[DEBUG] LLM attempt {_attempt+1} failed: {e}", flush=True)
                        last_error = str(e)

                if action_idx is None:
                    action_idx = 0  # Fallback

                # Execute action
                result = env_step(http, action_idx)
                obs = result
                
                reward = result.get("reward", 0.0)
                done = result.get("observation", {}).get("done", False)
                
                rewards.append(reward)
                steps_taken = step
                
                action_str = f'land({action_idx})'
                log_step(step=step, action=action_str, reward=reward, done=done, error=last_error)
                last_error = None

                if done:
                    break

            # Get final score
            grade_result = env_grade(http)
            score = grade_result.get("score", 0.0)
            success = score >= SUCCESS_THRESHOLD

        except Exception as e:
            print(f"[DEBUG] Episode error: {e}", flush=True)
            last_error = str(e)

    finally:
        # Cleanup
        if docker_proc is not None:
            print("[DEBUG] Stopping Docker container", flush=True)
            docker_proc.terminate()
            try:
                docker_proc.wait(timeout=10)
            except Exception:
                docker_proc.kill()
        
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    main()
