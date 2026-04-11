"""SUPERCELL — Deterministic graders for the VABB Mumbai ATC environment.

Each grader returns a score in [0.0, 1.0]. Graders are pure functions of
the episode's landing_log and crash_log, so the same episode always
produces the same score (required by the hackathon spec).
"""

from __future__ import annotations

from typing import Any, Callable


# =============================================================================
# Helpers
# =============================================================================


def _clamp(x: float) -> float:
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
    return _clamp(score)


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
    return _clamp(score)


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
    return _clamp(score)


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
    return _clamp(score)


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
    return grader(landing_log, crash_log, total, steps, max_steps)
