#!/usr/bin/env python3
"""
SUPERCELL — VABB Mumbai ATC Emergency Triage
OpenEnv hackathon baseline inference script.

Required environment variables (per hackathon spec):
    API_BASE_URL       LLM endpoint          (default: https://router.huggingface.co/v1)
    MODEL_NAME         Model identifier       (default: Qwen/Qwen2.5-72B-Instruct)
    HF_TOKEN           HuggingFace / API key

Optional:
    ENV_URL            Running environment URL      (default: http://localhost:7860)
    LOCAL_IMAGE_NAME   Docker image to boot locally (default: unset — expects ENV_URL live)
    SUPERCELL_TASK     Task id: easy | medium | hard | extra_hard  (default: hard)

Stdout format (strict — parsed by the hackathon validator):
    [START] task=<task> env=supercell model=<model>
    [STEP]  step=<n> action=<str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...,rn>

All rewards and scores are formatted to 2 decimal places.
Boolean fields are lowercase. Error is the raw error string or the literal "null".
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Optional

# =============================================================================
# Import OpenAI with a stdlib fallback.
#
# The hackathon spec asks participants to "use the OpenAI Client for all LLM
# calls", but the validator sandbox that runs inference.py may not have the
# `openai` package installed. If the import fails we fall back to a thin
# urllib-based shim that targets the same OpenAI-compatible /chat/completions
# endpoint, so inference.py still runs to completion and emits a valid
# [START] / [STEP] / [END] stream instead of crashing on import.
# =============================================================================
try:
    from openai import OpenAI  # type: ignore[import-not-found]
    _OPENAI_CLIENT_SOURCE = "openai"
except Exception:  # pragma: no cover — fallback exercised in validator sandboxes
    import urllib.error  # noqa: F401  (already imported below, kept for clarity)

    class _FallbackMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class _FallbackChoice:
        def __init__(self, content: str) -> None:
            self.message = _FallbackMessage(content)

    class _FallbackCompletion:
        def __init__(self, content: str) -> None:
            self.choices = [_FallbackChoice(content)]

    class _FallbackCompletionsAPI:
        def __init__(self, base_url: str, api_key: str) -> None:
            self._base_url = base_url.rstrip("/")
            self._api_key = api_key

        def create(
            self,
            model: str,
            messages: list,
            temperature: float = 0.0,
            max_tokens: int = 100,
            stream: bool = False,
            **_: object,
        ) -> "_FallbackCompletion":
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
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

    class _FallbackChatAPI:
        def __init__(self, base_url: str, api_key: str) -> None:
            self.completions = _FallbackCompletionsAPI(base_url, api_key)

    class OpenAI:  # type: ignore[no-redef]
        """Stdlib-only OpenAI-compatible client shim used when `openai` is absent."""

        def __init__(self, base_url: str, api_key: str, **_: object) -> None:
            self.chat = _FallbackChatAPI(base_url, api_key)

    _OPENAI_CLIENT_SOURCE = "urllib-fallback"


# =============================================================================
# Configuration
# =============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
ENV_URL: str = os.getenv("ENV_URL", "http://localhost:7860")
# (LOCAL_IMAGE_NAME already declared above with other env vars)
TASK_NAME: str = os.getenv("SUPERCELL_TASK", "hard")
BENCHMARK: str = "supercell"

MAX_STEPS: int = 70
SUCCESS_THRESHOLD: float = 0.40
LLM_TIMEOUT_SECONDS: float = 30.0
LLM_TEMPERATURE: float = 0.0
LLM_MAX_TOKENS: int = 80


# =============================================================================
# Structured stdout — exact format required by the hackathon validator
# =============================================================================


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int,
    action: str,
    reward: float,
    done: bool,
    error: Optional[str],
) -> None:
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# =============================================================================
# Tiny stdlib HTTP client — no extra runtime deps
# =============================================================================


class EnvClient:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self, method: str, path: str, payload: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}

    def get(self, path: str) -> dict[str, Any]:
        return self.request("GET", path)

    def post(
        self, path: str, payload: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        return self.request("POST", path, payload)


def env_reset(http: EnvClient, task_id: str) -> dict[str, Any]:
    return http.post("/reset", {"episode_id": task_id})


def env_step(http: EnvClient, flight_index: int) -> dict[str, Any]:
    return http.post("/step", {"action": {"flight_index": flight_index}})


def env_grade(http: EnvClient) -> dict[str, Any]:
    return http.post("/grade")


# =============================================================================
# Optional Docker bootstrap — only used if LOCAL_IMAGE_NAME is set
# =============================================================================


def _wait_for_health(url: str, timeout_s: int = 90) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=3.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def start_docker_container(image: str) -> tuple[subprocess.Popen[bytes], str]:
    print(f"[DEBUG] Booting container from image: {image}", file=sys.stderr, flush=True)
    proc = subprocess.Popen(
        ["docker", "run", "--rm", "-p", "7860:7860", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = "http://localhost:7860"
    if not _wait_for_health(url):
        print("[DEBUG] Container failed health check", file=sys.stderr, flush=True)
    return proc, url


# =============================================================================
# Prompt building and action parsing
# =============================================================================

SYSTEM_PROMPT = (
    "You are the Tower Controller at VABB (Chhatrapati Shivaji Intl, Mumbai) "
    "during monsoon operations. Your job is to sequence emergency landings on a "
    "single active runway. You must decide which inbound flight to clear to land "
    "next.\n\n"
    "Priority guidance (soft — use your judgment):\n"
    "  MAYDAY > PAN-PAN > medical_onboard > lowest fuel > highest passengers\n\n"
    "Rules:\n"
    "  - A flight cannot land if its min_visibility_nm exceeds current weather visibility.\n"
    "  - Heavy/SUPER wake aircraft block the runway for longer.\n"
    "  - Every step all airborne flights burn 1 minute of fuel.\n\n"
    'Respond ONLY with a JSON object of the form {"flight_index": N} '
    "where N is the 0-based index of the flight to clear next. No prose, no markdown."
)


def build_user_prompt(observation_payload: dict[str, Any]) -> str:
    obs = observation_payload.get("observation", {})
    task_name = obs.get("task_name", "Unknown")
    task_id = obs.get("task_id", "unknown")
    time_step = obs.get("time_step", 0)
    max_steps = obs.get("max_time_steps", 50)
    landed = obs.get("landed_safely", 0)
    crashed = obs.get("crashed", 0)
    runway_free = obs.get("runway_free_in_steps", 0)

    weather = obs.get("weather", {})
    vis = weather.get("visibility_nm", 10.0)
    precip = weather.get("precipitation", "none")
    trend = weather.get("trend", "stable")
    wind = weather.get("wind_knots", 0.0)

    flights = obs.get("flights", [])

    lines = [
        f"VABB TOWER — {task_name} ({task_id})",
        f"Step {time_step}/{max_steps}  |  Landed {landed}  |  Crashed {crashed}  "
        f"|  Runway free in {runway_free} step(s)",
        f"Weather: {vis:.1f} nm visibility, {precip}, {trend}, wind {wind:.0f} kt",
        "",
        "Inbound traffic:",
    ]
    for f in flights:
        idx = f.get("index", 0)
        callsign = f.get("callsign", "UNK")
        aircraft = f.get("aircraft_type", "")
        emergency = f.get("emergency", "NONE")
        fuel = f.get("fuel_minutes", 0)
        pax = f.get("passengers", 0)
        medical = " MED" if f.get("medical_onboard") else ""
        min_vis = f.get("min_visibility_nm", 1.0)
        fix = f.get("approach_fix", "---")
        can = "CLEAR" if f.get("can_land_now") else "BLOCKED"
        wake = f.get("wake_category", "MEDIUM")
        lines.append(
            f"  [{idx}] {callsign:<10} {aircraft:<18} {emergency:<8}{medical:<4} "
            f"fuel={fuel:>4.0f}m pax={pax:<4} min_vis={min_vis:.1f}nm "
            f"fix={fix:<6} wake={wake:<6} {can}"
        )
    lines.append("")
    lines.append('Respond with exactly: {"flight_index": N}')
    return "\n".join(lines)


def parse_action(content: str) -> Optional[int]:
    text = (content or "").strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    try:
        data = json.loads(text)
    except Exception:
        # Fallback: extract first integer
        digits = "".join(c if c.isdigit() else " " for c in text).split()
        if digits:
            try:
                return int(digits[0])
            except ValueError:
                return None
        return None
    idx = data.get("flight_index")
    if isinstance(idx, int) and idx >= 0:
        return idx
    return None


def call_llm(client: OpenAI, user_prompt: str) -> tuple[Optional[int], Optional[str]]:
    """Ask the model for an action. Returns (flight_index, error_message)."""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
        content = completion.choices[0].message.content or ""
        return parse_action(content), None
    except Exception as exc:
        return None, f"llm_error: {exc}"


# =============================================================================
# Episode loop
# =============================================================================


def run_episode() -> None:
    docker_proc: Optional[subprocess.Popen[bytes]] = None
    active_url = ENV_URL

    rewards: list[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    started = False  # whether [START] was emitted

    try:
        if LOCAL_IMAGE_NAME:
            docker_proc, active_url = start_docker_container(LOCAL_IMAGE_NAME)

        if not HF_TOKEN:
            log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
            started = True
            print("[DEBUG] Missing HF_TOKEN/HF_TOKEN", file=sys.stderr, flush=True)
            return

        http = EnvClient(base_url=active_url, timeout=30.0)
        try:
            http.get("/health")
        except Exception as exc:
            log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
            started = True
            print(
                f"[DEBUG] Cannot reach environment at {active_url}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            return

        client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
        print(
            f"[DEBUG] LLM client source: {_OPENAI_CLIENT_SOURCE}",
            file=sys.stderr,
            flush=True,
        )

        log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
        started = True

        obs_payload = env_reset(http, TASK_NAME)
        done = obs_payload.get("observation", {}).get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            prompt = build_user_prompt(obs_payload)
            action_idx, llm_error = call_llm(client, prompt)
            if action_idx is None:
                action_idx = 0  # Safe fallback — index 0 always exists when not done

            # Clamp to current flight count to avoid /step rejecting it
            flights_count = len(obs_payload.get("observation", {}).get("flights", []))
            if flights_count > 0:
                action_idx = max(0, min(action_idx, flights_count - 1))

            step_error: Optional[str] = llm_error
            try:
                result = env_step(http, action_idx)
            except Exception as exc:
                step_error = f"step_error: {exc}"
                log_step(step=step, action=f"land({action_idx})",
                         reward=0.0, done=False, error=step_error)
                break

            obs_payload = result
            reward = float(result.get("reward", 0.0))
            done = bool(result.get("observation", {}).get("done", False))

            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step,
                action=f"land({action_idx})",
                reward=reward,
                done=done,
                error=step_error,
            )

            if done:
                break

        try:
            grade_result = env_grade(http)
            score = float(grade_result.get("score", 0.0))
        except Exception as exc:
            print(f"[DEBUG] Grade request failed: {exc}", file=sys.stderr, flush=True)
            score = 0.0

        score = max(0.0, min(1.0, score))
        success = score >= SUCCESS_THRESHOLD

    finally:
        if docker_proc is not None:
            try:
                docker_proc.terminate()
                docker_proc.wait(timeout=10)
            except Exception:
                try:
                    docker_proc.kill()
                except Exception:
                    pass
        # Always emit exactly one [END] line matching the [START] above.
        if not started:
            log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    run_episode()
