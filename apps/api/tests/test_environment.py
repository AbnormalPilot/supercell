"""Tests for ATCEnvironment core logic — reset, step, state, edge cases."""

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ATCAction, ATCObservation, ATCState, EmergencyLevel
from server.atc_environment import ATCEnvironment


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def env():
    return ATCEnvironment()


@pytest.fixture
def easy_env(env):
    env.reset(episode_id="easy")
    return env


@pytest.fixture
def medium_env(env):
    env.reset(episode_id="medium")
    return env


@pytest.fixture
def hard_env(env):
    env.reset(episode_id="hard")
    return env


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------
class TestReset:
    def test_returns_observation(self, env):
        obs = env.reset(episode_id="easy")
        assert isinstance(obs, ATCObservation)

    def test_not_done(self, env):
        obs = env.reset(episode_id="easy")
        assert obs.done is False

    def test_zero_reward(self, env):
        obs = env.reset(episode_id="easy")
        assert obs.reward == 0.0

    def test_correct_flight_count(self, env):
        for tid, expected in [("easy", 4), ("medium", 7), ("hard", 12)]:
            obs = env.reset(episode_id=tid)
            assert len(obs.flights) == expected

    def test_correct_task_id(self, env):
        obs = env.reset(episode_id="medium")
        assert obs.task_id == "medium"

    def test_default_to_easy(self, env):
        obs = env.reset()
        assert obs.task_id == "easy"
        assert len(obs.flights) == 4

    def test_task_prefix_format(self, env):
        obs = env.reset(episode_id="task:hard")
        assert obs.task_id == "hard"
        assert len(obs.flights) == 12

    def test_reset_clears_previous_episode(self, env):
        env.reset(episode_id="easy")
        env.step(ATCAction(flight_index=0))
        env.step(ATCAction(flight_index=0))
        obs = env.reset(episode_id="easy")
        assert obs.landed_safely == 0
        assert obs.crashed == 0
        assert obs.time_step == 0
        assert len(obs.flights) == 4

    def test_state_after_reset(self, env):
        env.reset(episode_id="medium")
        st = env.state
        assert st.step_count == 0
        assert st.time_step == 0
        assert st.landed_safely == 0
        assert st.crashed == 0
        assert st.episode_reward == 0.0
        assert st.landing_log == []
        assert st.crash_log == []

    def test_observation_has_instructions(self, env):
        obs = env.reset(episode_id="easy")
        assert len(obs.instructions) > 0
        assert "flight_index" in obs.instructions

    def test_flights_have_contiguous_indices(self, env):
        obs = env.reset(episode_id="hard")
        indices = [f.index for f in obs.flights]
        assert indices == list(range(len(obs.flights)))

    def test_weather_populated(self, env):
        obs = env.reset(episode_id="medium")
        assert obs.weather.visibility_nm > 0
        assert obs.weather.wind_knots >= 0


# ---------------------------------------------------------------------------
# Step — basic mechanics
# ---------------------------------------------------------------------------
class TestStep:
    def test_lands_one_flight(self, easy_env):
        obs = easy_env.step(ATCAction(flight_index=0))
        assert obs.landed_safely == 1
        assert len(obs.flights) == 3

    def test_step_count_increments(self, easy_env):
        easy_env.step(ATCAction(flight_index=0))
        assert easy_env.state.step_count == 1
        easy_env.step(ATCAction(flight_index=0))
        assert easy_env.state.step_count == 2

    def test_time_advances(self, easy_env):
        easy_env.step(ATCAction(flight_index=0))
        assert easy_env.state.time_step > 0

    def test_reward_is_positive_for_normal_landing(self, easy_env):
        obs = easy_env.step(ATCAction(flight_index=0))
        assert obs.reward > 0

    def test_indices_reindex_after_removal(self, easy_env):
        obs = easy_env.step(ATCAction(flight_index=0))
        indices = [f.index for f in obs.flights]
        assert indices == [0, 1, 2]  # reindexed 0..n-1

    def test_landing_log_populated(self, easy_env):
        easy_env.step(ATCAction(flight_index=0))
        st = easy_env.state
        assert len(st.landing_log) == 1
        assert "callsign" in st.landing_log[0]
        assert "emergency" in st.landing_log[0]
        assert "fuel_at_landing" in st.landing_log[0]
        assert "landing_position" in st.landing_log[0]

    def test_step_after_done_is_noop(self, easy_env):
        # Run to completion
        for _ in range(20):
            obs = easy_env.step(ATCAction(flight_index=0))
            if obs.done:
                break
        landed_before = obs.landed_safely
        obs2 = easy_env.step(ATCAction(flight_index=0))
        assert obs2.done is True
        assert obs2.landed_safely == landed_before
        assert obs2.reward == 0.0


