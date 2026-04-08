"""Tests for deterministic grading functions."""

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.graders import (
    _emergency_rank,
    _fuel_management_score,
    _medical_score,
    _priority_score,
    grade_easy,
    grade_episode,
    grade_hard,
    grade_medium,
)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------
class TestEmergencyRank:
    def test_known_levels(self):
        assert _emergency_rank("MAYDAY") == 2
        assert _emergency_rank("PAN_PAN") == 1
        assert _emergency_rank("NONE") == 0

    def test_unknown_defaults_zero(self):
        assert _emergency_rank("BOGUS") == 0
        assert _emergency_rank("") == 0


class TestPriorityScore:
    def test_empty_log_returns_zero(self):
        assert _priority_score([], 0) == 0.0

    def test_perfect_ordering(self):
        """MAYDAY first, then PAN_PAN, then NONE = best score."""
        log = [
            {"emergency": "MAYDAY", "fuel_at_clear": 4, "landing_position": 0},
            {"emergency": "PAN_PAN", "fuel_at_clear": 20, "landing_position": 1},
            {"emergency": "NONE", "fuel_at_clear": 50, "landing_position": 2},
        ]
        score = _priority_score(log, 3)
        assert score == pytest.approx(1.0)

    def test_reversed_ordering_scores_lower(self):
        """NONE first, then PAN_PAN, then MAYDAY = suboptimal."""
        perfect = [
            {"emergency": "MAYDAY", "fuel_at_clear": 4, "landing_position": 0},
            {"emergency": "PAN_PAN", "fuel_at_clear": 20, "landing_position": 1},
            {"emergency": "NONE", "fuel_at_clear": 50, "landing_position": 2},
        ]
        reversed_log = [
            {"emergency": "NONE", "fuel_at_clear": 50, "landing_position": 0},
            {"emergency": "PAN_PAN", "fuel_at_clear": 20, "landing_position": 1},
            {"emergency": "MAYDAY", "fuel_at_clear": 4, "landing_position": 2},
        ]
        assert _priority_score(perfect, 3) > _priority_score(reversed_log, 3)

    def test_all_normal_returns_one(self):
        """When no emergencies exist, any ordering is acceptable."""
        log = [
            {"emergency": "NONE", "fuel_at_clear": 30, "landing_position": 0},
            {"emergency": "NONE", "fuel_at_clear": 40, "landing_position": 1},
        ]
        assert _priority_score(log, 2) == 1.0


class TestMedicalScore:
    def test_no_medical_returns_one(self):
        log = [
            {"medical_onboard": False, "landing_position": 0},
            {"medical_onboard": False, "landing_position": 1},
        ]
        assert _medical_score(log) == 1.0

    def test_medical_first_is_best(self):
        log_first = [
            {"medical_onboard": True, "landing_position": 0},
            {"medical_onboard": False, "landing_position": 1},
            {"medical_onboard": False, "landing_position": 2},
            {"medical_onboard": False, "landing_position": 3},
        ]
        log_last = [
            {"medical_onboard": False, "landing_position": 0},
            {"medical_onboard": False, "landing_position": 1},
            {"medical_onboard": False, "landing_position": 2},
            {"medical_onboard": True, "landing_position": 3},
        ]
        assert _medical_score(log_first) > _medical_score(log_last)

    def test_empty_log(self):
        # No entries at all — no medical to evaluate
        assert _medical_score([]) == 1.0


class TestFuelManagementScore:
    def test_no_data_returns_zero(self):
        assert _fuel_management_score([], []) == 0.0

    def test_all_comfortable_fuel(self):
        log = [
            {"fuel_at_landing": 30},
            {"fuel_at_landing": 25},
        ]
        assert _fuel_management_score(log, []) == 1.0

    def test_near_miss_penalized(self):
        log = [{"fuel_at_landing": 1.5}]  # < 2 min
        score = _fuel_management_score(log, [])
        assert score < 1.0

    def test_low_fuel_penalized(self):
        log = [{"fuel_at_landing": 3.0}]  # < 5 min
        score = _fuel_management_score(log, [])
        assert score < 1.0

    def test_crash_heavily_penalized(self):
        log = [{"fuel_at_landing": 30}]
        crash = [{"callsign": "CRASH1"}]
        score = _fuel_management_score(log, crash)
        assert score < 0.6

    def test_all_crashes(self):
        score = _fuel_management_score([], [{"c": 1}, {"c": 2}])
        assert score == 0.0


