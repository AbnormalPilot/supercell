"""Simplified graders for hackathon."""

from typing import List, Dict, Callable


# =============================================================================
# Grading Functions
# =============================================================================

def grade_easy(landing_log: List[Dict], crash_log: List[Dict], total: int, steps: int, max_steps: int) -> float:
    """Grade easy task."""
    if total == 0:
        return 0.0
    
    safety = len(landing_log) / total
    crashed_penalty = len(crash_log) * 0.3
    step_penalty = max(0, (steps - max_steps) / max_steps * 0.2) if max_steps > 0 else 0
    
    score = safety - crashed_penalty - step_penalty
    return max(0.0, min(1.0, score))


def grade_medium(landing_log: List[Dict], crash_log: List[Dict], total: int, steps: int, max_steps: int) -> float:
    """Grade medium task."""
    if total == 0:
        return 0.0
    
    safety = len(landing_log) / total
    priority = sum(1 for e in landing_log if e.get('emergency') in ['MAYDAY', 'PAN_PAN']) / max(1, len(landing_log))
    crashed_penalty = len(crash_log) * 0.4
    step_penalty = max(0, (steps - max_steps) / max_steps * 0.2) if max_steps > 0 else 0
    
    score = 0.6 * safety + 0.2 * priority - crashed_penalty - step_penalty
    return max(0.0, min(1.0, score))


def grade_hard(landing_log: List[Dict], crash_log: List[Dict], total: int, steps: int, max_steps: int) -> float:
    """Grade hard task."""
    if total == 0:
        return 0.0
    
    safety = len(landing_log) / total
    priority = sum(1 for e in landing_log if e.get('emergency') == 'MAYDAY') / max(1, len(landing_log))
    medical = sum(1 for e in landing_log if e.get('medical_onboard')) / max(1, len(landing_log))
    fuel = sum(1 for e in landing_log if e.get('fuel_on_landing', 0) > 5) / max(1, len(landing_log))
    crashed_penalty = len(crash_log) * 0.5
    step_penalty = max(0, (steps - max_steps) / max_steps * 0.2) if max_steps > 0 else 0
    
    score = 0.3 * safety + 0.2 * priority + 0.15 * medical + 0.25 * fuel - crashed_penalty - step_penalty
    return max(0.0, min(1.0, score))


def grade_extra_hard(landing_log: List[Dict], crash_log: List[Dict], total: int, steps: int, max_steps: int) -> float:
    """Grade extra hard task."""
    if total == 0:
        return 0.0
    
    safety = len(landing_log) / total
    priority = sum(1 for e in landing_log if e.get('emergency') == 'MAYDAY') / max(1, len(landing_log))
    medical = sum(1 for e in landing_log if e.get('medical_onboard')) / max(1, len(landing_log))
    fuel = sum(1 for e in landing_log if e.get('fuel_on_landing', 0) > 3) / max(1, len(landing_log))
    efficiency = min(1.0, total / steps) if steps > 0 else 0.0
    bonus = 0.1 if (len(crash_log) == 0 and len(landing_log) == total) else 0.0
    crashed_penalty = len(crash_log) * 0.6
    step_penalty = max(0, (steps - max_steps) / max_steps * 0.3) if max_steps > 0 else 0
    
    score = 0.25 * safety + 0.2 * priority + 0.15 * medical + 0.25 * fuel + 0.1 * efficiency + bonus - crashed_penalty - step_penalty
    return max(0.0, min(1.0, score))


# Grader registry
GRADERS: Dict[str, Callable] = {
    "easy": grade_easy,
    "medium": grade_medium,
    "hard": grade_hard,
    "extra_hard": grade_extra_hard,
}


def grade_episode(landing_log: List[Dict], crash_log: List[Dict], total: int, steps: int, max_steps: int, task_id: str) -> float:
    """Grade an episode based on task_id."""
    grader = GRADERS.get(task_id, grade_easy)
    return grader(landing_log, crash_log, total, steps, max_steps)