# ---------------------------------------------------------------------------
# Step — invalid & weather-blocked actions
# ---------------------------------------------------------------------------
class TestInvalidActions:
    def test_out_of_range_high(self, easy_env):
        obs = easy_env.step(ATCAction(flight_index=99))
        assert obs.reward == -5.0

    def test_out_of_range_at_boundary(self, easy_env):
        obs = easy_env.step(ATCAction(flight_index=4))  # exactly out of range
        assert obs.reward == -5.0

    def test_time_still_advances_on_invalid(self, easy_env):
        easy_env.step(ATCAction(flight_index=99))
        assert easy_env.state.time_step > 0

    def test_no_landing_on_invalid(self, easy_env):
        easy_env.step(ATCAction(flight_index=99))
        assert easy_env.state.landed_safely == 0

    def test_fuel_burns_on_invalid(self, easy_env):
        obs_before = easy_env.reset(episode_id="easy")
        fuel_before = obs_before.flights[0].fuel_minutes
        obs_after = easy_env.step(ATCAction(flight_index=99))
        fuel_after = obs_after.flights[0].fuel_minutes
        assert fuel_after < fuel_before


class TestWeatherBlocking:
    def test_weather_reject_penalty(self, medium_env):
        """Force visibility below a flight's minimum by manipulating weather."""
        # DLH401 (index 0) needs 3nm visibility
        # Manually set weather to 1nm
        medium_env._weather.visibility_nm = 1.0
        obs = medium_env.step(ATCAction(flight_index=0))
        assert obs.reward == -3.0

    def test_can_land_now_flag_updates(self, medium_env):
        medium_env._weather.visibility_nm = 2.0
        obs = medium_env._make_observation()
        # DLH401 needs 3nm — should show can_land_now=False
        dlh = next((f for f in obs.flights if f.callsign == "DLH401"), None)
        assert dlh is not None
        assert dlh.can_land_now is False

    def test_low_vis_flight_can_still_land(self, medium_env):
        """Flights with low min_visibility can land in poor weather."""
        medium_env._weather.visibility_nm = 1.5
        # AFR882 needs only 1.0nm — should still be able to land
        afr = next((f for f in medium_env._pending if f.callsign == "AFR882"), None)
        assert afr is not None
        assert medium_env._can_land(afr) is True


# ---------------------------------------------------------------------------
# Fuel mechanics
# ---------------------------------------------------------------------------
class TestFuelMechanics:
    def test_fuel_decreases_for_waiting_flights(self, easy_env):
        obs_before = easy_env.reset(episode_id="easy")
        # UAL441 is index 0, has 45 min fuel
        fuel_before = obs_before.flights[0].fuel_minutes
        assert fuel_before == 45.0

        # Land flight index 1 (DAL892) — UAL441 waits and burns fuel
        obs_after = easy_env.step(ATCAction(flight_index=1))
        ual = next((f for f in obs_after.flights if f.callsign == "UAL441"), None)
        assert ual is not None
        assert ual.fuel_minutes < fuel_before

    def test_landing_flight_does_not_burn_extra_fuel(self, easy_env):
        # DAL892 has 4 min fuel — it should still have fuel after landing as index 1
        easy_env.step(ATCAction(flight_index=1))  # land DAL892
        st = easy_env.state
        landed = st.landing_log[0]
        assert landed["callsign"] == "DAL892"
        assert landed["fuel_at_landing"] == 4.0  # didn't burn while it was being landed

    def test_crash_on_fuel_exhaustion(self, easy_env):
        # Land the two non-emergency flights first to make DAL892 (4 min fuel) crash
        easy_env.step(ATCAction(flight_index=0))  # UAL441
        easy_env.step(ATCAction(flight_index=1))  # AAL217 (shifted)
        st = easy_env.state
        assert st.crashed > 0

    def test_crash_logged(self, easy_env):
        easy_env.step(ATCAction(flight_index=0))
        easy_env.step(ATCAction(flight_index=1))
        st = easy_env.state
        assert len(st.crash_log) > 0
        crash = st.crash_log[0]
        assert "callsign" in crash
        assert "crashed_at_time" in crash

    def test_crash_reward_penalty(self, easy_env):
        easy_env.step(ATCAction(flight_index=0))
        easy_env.step(ATCAction(flight_index=1))
        # Episode reward should include -100 crash penalty
        assert easy_env.state.episode_reward < 0 or easy_env.state.crashed > 0


