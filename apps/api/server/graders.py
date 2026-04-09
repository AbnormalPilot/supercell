"""Deterministic graders for each ATC-Triage-v1 task.

Each grader receives the episode state at termination and returns a
score in [0.0, 1.0].  Graders are fully deterministic given the same
landing_log, crash_log, and task parameters.
"""

from __future__ import annotations

from models import EmergencyLevel


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _emergency_rank(level_str: str) -> int:
    """Map emergency string to priority rank (higher = more urgent)."""
    return {"MAYDAY": 2, "PAN_PAN": 1, "NONE": 0}.get(level_str, 0)


def _priority_score(landing_log: list[dict], total_flights: int) -> float:
    """Score how well emergencies were handled relative to their urgency.

    Ideal ordering: all MAYDAYs land first, then PAN_PANs, then normal.
    Score is based on position-weighted urgency matching.
    """
    if not landing_log:
        return 0.0

    n = len(landing_log)
    score = 0.0
    max_score = 0.0

    # Build ideal ordering
    sorted_ideal = sorted(
        landing_log, key=lambda x: (-_emergency_rank(x["emergency"]), x.get("fuel_at_clear", 999))
    )

    for position, entry in enumerate(landing_log):
        rank = _emergency_rank(entry["emergency"])
        ideal_rank = _emergency_rank(sorted_ideal[position]["emergency"])
        # Weight earlier positions more heavily
        weight = (n - position) / n
        max_score += ideal_rank * weight if ideal_rank > 0 else weight * 0.5
        score += rank * weight if rank > 0 else weight * 0.5

    if max_score == 0:
        return 1.0  # no emergencies — any order is fine
    return min(1.0, score / max_score)


def _medical_score(landing_log: list[dict]) -> float:
    """Extra credit for landing medical emergencies in the first half."""
    medical_entries = [e for e in landing_log if e.get("medical_onboard")]
    if not medical_entries:
        return 1.0
    n = len(landing_log)
    half = n / 2
    score = 0.0
    for entry in medical_entries:
        pos = entry["landing_position"]
        score += max(0.0, 1.0 - pos / half)
    return min(1.0, score / len(medical_entries))


def _fuel_management_score(landing_log: list[dict], crash_log: list[dict]) -> float:
    """Penalize letting fuel get dangerously low even without crashes."""
    if not landing_log and not crash_log:
        return 0.0
    total = len(landing_log) + len(crash_log)
    penalty = 0.0
    for entry in landing_log:
        fuel_left = entry.get("fuel_at_landing", 999)
        if fuel_left < 2:
            penalty += 0.5  # near-miss
        elif fuel_left < 5:
            penalty += 0.2  # uncomfortably low
    for _ in crash_log:
        penalty += 1.0  # crash
    return max(0.0, 1.0 - penalty / total)


# ---------------------------------------------------------------------------
# Task-specific graders
# ---------------------------------------------------------------------------

def grade_easy(
    landing_log: list[dict],
    crash_log: list[dict],
    total_flights: int,
    steps_used: int,
    max_steps: int,
) -> float:
    """Easy task grader.

    Weights: safety 40%, priority 40%, efficiency 20%.
    """
    # Safety: proportion of flights landed safely
    safety = len(landing_log) / total_flights if total_flights > 0 else 0.0

    # Priority: emergency ordering quality
    priority = _priority_score(landing_log, total_flights)

    # Efficiency: steps vs optimal (optimal = total_flights since 1 landing/step)
    optimal = total_flights
    efficiency = min(1.0, optimal / steps_used) if steps_used > 0 else 0.0

    return round(0.40 * safety + 0.40 * priority + 0.20 * efficiency, 4)


def grade_medium(
    landing_log: list[dict],
    crash_log: list[dict],
    total_flights: int,
    steps_used: int,
    max_steps: int,
) -> float:
    """Medium task grader.

    Weights: safety 30%, priority 25%, medical 15%, fuel mgmt 15%, efficiency 15%.
    """
    safety = len(landing_log) / total_flights if total_flights > 0 else 0.0
    priority = _priority_score(landing_log, total_flights)
    medical = _medical_score(landing_log)
    fuel = _fuel_management_score(landing_log, crash_log)
    optimal = total_flights
    efficiency = min(1.0, optimal / steps_used) if steps_used > 0 else 0.0

    return round(
        0.30 * safety
        + 0.25 * priority
        + 0.15 * medical
        + 0.15 * fuel
        + 0.15 * efficiency,
        4,
    )


def grade_hard(
    landing_log: list[dict],
    crash_log: list[dict],
    total_flights: int,
    steps_used: int,
    max_steps: int,
) -> float:
    """Hard task grader.

    Weights: safety 30%, priority 20%, medical 10%, fuel 20%, efficiency 10%, bonus 10%.
    """
    safety = len(landing_log) / total_flights if total_flights > 0 else 0.0
    priority = _priority_score(landing_log, total_flights)
    medical = _medical_score(landing_log)
    fuel = _fuel_management_score(landing_log, crash_log)
    optimal = total_flights
    efficiency = min(1.0, optimal / steps_used) if steps_used > 0 else 0.0

    # Bonus: extra credit for zero crashes with all flights landed
    bonus = 1.0 if (len(crash_log) == 0 and len(landing_log) == total_flights) else 0.0

    return round(
        0.30 * safety
        + 0.20 * priority
        + 0.10 * medical
        + 0.20 * fuel
        + 0.10 * efficiency
        + 0.10 * bonus,
        4,
    )


def grade_extra_hard(
    landing_log: list[dict],
    crash_log: list[dict],
    total_flights: int,
    steps_used: int,
    max_steps: int,
) -> float:
    """Extra hard task grader.

    Weights: safety 25%, priority 20%, medical 15%, fuel 25%, efficiency 10%, bonus 5%.
    Extra strict fuel penalties and lower tolerances for errors.
    """
    safety = len(landing_log) / total_flights if total_flights > 0 else 0.0
    priority = _priority_score(landing_log, total_flights)
    medical = _medical_score(landing_log)
    fuel = _fuel_management_score(landing_log, crash_log)
    optimal = total_flights
    efficiency = min(1.0, optimal / steps_used) if steps_used > 0 else 0.0

    # Bonus: extra credit for zero crashes with all flights landed
    bonus = 1.0 if (len(crash_log) == 0 and len(landing_log) == total_flights) else 0.0

    # Penalty for exceeding step budget
    step_penalty = 0.0
    if steps_used > max_steps:
        step_penalty = min(0.2, (steps_used - max_steps) / max_steps)

    score = round(
        0.25 * safety
        + 0.20 * priority
        + 0.15 * medical
        + 0.25 * fuel
        + 0.10 * efficiency
        + 0.05 * bonus,
        4,
    )

    return max(0.0, score - step_penalty)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

GRADERS = {
    "easy": grade_easy,
    "medium": grade_medium,
    "hard": grade_hard,
    "extra_hard": grade_extra_hard,
}


def grade_episode(
    task_id: str,
    landing_log: list[dict],
    crash_log: list[dict],
    total_flights: int,
    steps_used: int,
    max_steps: int,
) -> float:
    """Grade a completed episode. Returns a score in [0.0, 1.0]."""
    grader = GRADERS.get(task_id)
    if grader is None:
        raise ValueError(f"No grader for task_id '{task_id}'")
    return grader(landing_log, crash_log, total_flights, steps_used, max_steps)
