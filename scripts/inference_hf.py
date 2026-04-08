#!/usr/bin/env python3
"""PyTorch + Hugging Face inference baseline for ATC-Triage-v1.

Uses Meta's Llama models via Hugging Face transformers (local GPU/CPU)
or the HF Inference API (remote, no GPU required).

Required environment variables:
    HF_TOKEN      -- Hugging Face access token (for gated models / Inference API)
    MODEL_NAME    -- HF model identifier (default: meta-llama/Llama-3.2-3B-Instruct)
    USE_LOCAL     -- "true" to load model locally with PyTorch; "false" for HF Inference API
    ENV_URL       -- ATC environment server URL (default: http://localhost:8000)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Protocol

# Ensure apps/api is importable (models, client live there)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "apps", "api"))

from client import ATCClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME: str = os.environ.get(
    "MODEL_NAME", "meta-llama/Llama-3.2-3B-Instruct"
)
HF_TOKEN: str = os.environ.get("HF_TOKEN", "")
USE_LOCAL: bool = os.environ.get("USE_LOCAL", "false").lower() in ("true", "1", "yes")
ENV_URL: str = os.environ.get("ENV_URL", "http://localhost:8000")

TASKS: list[str] = ["easy", "medium", "hard"]
MAX_RETRIES: int = 3  # retries per LLM call on parse failure


# ---------------------------------------------------------------------------
# Inference backend protocol
# ---------------------------------------------------------------------------

class InferenceBackend(Protocol):
    """Minimal interface shared by local and remote backends."""

    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


# ---------------------------------------------------------------------------
# Local PyTorch backend (transformers + torch)
# ---------------------------------------------------------------------------

class LocalBackend:
    """Loads a Hugging Face causal-LM locally using PyTorch."""

    def __init__(self, model_name: str, token: str) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._torch = torch
        device_label = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        print(f"  Loading tokenizer: {model_name}")
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            token=token or None,
            trust_remote_code=True,
        )

        print(f"  Loading model on {device_label} ({dtype})")
        self._model = AutoModelForCausalLM.from_pretrained(
            model_name,
            token=token or None,
            torch_dtype=dtype,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True,
        )
        if not torch.cuda.is_available():
            self._model = self._model.to(device_label)

        self._model.eval()
        self._device = device_label
        print(f"  Model loaded successfully on {device_label}")

    # ------------------------------------------------------------------

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        torch = self._torch
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Use chat template if the tokenizer provides one
        if hasattr(self._tokenizer, "apply_chat_template"):
            input_text: str = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            # Fallback: concatenate system + user
            input_text = f"{system_prompt}\n\n{user_prompt}\n\nResponse:"

        inputs = self._tokenizer(input_text, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self._device)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self._device)

        with torch.no_grad():
            output_ids = self._model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_new_tokens=100,
                temperature=0.1,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        # Decode only the newly generated tokens
        generated_ids = output_ids[0, input_ids.shape[1]:]
        return self._tokenizer.decode(generated_ids, skip_special_tokens=True)


# ---------------------------------------------------------------------------
# Remote HF Inference API backend
# ---------------------------------------------------------------------------

class RemoteBackend:
    """Calls the Hugging Face Inference API (no local GPU needed)."""

    def __init__(self, model_name: str, token: str) -> None:
        from huggingface_hub import InferenceClient

        self._client = InferenceClient(model=model_name, token=token or None)
        self._model_name = model_name
        print(f"  Using HF Inference API: {model_name}")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = self._client.chat_completion(
            messages=messages,
            max_tokens=100,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Prompt building (mirrors inference.py)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an expert air traffic controller AI. "
    "Respond only with JSON."
)


def build_prompt(observation: dict) -> str:
    """Convert an ATC observation dict into a prompt for the LLM."""
    obs = observation.get("observation", observation)
    flights = obs.get("flights", [])
    weather = obs.get("weather", {})

    lines = [
        "You are an expert air traffic controller. "
        "You must decide which flight to clear for landing next.",
        "",
        "=== WEATHER ===",
        f"Visibility: {weather.get('visibility_nm', '?')} nm | "
        f"Wind: {weather.get('wind_knots', '?')} kt | "
        f"Crosswind: {weather.get('crosswind_knots', '?')} kt | "
        f"Precipitation: {weather.get('precipitation', 'none')} | "
        f"Trend: {weather.get('trend', 'stable')}",
        "",
        "=== RUNWAY ===",
        f"Free in: {obs.get('runway_free_in_steps', 0)} steps | "
        f"Time step: {obs.get('time_step', 0)}/{obs.get('max_time_steps', '?')} | "
        f"Landed: {obs.get('landed_safely', 0)} | "
        f"Crashed: {obs.get('crashed', 0)} | "
        f"Total: {obs.get('total_flights', '?')}",
        "",
        "=== PENDING FLIGHTS ===",
    ]

    for f in flights:
        status_parts: list[str] = []
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
            f"  [{f['index']}] {f['callsign']} ({f['aircraft_type']}) -- "
            f"Emergency: {f.get('emergency', 'NONE')} | "
            f"Fuel: {f.get('fuel_minutes', '?')} min | "
            f"Pax: {f.get('passengers', '?')} | "
            f"Vis min: {f.get('min_visibility_nm', '?')} nm | "
            f"Wake: {f.get('wake_category', '?')} | "
            f"Status: {status}"
        )

    lines.extend([
        "",
        "RULES:",
        "- MAYDAY flights are in immediate danger -- prioritize by fuel remaining",
        "- Flights with <10 min fuel will crash if not landed soon "
        "(fuel burns ~1 min per separation step)",
        "- PAN-PAN / medical passengers are urgent but not immediately "
        "life-threatening",
        "- Flights that 'CANNOT LAND' in current weather should be deferred "
        "unless weather is improving",
        "- Each landing uses 2-4 steps of separation time; all waiting "
        "flights burn fuel",
        "- More passengers = higher stakes",
        "",
        'Respond with ONLY a JSON object: {"flight_index": <index>}',
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Action parsing (mirrors inference.py)
# ---------------------------------------------------------------------------

def parse_action(response_text: str) -> int | None:
    """Extract flight_index from LLM response text."""
    text = response_text.strip()

    # Try JSON parse
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            if "flight_index" in data:
                return int(data["flight_index"])
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fallback: look for flight_index key pattern
    match = re.search(r"flight_index[\"'\s:]+(\d+)", text)
    if match:
        return int(match.group(1))

    # Last resort: first digit
    match = re.search(r"\d+", text)
    if match:
        return int(match.group(0))

    return None


# ---------------------------------------------------------------------------
# Task runner
# ---------------------------------------------------------------------------

def run_task(
    backend: InferenceBackend,
    env: ATCClient,
    task_id: str,
) -> dict:
    """Run a single task episode and return results."""
    print(f"\n{'=' * 60}")
    print(f"  Task: {task_id}")
    print(f"{'=' * 60}")

    obs = env.reset(task_id=task_id)
    done = obs.get("done", False)
    step_num = 0

    while not done:
        prompt = build_prompt(obs)

        # Call LLM with retries
        action_idx: int | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response_text = backend.generate(SYSTEM_PROMPT, prompt)
                action_idx = parse_action(response_text)
                if action_idx is not None:
                    break
            except Exception as exc:
                print(f"  LLM error (attempt {attempt + 1}): {exc}")
                time.sleep(1)

        if action_idx is None:
            action_idx = 0  # fallback: pick first flight
            print(
                f"  Step {step_num}: Failed to parse LLM response, "
                "defaulting to index 0"
            )

        # Step the environment
        obs = env.step(action_idx)
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

    # Grade the episode
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


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------

def create_backend(
    model_name: str,
    token: str,
    *,
    use_local: bool,
) -> InferenceBackend:
    """Instantiate the appropriate inference backend."""
    if use_local:
        return LocalBackend(model_name=model_name, token=token)
    return RemoteBackend(model_name=model_name, token=token)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> list[dict]:
    print("=" * 60)
    print("  ATC-Triage-v1  --  PyTorch / Llama Inference Baseline")
    print("=" * 60)
    print(f"  Model:       {MODEL_NAME}")
    print(f"  Backend:     {'local (PyTorch)' if USE_LOCAL else 'HF Inference API'}")
    print(f"  Environment: {ENV_URL}")
    print()

    if not HF_TOKEN:
        print(
            "WARNING: HF_TOKEN is not set. "
            "You may need it for gated models or the Inference API."
        )

    # Build backend
    try:
        backend = create_backend(
            model_name=MODEL_NAME,
            token=HF_TOKEN,
            use_local=USE_LOCAL,
        )
    except ImportError as exc:
        missing = str(exc)
        print(f"ERROR: Missing dependency: {missing}")
        if USE_LOCAL:
            print(
                "Install PyTorch + transformers for local inference:\n"
                "  pip install torch transformers"
            )
        else:
            print(
                "Install huggingface_hub for remote inference:\n"
                "  pip install huggingface_hub"
            )
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Failed to initialize backend: {exc}")
        sys.exit(1)

    # Connect to the ATC environment server
    env = ATCClient(base_url=ENV_URL)
    try:
        health = env.health()
        print(f"  Server health: {health['status']}")
    except Exception as exc:
        print(f"ERROR: Cannot reach environment server at {ENV_URL}: {exc}")
        print("Start the server first: uv run python -m server.app")
        sys.exit(1)

    # Run all tasks
    results: list[dict] = []
    for task_id in TASKS:
        result = run_task(backend, env, task_id)
        results.append(result)

    # Summary
    print(f"\n{'=' * 60}")
    print("  RESULTS SUMMARY")
    print(f"{'=' * 60}")
    print(
        f"  {'Task':<10} {'Score':>8} {'Steps':>6} "
        f"{'Landed':>7} {'Crashed':>8} {'Reward':>10}"
    )
    print(
        f"  {'-' * 10} {'-' * 8} {'-' * 6} "
        f"{'-' * 7} {'-' * 8} {'-' * 10}"
    )
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
