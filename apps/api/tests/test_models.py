"""Tests for Pydantic models, enums, and serialization."""

import sys
import os

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    ATCAction,
    ATCObservation,
    ATCState,
    EmergencyLevel,
    Flight,
    FlightInfo,
    WakeCategory,
    Weather,
    WeatherInfo,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------
class TestEmergencyLevel:
    def test_values(self):
        assert EmergencyLevel.NONE == 0
        assert EmergencyLevel.PAN_PAN == 1
        assert EmergencyLevel.MAYDAY == 2

    def test_ordering(self):
        assert EmergencyLevel.MAYDAY > EmergencyLevel.PAN_PAN > EmergencyLevel.NONE

    def test_name_strings(self):
        assert EmergencyLevel.MAYDAY.name == "MAYDAY"
        assert EmergencyLevel.PAN_PAN.name == "PAN_PAN"
        assert EmergencyLevel.NONE.name == "NONE"


class TestWakeCategory:
    def test_values(self):
        assert WakeCategory.LIGHT == 1
        assert WakeCategory.MEDIUM == 2
        assert WakeCategory.HEAVY == 3
        assert WakeCategory.SUPER == 4

    def test_ordering(self):
        assert WakeCategory.SUPER > WakeCategory.HEAVY > WakeCategory.MEDIUM > WakeCategory.LIGHT


# ---------------------------------------------------------------------------
# Internal domain models
# ---------------------------------------------------------------------------
class TestFlight:
    def test_minimal_construction(self):
        f = Flight(
            callsign="TEST01",
            aircraft_type="B737",
            fuel_minutes=30.0,
            passengers=150,
            distance_nm=20.0,
        )
        assert f.callsign == "TEST01"
        assert f.emergency == EmergencyLevel.NONE
        assert f.wake_category == WakeCategory.MEDIUM
        assert f.medical_onboard is False
        assert f.min_visibility_nm == 1.0

    def test_full_construction(self):
        f = Flight(
            callsign="DAL892",
            aircraft_type="A320neo",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=4.0,
            passengers=165,
            distance_nm=12.0,
            approach_speed_knots=135,
            medical_onboard=True,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.HEAVY,
        )
        assert f.emergency == EmergencyLevel.MAYDAY
        assert f.medical_onboard is True
        assert f.wake_category == WakeCategory.HEAVY

    def test_serialization_roundtrip(self):
        f = Flight(
            callsign="AAL100",
            aircraft_type="B777",
            fuel_minutes=60.0,
            passengers=300,
            distance_nm=30.0,
        )
        data = f.model_dump()
        f2 = Flight(**data)
        assert f2 == f


class TestWeather:
    def test_defaults(self):
        w = Weather()
        assert w.visibility_nm == 10.0
        assert w.precipitation == "none"
        assert w.trend == "stable"

    def test_custom_values(self):
        w = Weather(visibility_nm=2.0, precipitation="thunderstorm", trend="deteriorating")
        assert w.visibility_nm == 2.0
        assert w.precipitation == "thunderstorm"


# ---------------------------------------------------------------------------
# API models (wire-format)
# ---------------------------------------------------------------------------
class TestFlightInfo:
    def test_construction(self):
        fi = FlightInfo(
            index=0,
            callsign="UAL441",
            aircraft_type="B737",
            emergency="NONE",
            fuel_minutes=45.0,
            passengers=180,
            distance_nm=20.0,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category="MEDIUM",
        )
        assert fi.can_land_now is True  # default

    def test_json_serializable(self):
        fi = FlightInfo(
            index=1,
            callsign="DAL892",
            aircraft_type="A320",
            emergency="MAYDAY",
            fuel_minutes=4.0,
            passengers=165,
            distance_nm=12.0,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category="MEDIUM",
            can_land_now=True,
        )
        data = fi.model_dump()
        assert isinstance(data, dict)
        assert data["emergency"] == "MAYDAY"


class TestWeatherInfo:
    def test_defaults(self):
        wi = WeatherInfo()
        assert wi.visibility_nm == 10.0
        assert wi.trend == "stable"

    def test_custom(self):
        wi = WeatherInfo(visibility_nm=1.5, precipitation="rain", trend="deteriorating")
        assert wi.visibility_nm == 1.5


class TestATCAction:
    def test_valid_action(self):
        a = ATCAction(flight_index=0)
        assert a.flight_index == 0

    def test_negative_index_rejected(self):
        with pytest.raises(ValidationError):
            ATCAction(flight_index=-1)

    def test_missing_index_rejected(self):
        with pytest.raises(ValidationError):
            ATCAction()  # flight_index is required

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            ATCAction(flight_index=0, bogus="data")

    def test_metadata_allowed(self):
        a = ATCAction(flight_index=2, metadata={"reason": "fuel critical"})
        assert a.metadata["reason"] == "fuel critical"

    def test_json_roundtrip(self):
        a = ATCAction(flight_index=3)
        data = a.model_dump()
        a2 = ATCAction(**data)
        assert a2.flight_index == 3


class TestATCObservation:
    def test_defaults(self):
        obs = ATCObservation()
        assert obs.flights == []
        assert obs.done is False
        assert obs.reward is None
        assert obs.task_id == "easy"
        assert obs.landed_safely == 0

    def test_json_schema_exists(self):
        schema = ATCObservation.model_json_schema()
        assert "properties" in schema
        assert "flights" in schema["properties"]
        assert "weather" in schema["properties"]


class TestATCState:
    def test_defaults(self):
        st = ATCState()
        assert st.step_count == 0
        assert st.episode_reward == 0.0
        assert st.landing_log == []
        assert st.crash_log == []

    def test_custom(self):
        st = ATCState(
            episode_id="test",
            step_count=5,
            task_id="hard",
            crashed=2,
            total_flights=12,
        )
        assert st.task_id == "hard"
        assert st.crashed == 2
