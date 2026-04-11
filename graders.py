"""SUPERCELL — Deterministic graders for the VABB Mumbai ATC environment.

Each grader returns a score in the STRICT open interval (0.01, 0.99).

Why not [0.0, 1.0]? The hackathon's Task Validation phase rejects
scores of exactly 0.0 or 1.0 — such extremes are indistinguishable
from a dummy "always 0" or "always 1" grader and indicate a
non-functional grading signal. All outputs are clamped through
`strict_score()` so perfect and catastrophic episodes still return
meaningful-but-distinct values (0.99 vs 0.01) that the validator
accepts as real grading output.

Graders are pure functions of landing_log + crash_log, so identical
episodes always return identical scores (required by the spec).
"""

from __future__ import annotations

import math
from typing import Any, Callable


# =============================================================================
# Helpers
# =============================================================================

# Strict open interval (0.0, 1.0) — never return exactly 0 or 1.
MIN_STRICT_SCORE = 0.01
MAX_STRICT_SCORE = 0.99


def strict_score(value: float) -> float:
    """Clamp a raw score into the strict open interval (0.01, 0.99).

    The hackathon task validator considers exact 0.0 or 1.0 scores as
    evidence of a non-working grader, so every public score is pushed
    at least MIN_STRICT_SCORE away from 0 and MAX_STRICT_SCORE away
    from 1.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return MIN_STRICT_SCORE
    if math.isnan(v) or math.isinf(v):
        return MIN_STRICT_SCORE
    if v <= 0.0:
        return MIN_STRICT_SCORE
    if v >= 1.0:
        return MAX_STRICT_SCORE
    return max(MIN_STRICT_SCORE, min(MAX_STRICT_SCORE, v))


def _clamp(x: float) -> float:
    """Internal clamp to [0, 1] — used before the final strict clamp."""
    return max(0.0, min(1.0, x))


def _ratio(num: float, denom: float) -> float:
    return num / denom if denom > 0 else 0.0


# =============================================================================
# Task-specific graders
# =============================================================================


def _efficiency(landed: int, steps: int, total: int, max_steps: int) -> float:
    """Time-efficiency — only credited when at least one flight landed.

    A freshly-reset (un-played) episode yields 0.0 here, preventing
    "no-op" bonuses.
    """
    if landed == 0 or steps == 0:
        return 0.0
    return _clamp(1.0 - _ratio(max(0, steps - total * 2), max_steps))


def grade_easy(
    landing_log: list[dict[str, Any]],
    crash_log: list[dict[str, Any]],
    total: int,
    steps: int,
    max_steps: int,
) -> float:
    """Winter Haze — simple clear-sky scenario.

    40% safety · 40% priority ordering · 20% efficiency.
    """
    if total == 0:
        return 0.0

    landed = len(landing_log)
    safety = _ratio(landed, total)

    # Priority = fraction of landings that were MAYDAY/PAN-PAN when such
    # flights existed in the scenario. Since easy has 1 MAYDAY + 1 PAN-PAN,
    # reward landing them at all.
    priority_landings = sum(
        1 for e in landing_log if e.get("emergency") in ("MAYDAY", "PAN_PAN")
    )
    priority = _ratio(priority_landings, min(2, total))

    efficiency = _efficiency(landed, steps, total, max_steps)
    crash_penalty = _ratio(len(crash_log), total) * 0.50

    score = 0.40 * safety + 0.40 * priority + 0.20 * efficiency - crash_penalty
    return strict_score(_clamp(score))


def grade_medium(
    landing_log: list[dict[str, Any]],
    crash_log: list[dict[str, Any]],
    total: int,
    steps: int,
    max_steps: int,
) -> float:
    """Pre-Monsoon Squall — weather window management.

    30% safety · 25% priority · 15% medical · 15% fuel management · 15% efficiency.
    """
    if total == 0:
        return 0.0

    landed = len(landing_log)
    landed_and_crashed = landed + len(crash_log)
    safety = _ratio(landed, total)
    # Priority: of all emergency flights in the scenario, how many were
    # safely landed (rather than crashed or left stranded).
    total_emergencies = sum(
        1 for e in landing_log + crash_log if e.get("emergency") in ("MAYDAY", "PAN_PAN")
    )
    emergency_landed = sum(
        1 for e in landing_log if e.get("emergency") in ("MAYDAY", "PAN_PAN")
    )
    priority = _ratio(emergency_landed, max(1, total_emergencies))
    medical_total = sum(
        1 for e in landing_log + crash_log if e.get("medical_onboard")
    )
    medical = _ratio(
        sum(1 for e in landing_log if e.get("medical_onboard")),
        max(1, medical_total),
    )
    # Fuel management — reward landings that had fuel reserve left
    fuel_ok = sum(1 for e in landing_log if e.get("fuel_on_landing", 0) > 3)
    fuel_score = _ratio(fuel_ok, max(1, landed))
    efficiency = _efficiency(landed, steps, total, max_steps)
    crash_penalty = _ratio(len(crash_log), total) * 0.40

    score = (
        0.30 * safety
        + 0.25 * priority
        + 0.15 * medical
        + 0.15 * fuel_score
        + 0.15 * efficiency
        - crash_penalty
    )
    return strict_score(_clamp(score))


def grade_hard(
    landing_log: list[dict[str, Any]],
    crash_log: list[dict[str, Any]],
    total: int,
    steps: int,
    max_steps: int,
) -> float:
    """Mumbai Monsoon Surge — fuel traps and weather gates.

    30% safety · 20% priority · 10% medical · 20% fuel management ·
    10% efficiency · 10% perfect-run bonus.
    """
    if total == 0:
        return 0.0

    landed = len(landing_log)
    safety = _ratio(landed, total)
    # Priority: of all MAYDAY flights in the scenario, how many landed safely
    total_maydays = sum(
        1 for e in landing_log + crash_log if e.get("emergency") == "MAYDAY"
    )
    mayday_landed = sum(1 for e in landing_log if e.get("emergency") == "MAYDAY")
    priority = _ratio(mayday_landed, max(1, total_maydays))
    medical_total = sum(
        1 for e in landing_log + crash_log if e.get("medical_onboard")
    )
    medical = _ratio(
        sum(1 for e in landing_log if e.get("medical_onboard")),
        max(1, medical_total),
    )
    # Hard task has true fuel traps — reward keeping reserve above 5 min
    fuel_ok = sum(1 for e in landing_log if e.get("fuel_on_landing", 0) > 5)
    fuel_score = _ratio(fuel_ok, max(1, landed))
    efficiency = _efficiency(landed, steps, total, max_steps)
    crash_penalty = _ratio(len(crash_log), total) * 0.35
    perfect_bonus = 0.10 if (len(crash_log) == 0 and landed == total) else 0.0

    score = (
        0.30 * safety
        + 0.20 * priority
        + 0.10 * medical
        + 0.20 * fuel_score
        + 0.10 * efficiency
        + perfect_bonus
        - crash_penalty
    )
    return strict_score(_clamp(score))


def grade_extra_hard(
    landing_log: list[dict[str, Any]],
    crash_log: list[dict[str, Any]],
    total: int,
    steps: int,
    max_steps: int,
) -> float:
    """Total System Chaos — hidden bonus task, stricter weights."""
    if total == 0:
        return 0.0

    landed = len(landing_log)
    safety = _ratio(landed, total)
    total_maydays = sum(
        1 for e in landing_log + crash_log if e.get("emergency") == "MAYDAY"
    )
    mayday_landed = sum(1 for e in landing_log if e.get("emergency") == "MAYDAY")
    priority = _ratio(mayday_landed, max(1, total_maydays))
    medical_total = sum(
        1 for e in landing_log + crash_log if e.get("medical_onboard")
    )
    medical = _ratio(
        sum(1 for e in landing_log if e.get("medical_onboard")),
        max(1, medical_total),
    )
    fuel_ok = sum(1 for e in landing_log if e.get("fuel_on_landing", 0) > 3)
    fuel_score = _ratio(fuel_ok, max(1, landed))
    # Extra hard uses throughput efficiency (landings per step), zeroed for no-op episodes
    if landed == 0 or steps == 0:
        efficiency = 0.0
    else:
        efficiency = _clamp(_ratio(total, max(1, steps)))
    perfect_bonus = 0.10 if (len(crash_log) == 0 and landed == total) else 0.0
    crash_penalty = _ratio(len(crash_log), total) * 0.30

    score = (
        0.25 * safety
        + 0.20 * priority
        + 0.15 * medical
        + 0.20 * fuel_score
        + 0.10 * efficiency
        + perfect_bonus
        - crash_penalty
    )
    return strict_score(_clamp(score))


# =============================================================================
# Registry
# =============================================================================


GRADERS: dict[str, Callable[..., float]] = {
    "easy": grade_easy,
    "medium": grade_medium,
    "hard": grade_hard,
    "extra_hard": grade_extra_hard,
}


def grade_episode(
    landing_log: list[dict[str, Any]],
    crash_log: list[dict[str, Any]],
    total: int,
    steps: int,
    max_steps: int,
    task_id: str,
) -> float:
    grader = GRADERS.get(task_id, grade_easy)
    return strict_score(grader(landing_log, crash_log, total, steps, max_steps))