# ---------------------------------------------------------------------------
# Task grader tests
# ---------------------------------------------------------------------------
class TestGradeEasy:
    def test_perfect_score(self):
        log = [
            {"emergency": "MAYDAY", "fuel_at_clear": 4, "landing_position": 0},
            {"emergency": "PAN_PAN", "fuel_at_clear": 28, "landing_position": 1},
            {"emergency": "NONE", "fuel_at_clear": 43, "landing_position": 2},
            {"emergency": "NONE", "fuel_at_clear": 48, "landing_position": 3},
        ]
        score = grade_easy(log, [], 4, 4, 15)
        assert 0.9 <= score <= 1.0

    def test_all_crashed(self):
        crash = [{"c": i} for i in range(4)]
        score = grade_easy([], crash, 4, 4, 15)
        # 0 safety, 0 priority, but efficiency component may be nonzero
        assert score < 0.3

    def test_partial_landing(self):
        log = [
            {"emergency": "MAYDAY", "fuel_at_clear": 4, "landing_position": 0},
            {"emergency": "NONE", "fuel_at_clear": 43, "landing_position": 1},
        ]
        crash = [{"c": 1}]
        score = grade_easy(log, crash, 4, 3, 15)
        assert 0.0 < score < 1.0

    def test_return_range(self):
        """Score must be in [0, 1] for any inputs."""
        for n_landed in range(5):
            for n_crashed in range(5 - n_landed):
                log = [
                    {"emergency": "NONE", "fuel_at_clear": 50, "landing_position": i}
                    for i in range(n_landed)
                ]
                crash = [{"c": i} for i in range(n_crashed)]
                total = max(n_landed + n_crashed, 1)
                score = grade_easy(log, crash, total, max(n_landed, 1), 15)
                assert 0.0 <= score <= 1.0, f"Out of range: {score}"


class TestGradeMedium:
    def test_score_in_range(self):
        log = [
            {"emergency": "MAYDAY", "fuel_at_clear": 6, "fuel_at_landing": 6, "medical_onboard": False, "landing_position": 0},
            {"emergency": "PAN_PAN", "fuel_at_clear": 20, "fuel_at_landing": 18, "medical_onboard": True, "landing_position": 1},
            {"emergency": "NONE", "fuel_at_clear": 8, "fuel_at_landing": 4, "medical_onboard": False, "landing_position": 2},
        ]
        score = grade_medium(log, [], 7, 3, 30)
        assert 0.0 <= score <= 1.0

    def test_zero_steps_returns_zero_efficiency(self):
        # steps_used=0 edge case — efficiency is 0 but medical score defaults to 1.0
        score = grade_medium([], [], 7, 0, 30)
        assert score < 0.2


class TestGradeHard:
    def test_perfect_bonus(self):
        """All 12 landed, 0 crashed → bonus component is 1.0."""
        log = [
            {"emergency": "MAYDAY", "fuel_at_clear": 5, "fuel_at_landing": 5, "medical_onboard": True, "landing_position": i}
            for i in range(12)
        ]
        score = grade_hard(log, [], 12, 12, 50)
        assert score > 0.5  # bonus contributes 0.10

    def test_no_bonus_with_crash(self):
        log = [
            {"emergency": "NONE", "fuel_at_clear": 30, "fuel_at_landing": 28, "medical_onboard": False, "landing_position": i}
            for i in range(11)
        ]
        crash = [{"c": 1}]
        score_crash = grade_hard(log, crash, 12, 12, 50)
        log_full = log + [{"emergency": "NONE", "fuel_at_clear": 30, "fuel_at_landing": 28, "medical_onboard": False, "landing_position": 11}]
        score_clean = grade_hard(log_full, [], 12, 12, 50)
        assert score_clean > score_crash  # bonus difference


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
class TestGradeEpisode:
    def test_unknown_task_raises(self):
        with pytest.raises(ValueError, match="No grader"):
            grade_episode("nonexistent", [], [], 4, 4, 15)

    def test_dispatches_correctly(self):
        for task_id in ["easy", "medium", "hard"]:
            score = grade_episode(task_id, [], [], 4, 1, 15)
            assert 0.0 <= score <= 1.0

    def test_deterministic(self):
        """Same inputs always produce the same score."""
        log = [
            {"emergency": "MAYDAY", "fuel_at_clear": 4, "fuel_at_landing": 4, "medical_onboard": False, "landing_position": 0},
            {"emergency": "NONE", "fuel_at_clear": 43, "fuel_at_landing": 41, "medical_onboard": False, "landing_position": 1},
        ]
        s1 = grade_episode("easy", log, [], 4, 2, 15)
        s2 = grade_episode("easy", log, [], 4, 2, 15)
        assert s1 == s2
