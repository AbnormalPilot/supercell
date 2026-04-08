"""Tests for the inference script's prompt building and action parsing."""

import sys
import os

_api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_repo_root = os.path.dirname(os.path.dirname(_api_root))
sys.path.insert(0, _api_root)
sys.path.insert(0, os.path.join(_repo_root, "scripts"))

from inference import build_prompt, parse_action


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------
class TestBuildPrompt:
    def _make_obs(self, flights=None, weather=None, **kwargs):
        return {
            "observation": {
                "flights": flights or [],
                "weather": weather or {
                    "visibility_nm": 10.0,
                    "wind_knots": 8,
                    "crosswind_knots": 3,
                    "precipitation": "none",
                    "trend": "stable",
                },
                "runway_free_in_steps": 0,
                "time_step": 0,
                "max_time_steps": 15,
                "landed_safely": 0,
                "crashed": 0,
                "total_flights": 4,
                **kwargs,
            }
        }

    def test_returns_string(self):
        prompt = build_prompt(self._make_obs())
        assert isinstance(prompt, str)

    def test_contains_weather_info(self):
        prompt = build_prompt(self._make_obs())
        assert "WEATHER" in prompt
        assert "10.0" in prompt  # visibility

    def test_contains_runway_info(self):
        prompt = build_prompt(self._make_obs())
        assert "RUNWAY" in prompt

    def test_contains_flight_info(self):
        flights = [
            {
                "index": 0,
                "callsign": "DAL892",
                "aircraft_type": "A320",
                "emergency": "MAYDAY",
                "fuel_minutes": 4.0,
                "passengers": 165,
                "distance_nm": 12.0,
                "medical_onboard": False,
                "min_visibility_nm": 1.0,
                "wake_category": "MEDIUM",
                "can_land_now": True,
            }
        ]
        prompt = build_prompt(self._make_obs(flights=flights))
        assert "DAL892" in prompt
        assert "MAYDAY" in prompt
        assert "4.0" in prompt

    def test_fuel_critical_flagged(self):
        flights = [
            {
                "index": 0,
                "callsign": "TEST01",
                "aircraft_type": "B737",
                "emergency": "NONE",
                "fuel_minutes": 5.0,
                "passengers": 100,
                "distance_nm": 20.0,
                "medical_onboard": False,
                "min_visibility_nm": 1.0,
                "wake_category": "MEDIUM",
                "can_land_now": True,
            }
        ]
        prompt = build_prompt(self._make_obs(flights=flights))
        assert "FUEL CRITICAL" in prompt

    def test_medical_flagged(self):
        flights = [
            {
                "index": 0,
                "callsign": "AAL217",
                "aircraft_type": "B757",
                "emergency": "PAN_PAN",
                "fuel_minutes": 30.0,
                "passengers": 210,
                "distance_nm": 25.0,
                "medical_onboard": True,
                "min_visibility_nm": 1.0,
                "wake_category": "MEDIUM",
                "can_land_now": True,
            }
        ]
        prompt = build_prompt(self._make_obs(flights=flights))
        assert "MEDICAL" in prompt

    def test_weather_hold_flagged(self):
        flights = [
            {
                "index": 0,
                "callsign": "TEST01",
                "aircraft_type": "B737",
                "emergency": "NONE",
                "fuel_minutes": 50.0,
                "passengers": 100,
                "distance_nm": 20.0,
                "medical_onboard": False,
                "min_visibility_nm": 1.0,
                "wake_category": "MEDIUM",
                "can_land_now": False,
            }
        ]
        prompt = build_prompt(self._make_obs(flights=flights))
        assert "CANNOT LAND" in prompt

    def test_contains_json_instruction(self):
        prompt = build_prompt(self._make_obs())
        assert "flight_index" in prompt

    def test_handles_nested_observation(self):
        """Prompt builder handles both raw obs and wrapped obs."""
        raw = {
            "flights": [],
            "weather": {"visibility_nm": 10, "wind_knots": 8, "crosswind_knots": 3, "precipitation": "none", "trend": "stable"},
            "runway_free_in_steps": 0,
            "time_step": 0,
            "max_time_steps": 15,
            "landed_safely": 0,
            "crashed": 0,
            "total_flights": 0,
        }
        prompt = build_prompt(raw)
        assert isinstance(prompt, str)
        assert "WEATHER" in prompt


# ---------------------------------------------------------------------------
# Action parsing
# ---------------------------------------------------------------------------
class TestParseAction:
    def test_valid_json(self):
        assert parse_action('{"flight_index": 0}') == 0

    def test_json_with_whitespace(self):
        assert parse_action('  { "flight_index" : 2 }  ') == 2

    def test_json_in_markdown(self):
        text = 'I recommend landing flight 1.\n```json\n{"flight_index": 1}\n```'
        assert parse_action(text) == 1

    def test_json_with_extra_fields(self):
        assert parse_action('{"flight_index": 3, "reason": "fuel low"}') == 3

    def test_bare_number_fallback(self):
        assert parse_action("flight_index: 2") == 2

    def test_digit_fallback(self):
        assert parse_action("I choose flight 0") == 0

    def test_returns_none_for_empty(self):
        assert parse_action("") is None

    def test_returns_none_for_no_numbers(self):
        assert parse_action("I don't know which flight to pick") is None

    def test_multiline_json(self):
        text = """Based on my analysis:
{
  "flight_index": 4
}
"""
        assert parse_action(text) == 4

    def test_single_quotes_fallback(self):
        assert parse_action("flight_index': 1") == 1

    def test_large_index(self):
        assert parse_action('{"flight_index": 11}') == 11
