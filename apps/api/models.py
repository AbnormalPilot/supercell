"""Pydantic models for ATC-Triage-v1 OpenEnv environment."""

from __future__ import annotations

from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Base types (compatible with openenv-core; fallback if not installed)
# ---------------------------------------------------------------------------
try:
    from openenv.core.env_server.types import Action, Observation, State
except ImportError:

    class Action(BaseModel):
        model_config = ConfigDict(
            extra="forbid",
            validate_assignment=True,
            arbitrary_types_allowed=True,
        )
        metadata: dict = Field(default_factory=dict)

    class Observation(BaseModel):
        model_config = ConfigDict(
            extra="forbid",
            validate_assignment=True,
            arbitrary_types_allowed=True,
        )
        done: bool = Field(default=False)
        reward: float | int | bool | None = Field(default=None)
        metadata: dict = Field(default_factory=dict)

    class State(BaseModel):
        model_config = ConfigDict(
            extra="allow",
            validate_assignment=True,
            arbitrary_types_allowed=True,
        )
        episode_id: Optional[str] = None
        step_count: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Domain enums
# ---------------------------------------------------------------------------
class EmergencyLevel(IntEnum):
    NONE = 0
    PAN_PAN = 1   # Urgency condition
    MAYDAY = 2    # Distress / life-threatening


class WakeCategory(IntEnum):
    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3
    SUPER = 4


# ---------------------------------------------------------------------------
# Internal domain models (not part of OpenEnv API, used inside environment)
# ---------------------------------------------------------------------------
class Flight(BaseModel):
    """Internal representation of an inbound flight."""

    callsign: str
    aircraft_type: str
    emergency: EmergencyLevel = EmergencyLevel.NONE
    fuel_minutes: float  # minutes of fuel remaining
    passengers: int
    distance_nm: float
    approach_speed_knots: float = 140.0
    medical_onboard: bool = False
    min_visibility_nm: float = 1.0  # CAT-I ILS minimum
    wake_category: WakeCategory = WakeCategory.MEDIUM


class Weather(BaseModel):
    """Current weather state at the airport."""

    visibility_nm: float = 10.0
    wind_knots: float = 8.0
    crosswind_knots: float = 3.0
    ceiling_feet: float = 5000.0
    precipitation: str = "none"  # none | rain | snow | thunderstorm
    trend: str = "stable"  # stable | improving | deteriorating


# ---------------------------------------------------------------------------
# OpenEnv API models — serialized over the wire
# ---------------------------------------------------------------------------
class FlightInfo(BaseModel):
    """Flight data exposed in observations (JSON-serializable)."""

    index: int
    callsign: str
    aircraft_type: str
    emergency: str  # "NONE" | "PAN_PAN" | "MAYDAY"
    fuel_minutes: float
    passengers: int
    distance_nm: float
    medical_onboard: bool
    min_visibility_nm: float
    wake_category: str
    can_land_now: bool = True  # given current weather


class WeatherInfo(BaseModel):
    """Weather data exposed in observations."""

    visibility_nm: float = 10.0
    wind_knots: float = 0.0
    crosswind_knots: float = 0.0
    ceiling_feet: float = 5000.0
    precipitation: str = "none"
    trend: str = "stable"


class ATCAction(Action):
    """Agent's action: select which flight to clear for landing next."""

    flight_index: int = Field(
        ...,
        description="Index of the flight in the pending-flights list to clear for landing.",
        ge=0,
    )


class ATCObservation(Observation):
    """Full observation returned to the agent each step."""

    flights: list[FlightInfo] = Field(default_factory=list)
    weather: WeatherInfo = WeatherInfo()
    runway_free_in_steps: int = 0
    time_step: int = 0
    max_time_steps: int = 50
    landed_safely: int = 0
    crashed: int = 0
    total_flights: int = 0
    task_id: str = "easy"
    instructions: str = ""


class ATCState(State):
    """Internal episode state."""

    task_id: str = "easy"
    time_step: int = 0
    landed_safely: int = 0
    crashed: int = 0
    total_flights: int = 0
    episode_reward: float = 0.0
    landing_log: list[dict] = Field(default_factory=list)
    crash_log: list[dict] = Field(default_factory=list)