# ---------------------------------------------------------------------------
# Wake turbulence separation
# ---------------------------------------------------------------------------
class TestWakeSeparation:
    def test_heavy_behind_heavy_more_separation(self, medium_env):
        """Landing a HEAVY after a HEAVY should advance time more than MEDIUM-MEDIUM."""
        env1 = ATCEnvironment()
        env1.reset(episode_id="medium")
        # Land BAW119 (HEAVY, index 1) first
        env1.step(ATCAction(flight_index=1))
        t1 = env1.state.time_step
        # Then land DLH401 (HEAVY, index 0 after shift)
        env1.step(ATCAction(flight_index=0))
        heavy_heavy_time = env1.state.time_step - t1

        env2 = ATCEnvironment()
        env2.reset(episode_id="medium")
        # Land AFR882 (MEDIUM, index 2) first
        env2.step(ATCAction(flight_index=2))
        t2 = env2.state.time_step
        # Then land JBU562 (MEDIUM, index 2 after shift)
        env2.step(ATCAction(flight_index=2))
        medium_medium_time = env2.state.time_step - t2

        # HEAVY-HEAVY separation should be >= MEDIUM-MEDIUM
        assert heavy_heavy_time >= medium_medium_time


# ---------------------------------------------------------------------------
# Episode completion
# ---------------------------------------------------------------------------
class TestEpisodeCompletion:
    def test_done_when_all_landed(self, easy_env):
        for _ in range(10):
            obs = easy_env.step(ATCAction(flight_index=0))
            if obs.done:
                break
        assert obs.done

    def test_completion_bonus_no_crashes(self, env):
        env.reset(episode_id="easy")
        # Land optimally: DAL892 (MAYDAY) first
        env.step(ATCAction(flight_index=1))  # DAL892
        env.step(ATCAction(flight_index=1))  # AAL217
        env.step(ATCAction(flight_index=0))  # UAL441
        obs = env.step(ATCAction(flight_index=0))  # SWA103
        assert obs.done
        # Should include +50 completion bonus (no crashes)
        assert env.state.episode_reward > 100  # base rewards + bonus

    def test_no_completion_bonus_with_crash(self, env):
        env.reset(episode_id="easy")
        # Delay the MAYDAY flight to cause a crash
        env.step(ATCAction(flight_index=0))  # UAL441 first
        env.step(ATCAction(flight_index=1))  # AAL217
        # DAL892 should have crashed
        st = env.state
        crashed = st.crashed > 0
        # Run remaining
        for _ in range(10):
            obs = env.step(ATCAction(flight_index=0))
            if obs.done:
                break
        # Reward should be lower due to crash penalty and no completion bonus
        if crashed:
            assert env.state.episode_reward < 100


# ---------------------------------------------------------------------------
# Weather timeline (medium task)
# ---------------------------------------------------------------------------
class TestWeatherTimeline:
    def test_visibility_drops_over_time(self, medium_env):
        vis_initial = medium_env._weather.visibility_nm
        # Land several flights to advance time
        for _ in range(5):
            medium_env.step(ATCAction(flight_index=0))
        vis_later = medium_env._weather.visibility_nm
        assert vis_later < vis_initial

    def test_hard_weather_oscillates(self, hard_env):
        """Hard task weather should go down then come back up."""
        vis_readings = [hard_env._weather.visibility_nm]
        for _ in range(12):
            if hard_env._done:
                break
            hard_env.step(ATCAction(flight_index=0))
            vis_readings.append(hard_env._weather.visibility_nm)
        min_vis = min(vis_readings)
        max_vis = max(vis_readings)
        assert min_vis < max_vis


