"""SUPERCELL — OpenEnv-compliant Pydantic models.

Action, Observation, and State all inherit from the canonical
`openenv.core.env_server.types` base classes so that the serializer
in `openenv.core.env_server.http_server` can round-trip payloads
correctly, and so `/schema` exposes all three schemas.

VABB Mumbai ATC Emergency Triage environment.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from openenv.core.env_server.types import Action, Observation, State
from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================


class EmergencyLevel(IntEnum):
    NONE = 0
    PAN_PAN = 1  # Urgent, not life-threatening
    MAYDAY = 2   # Life-threatening


class WakeCategory(IntEnum):
    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3
    SUPER = 4


# =============================================================================
# Domain models (internal use — not inherited from Action/Observation)
# =============================================================================


class Flight(BaseModel):
    """Inbound flight on approach to VABB (internal simulation object)."""

    model_config = ConfigDict(use_enum_values=False, arbitrary_types_allowed=True)

    callsign: str
    aircraft_type: str
    emergency: EmergencyLevel = EmergencyLevel.NONE
    fuel_minutes: float = 30.0
    passengers: int = 100
    distance_nm: float = 20.0
    approach_speed_knots: float = 140.0
    medical_onboard: bool = False
    min_visibility_nm: float = 1.0
    wake_category: WakeCategory = WakeCategory.MEDIUM
    bearing_deg: float = 90.0
    approach_fix: str = "PARAR"


class Weather(BaseModel):
    """VABB airport weather snapshot (internal)."""

    visibility_nm: float = 10.0
    wind_knots: float = 8.0
    crosswind_knots: float = 3.0
    ceiling_feet: float = 5000.0
    precipitation: str = "none"
    trend: str = "stable"


# =============================================================================
# Payload sub-models (appear inside the observation)
# =============================================================================


class FlightInfo(BaseModel):
    """Flight as serialized into the observation payload."""

    model_config = ConfigDict(extra="forbid")

    index: int
    callsign: str
    aircraft_type: str
    emergency: str
    fuel_minutes: float
    passengers: int
    distance_nm: float
    medical_onboard: bool
    min_visibility_nm: float
    wake_category: str
    can_land_now: bool = True
    bearing_deg: float = 90.0
    approach_fix: str = "PARAR"


class WeatherInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visibility_nm: float = 10.0
    wind_knots: float = 0.0
    crosswind_knots: float = 0.0
    ceiling_feet: float = 5000.0
    precipitation: str = "none"
    trend: str = "stable"


# =============================================================================
# OpenEnv contract classes (Action / Observation / State)
# =============================================================================


class ATCAction(Action):
    """Agent action: clear a specific inbound flight to land.

    Inherits `metadata: Dict[str, Any]` from the canonical Action base.
    """

    flight_index: int = Field(
        default=0,
        ge=0,
        description="0-based index into observation.flights — which flight to land next.",
    )


class ATCObservation(Observation):
    """VABB tower observation returned by `reset()` and `step()`.

    Inherits `done`, `reward`, and `metadata` from the canonical
    Observation base (the HTTP serializer pulls `reward` and `done`
    out to the response envelope).
    """

    flights: list[FlightInfo] = Field(default_factory=list)
    weather: WeatherInfo = Field(default_factory=WeatherInfo)
    runway_free_in_steps: int = 0
    time_step: int = 0
    max_time_steps: int = 50
    landed_safely: int = 0
    crashed: int = 0
    total_flights: int = 0
    task_id: str = "easy"
    task_name: str = ""
    episode_reward: float = 0.0
    instructions: str = ""


class ATCState(State):
    """Internal episode state.

    Inherits `episode_id` and `step_count` from the canonical State base.
    Uses `extra="allow"` to tolerate the domain fields we append.
    """

    task_id: str = "easy"
    task_name: str = ""
    time_step: int = 0
    landed_safely: int = 0
    crashed: int = 0
    total_flights: int = 0
    episode_reward: float = 0.0
    flights: list[Flight] = Field(default_factory=list)
    weather: Weather = Field(default_factory=Weather)
    runway_free_in_steps: int = 0
    landing_log: list[dict[str, Any]] = Field(default_factory=list)
    crash_log: list[dict[str, Any]] = Field(default_factory=list)
    max_steps: int = 50
    separation_steps: int = 2
    weather_timeline: list[dict[str, Any]] = Field(default_factory=list)
