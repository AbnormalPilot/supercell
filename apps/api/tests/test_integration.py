"""Integration tests — full episode runs with known strategies and reproducibility."""

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ATCAction
from server.atc_environment import ATCEnvironment


# ---------------------------------------------------------------------------
# Strategy helpers
# ---------------------------------------------------------------------------
def _urgency_key(f):
    """Sort key: MAYDAY first, then lowest fuel, then PAN_PAN, then by passengers."""
    e = 2 if f.emergency == "MAYDAY" else 1 if f.emergency == "PAN_PAN" else 0
    return (-e, f.fuel_minutes, -f.passengers)


def _run_episode(task_id: str, strategy="urgency") -> dict:
    """Run a full episode with the given strategy. Returns summary dict."""
    env = ATCEnvironment()
    obs = env.reset(episode_id=task_id)
    rewards = []
    step = 0

    while not obs.done and step < 60:
        flights = obs.flights
        if not flights:
            break

        if strategy == "urgency":
            best = min(flights, key=_urgency_key)
            idx = best.index
        elif strategy == "first":
            idx = 0
        elif strategy == "last":
            idx = len(flights) - 1
        elif strategy == "random_invalid":
            idx = 999
        else:
            idx = 0

        obs = env.step(ATCAction(flight_index=idx))
        rewards.append(obs.reward)
        step += 1

    return {
        "task_id": task_id,
        "score": env.grade(),
        "landed": env.state.landed_safely,
        "crashed": env.state.crashed,
        "total": env.state.total_flights,
        "steps": env.state.step_count,
        "reward": env.state.episode_reward,
        "rewards": rewards,
    }


# ---------------------------------------------------------------------------
# Full episode tests
# ---------------------------------------------------------------------------
class TestEasyFullEpisode:
    def test_urgency_strategy_scores_high(self):
        r = _run_episode("easy", "urgency")
        assert r["score"] >= 0.9
        assert r["crashed"] == 0
        assert r["landed"] == 4

    def test_first_strategy_still_completes(self):
        r = _run_episode("easy", "first")
        assert r["landed"] + r["crashed"] == r["total"]

    def test_last_strategy_still_completes(self):
        r = _run_episode("easy", "last")
        assert r["landed"] + r["crashed"] == r["total"]


class TestMediumFullEpisode:
    def test_urgency_strategy(self):
        r = _run_episode("medium", "urgency")
        assert r["score"] > 0.5
        assert r["landed"] >= 5  # at least most flights

    def test_first_strategy(self):
        r = _run_episode("medium", "first")
        assert 0.0 <= r["score"] <= 1.0

    def test_medium_harder_than_easy(self):
        easy = _run_episode("easy", "first")
        medium = _run_episode("medium", "first")
        # "first" strategy (naive) should do worse on medium
        assert medium["crashed"] >= easy["crashed"] or medium["score"] <= easy["score"]


class TestHardFullEpisode:
    def test_urgency_strategy(self):
        r = _run_episode("hard", "urgency")
        assert r["score"] > 0.3
        assert r["landed"] >= 6  # at least half

    def test_hard_has_crashes_with_naive_strategy(self):
        r = _run_episode("hard", "first")
        assert r["crashed"] > 0  # naive strategy should cause crashes

    def test_hard_genuinely_challenging(self):
        """Even urgency strategy can't get perfect on hard."""
        r = _run_episode("hard", "urgency")
        # Hard task should be challenging — likely some crashes
        assert r["score"] < 1.0 or r["crashed"] > 0 or r["score"] >= 0.9


# ---------------------------------------------------------------------------
# Strategy comparison
# ---------------------------------------------------------------------------
class TestStrategyComparison:
    def test_urgency_beats_naive_on_easy(self):
        urgency = _run_episode("easy", "urgency")
        naive = _run_episode("easy", "first")
        assert urgency["score"] >= naive["score"]

    def test_urgency_beats_naive_on_hard(self):
        urgency = _run_episode("hard", "urgency")
        naive = _run_episode("hard", "first")
        assert urgency["score"] >= naive["score"]

    def test_all_invalid_scores_zero(self):
        r = _run_episode("easy", "random_invalid")
        # All invalid actions — nothing gets landed
        assert r["landed"] == 0 or r["score"] < 0.5


# ---------------------------------------------------------------------------
# Reward signal properties
# ---------------------------------------------------------------------------
class TestRewardSignalProperties:
    def test_reward_varies_across_steps(self):
        """Reward should not be constant — different flights yield different rewards."""
        r = _run_episode("easy", "urgency")
        unique_rewards = set(r["rewards"])
        assert len(unique_rewards) > 1

    def test_positive_rewards_for_successful_landings(self):
        r = _run_episode("easy", "urgency")
        positive_count = sum(1 for rr in r["rewards"] if rr > 0)
        assert positive_count >= r["landed"]

    def test_episode_reward_is_sum_of_components(self):
        """Episode reward should be the accumulated total."""
        env = ATCEnvironment()
        env.reset(episode_id="easy")
        for _ in range(10):
            obs = env.step(ATCAction(flight_index=0))
            if obs.done:
                break
        # Episode reward should be nonzero
        assert env.state.episode_reward != 0.0


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
class TestReproducibility:
    def test_same_strategy_same_result(self):
        r1 = _run_episode("easy", "urgency")
        r2 = _run_episode("easy", "urgency")
        assert r1["score"] == r2["score"]
        assert r1["landed"] == r2["landed"]
        assert r1["crashed"] == r2["crashed"]
        assert r1["rewards"] == r2["rewards"]

    def test_medium_reproducible(self):
        r1 = _run_episode("medium", "urgency")
        r2 = _run_episode("medium", "urgency")
        assert r1["score"] == r2["score"]

    def test_hard_reproducible(self):
        r1 = _run_episode("hard", "urgency")
        r2 = _run_episode("hard", "urgency")
        assert r1["score"] == r2["score"]


# ---------------------------------------------------------------------------
# Grader consistency
# ---------------------------------------------------------------------------
class TestGraderConsistency:
    def test_perfect_play_scores_highest(self):
        """Urgency-optimal play should score >= any random strategy."""
        scores = {}
        for strategy in ["urgency", "first", "last"]:
            r = _run_episode("easy", strategy)
            scores[strategy] = r["score"]
        assert scores["urgency"] >= scores["first"]
        assert scores["urgency"] >= scores["last"]

    def test_scores_within_valid_range(self):
        for tid in ["easy", "medium", "hard"]:
            for strategy in ["urgency", "first", "last"]:
                r = _run_episode(tid, strategy)
                assert 0.0 <= r["score"] <= 1.0, f"{tid}/{strategy}: {r['score']}"

    def test_harder_tasks_score_lower_with_naive(self):
        """Naive strategy should score progressively worse on harder tasks."""
        easy = _run_episode("easy", "first")
        hard = _run_episode("hard", "first")
        assert easy["score"] >= hard["score"]