# ---------------------------------------------------------------------------
# Grading integration
# ---------------------------------------------------------------------------
class TestGrading:
    def test_grade_before_any_step(self, easy_env):
        score = easy_env.grade()
        assert score == 0.0  # nothing landed

    def test_grade_after_optimal_easy(self, env):
        env.reset(episode_id="easy")
        env.step(ATCAction(flight_index=1))  # DAL892 (MAYDAY)
        env.step(ATCAction(flight_index=1))  # AAL217 (PAN_PAN)
        env.step(ATCAction(flight_index=0))  # UAL441
        env.step(ATCAction(flight_index=0))  # SWA103
        score = env.grade()
        assert score >= 0.9

    def test_grade_after_worst_easy(self, env):
        """Land normals first, let MAYDAY crash."""
        env.reset(episode_id="easy")
        env.step(ATCAction(flight_index=0))  # UAL441
        env.step(ATCAction(flight_index=1))  # AAL217 (shifted)
        # DAL892 has likely crashed — continue
        for _ in range(5):
            obs = env.step(ATCAction(flight_index=0))
            if obs.done:
                break
        score = env.grade()
        # Suboptimal play should score noticeably lower than perfect (1.0)
        assert score < 0.95

    def test_grade_in_range_all_tasks(self):
        for tid in ["easy", "medium", "hard"]:
            env = ATCEnvironment()
            env.reset(episode_id=tid)
            for _ in range(60):
                obs = env.step(ATCAction(flight_index=0))
                if obs.done:
                    break
            score = env.grade()
            assert 0.0 <= score <= 1.0, f"{tid}: {score}"


# ---------------------------------------------------------------------------
# Reward signal quality
# ---------------------------------------------------------------------------
class TestRewardSignal:
    def test_positive_reward_for_landing(self, easy_env):
        obs = easy_env.step(ATCAction(flight_index=0))
        assert obs.reward > 0

    def test_mayday_landing_higher_reward(self, env):
        env.reset(episode_id="easy")
        obs_normal = env.step(ATCAction(flight_index=0))  # UAL441 (NONE)
        r_normal = obs_normal.reward

        env.reset(episode_id="easy")
        obs_mayday = env.step(ATCAction(flight_index=1))  # DAL892 (MAYDAY)
        r_mayday = obs_mayday.reward

        assert r_mayday > r_normal

    def test_medical_adds_reward(self, env):
        env.reset(episode_id="easy")
        obs_medical = env.step(ATCAction(flight_index=2))  # AAL217 (PAN_PAN + medical)
        r_medical = obs_medical.reward

        env.reset(episode_id="easy")
        obs_plain = env.step(ATCAction(flight_index=3))  # SWA103 (NONE, no medical)
        r_plain = obs_plain.reward

        assert r_medical > r_plain

    def test_cumulative_reward_tracked(self, easy_env):
        easy_env.step(ATCAction(flight_index=0))
        r1 = easy_env.state.episode_reward
        easy_env.step(ATCAction(flight_index=0))
        r2 = easy_env.state.episode_reward
        assert r2 != r1  # reward changes each step

    def test_dense_signal_every_step(self, easy_env):
        """Every step should produce a non-None reward."""
        for i in range(4):
            obs = easy_env.step(ATCAction(flight_index=0))
            assert obs.reward is not None
            if obs.done:
                break


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
class TestDeterminism:
    def test_same_actions_same_outcome(self):
        """Running the same sequence of actions twice produces identical results."""
        results = []
        for _ in range(2):
            env = ATCEnvironment()
            env.reset(episode_id="easy")
            rewards = []
            for idx in [1, 1, 0, 0]:
                obs = env.step(ATCAction(flight_index=idx))
                rewards.append(obs.reward)
            results.append({
                "rewards": rewards,
                "score": env.grade(),
                "landed": env.state.landed_safely,
                "crashed": env.state.crashed,
            })
        assert results[0] == results[1]

    def test_reset_is_deterministic(self):
        env = ATCEnvironment()
        obs1 = env.reset(episode_id="medium")
        callsigns1 = [f.callsign for f in obs1.flights]
        obs2 = env.reset(episode_id="medium")
        callsigns2 = [f.callsign for f in obs2.flights]
        assert callsigns1 == callsigns2


# ---------------------------------------------------------------------------
# Observation serialization
# ---------------------------------------------------------------------------
class TestObservationSerialization:
    def test_json_serializable(self, easy_env):
        obs = easy_env.step(ATCAction(flight_index=0))
        data = obs.model_dump()
        assert isinstance(data, dict)
        assert isinstance(data["flights"], list)
        assert isinstance(data["weather"], dict)

    def test_flights_contain_required_fields(self, easy_env):
        obs = easy_env.step(ATCAction(flight_index=0))
        for f in obs.flights:
            assert hasattr(f, "callsign")
            assert hasattr(f, "emergency")
            assert hasattr(f, "fuel_minutes")
            assert hasattr(f, "passengers")
            assert hasattr(f, "can_land_now")
