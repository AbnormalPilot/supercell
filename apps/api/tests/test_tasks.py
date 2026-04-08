"""Tests for task scenario definitions."""

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import EmergencyLevel, WakeCategory
from server.tasks import Scenario, get_task_scenario, list_tasks, TASKS


class TestGetTaskScenario:
    def test_easy_loads(self):
        s = get_task_scenario("easy")
        assert isinstance(s, Scenario)
        assert s.task_id == "easy"

    def test_medium_loads(self):
        s = get_task_scenario("medium")
        assert s.task_id == "medium"

    def test_hard_loads(self):
        s = get_task_scenario("hard")
        assert s.task_id == "hard"

    def test_unknown_task_raises(self):
        with pytest.raises(ValueError, match="Unknown task_id"):
            get_task_scenario("impossible")

    def test_seed_param_accepted(self):
        # Seed is accepted even though scenarios are currently deterministic
        s = get_task_scenario("easy", seed=42)
        assert s.task_id == "easy"


class TestListTasks:
    def test_returns_three_tasks(self):
        tasks = list_tasks()
        assert len(tasks) == 3

    def test_task_ids(self):
        ids = {t["task_id"] for t in list_tasks()}
        assert ids == {"easy", "medium", "hard"}

    def test_required_fields_present(self):
        for t in list_tasks():
            assert "task_id" in t
            assert "task_name" in t
            assert "description" in t
            assert "num_flights" in t
            assert "max_steps" in t

    def test_flight_counts(self):
        tasks = {t["task_id"]: t for t in list_tasks()}
        assert tasks["easy"]["num_flights"] == 4
        assert tasks["medium"]["num_flights"] == 7
        assert tasks["hard"]["num_flights"] == 12

    def test_difficulty_progression(self):
        """Harder tasks have more flights and higher step limits."""
        tasks = {t["task_id"]: t for t in list_tasks()}
        assert tasks["easy"]["num_flights"] < tasks["medium"]["num_flights"]
        assert tasks["medium"]["num_flights"] < tasks["hard"]["num_flights"]
        assert tasks["easy"]["max_steps"] < tasks["medium"]["max_steps"]
        assert tasks["medium"]["max_steps"] < tasks["hard"]["max_steps"]


class TestEasyScenario:
    @pytest.fixture
    def scenario(self):
        return get_task_scenario("easy")

    def test_flight_count(self, scenario):
        assert len(scenario.flights) == 4

    def test_has_mayday(self, scenario):
        maydays = [f for f in scenario.flights if f.emergency == EmergencyLevel.MAYDAY]
        assert len(maydays) == 1
        assert maydays[0].callsign == "DAL892"

    def test_has_pan_pan(self, scenario):
        pan_pans = [f for f in scenario.flights if f.emergency == EmergencyLevel.PAN_PAN]
        assert len(pan_pans) == 1

    def test_mayday_has_low_fuel(self, scenario):
        mayday = next(f for f in scenario.flights if f.emergency == EmergencyLevel.MAYDAY)
        assert mayday.fuel_minutes <= 5.0

    def test_has_medical(self, scenario):
        medical = [f for f in scenario.flights if f.medical_onboard]
        assert len(medical) == 1

    def test_clear_weather(self, scenario):
        assert scenario.weather.visibility_nm >= 10.0
        assert scenario.weather.trend == "stable"
        assert scenario.weather_timeline == []

    def test_all_can_land_in_clear_weather(self, scenario):
        for f in scenario.flights:
            assert f.min_visibility_nm <= scenario.weather.visibility_nm

    def test_unique_callsigns(self, scenario):
        callsigns = [f.callsign for f in scenario.flights]
        assert len(callsigns) == len(set(callsigns))


class TestMediumScenario:
    @pytest.fixture
    def scenario(self):
        return get_task_scenario("medium")

    def test_flight_count(self, scenario):
        assert len(scenario.flights) == 7

    def test_has_weather_timeline(self, scenario):
        assert len(scenario.weather_timeline) > 0

    def test_weather_deteriorates(self, scenario):
        assert scenario.weather.trend == "deteriorating"

    def test_has_weather_sensitive_aircraft(self, scenario):
        """At least one aircraft needs visibility > 2nm."""
        high_vis = [f for f in scenario.flights if f.min_visibility_nm >= 2.0]
        assert len(high_vis) >= 1

    def test_has_multiple_emergencies(self, scenario):
        emergencies = [f for f in scenario.flights if f.emergency != EmergencyLevel.NONE]
        assert len(emergencies) >= 3

    def test_has_fuel_critical(self, scenario):
        critical = [f for f in scenario.flights if f.fuel_minutes <= 10]
        assert len(critical) >= 2

    def test_has_mixed_wake_categories(self, scenario):
        categories = {f.wake_category for f in scenario.flights}
        assert len(categories) >= 3  # at least LIGHT, MEDIUM, HEAVY


class TestHardScenario:
    @pytest.fixture
    def scenario(self):
        return get_task_scenario("hard")

    def test_flight_count(self, scenario):
        assert len(scenario.flights) == 12

    def test_three_maydays(self, scenario):
        maydays = [f for f in scenario.flights if f.emergency == EmergencyLevel.MAYDAY]
        assert len(maydays) == 3

    def test_two_pan_pans(self, scenario):
        pan_pans = [f for f in scenario.flights if f.emergency == EmergencyLevel.PAN_PAN]
        assert len(pan_pans) == 2

    def test_has_cargo_flight(self, scenario):
        cargo = [f for f in scenario.flights if f.passengers == 0]
        assert len(cargo) >= 1

    def test_has_vfr_aircraft(self, scenario):
        """At least one aircraft needs visibility >= 3nm (VFR)."""
        vfr = [f for f in scenario.flights if f.min_visibility_nm >= 3.0]
        assert len(vfr) >= 1

    def test_oscillating_weather(self, scenario):
        """Weather timeline must go down then back up."""
        vis_values = [e["visibility_nm"] for e in scenario.weather_timeline if "visibility_nm" in e]
        assert min(vis_values) < 2.0  # goes low
        assert max(vis_values) > 4.0  # comes back up

    def test_unique_callsigns(self, scenario):
        callsigns = [f.callsign for f in scenario.flights]
        assert len(callsigns) == len(set(callsigns))

    def test_multiple_fuel_critical(self, scenario):
        critical = [f for f in scenario.flights if f.fuel_minutes <= 10]
        assert len(critical) >= 4
