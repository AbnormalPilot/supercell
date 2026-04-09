"""Simplified ATC models for hackathon submission."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import IntEnum


class EmergencyLevel(IntEnum):
    NONE = 0
    PAN_PAN = 1
    MAYDAY = 2


class WakeCategory(IntEnum):
    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3
    SUPER = 4


@dataclass
class Flight:
    """Inbound flight for landing."""
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


@dataclass
class Weather:
    """Airport weather conditions."""
    visibility_nm: float = 10.0
    wind_knots: float = 8.0
    crosswind_knots: float = 3.0
    ceiling_feet: float = 5000.0
    precipitation: str = "none"
    trend: str = "stable"


@dataclass
class FlightInfo:
    """Flight data for API responses."""
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


@dataclass  
class WeatherInfo:
    """Weather data for API responses."""
    visibility_nm: float = 10.0
    wind_knots: float = 0.0
    crosswind_knots: float = 0.0
    ceiling_feet: float = 5000.0
    precipitation: str = "none"
    trend: str = "stable"


@dataclass
class ATCAction:
    """Agent action - which flight to land."""
    flight_index: int = 0


@dataclass
class ATCObservation:
    """Environment observation."""
    flights: List[FlightInfo] = field(default_factory=list)
    weather: WeatherInfo = field(default_factory=WeatherInfo)
    runway_free_in_steps: int = 0
    time_step: int = 0
    max_time_steps: int = 50
    landed_safely: int = 0
    crashed: int = 0
    total_flights: int = 0
    task_id: str = "easy"
    task_name: str = ""
    done: bool = False
    reward: float = 0.0
    episode_reward: float = 0.0
    instructions: str = ""


@dataclass
class ATCState:
    """Internal episode state."""
    task_id: str = "easy"
    task_name: str = ""
    time_step: int = 0
    landed_safely: int = 0
    crashed: int = 0
    total_flights: int = 0
    episode_reward: float = 0.0
    flights: List[Flight] = field(default_factory=list)
    weather: Weather = field(default_factory=Weather)
    runway_free_in_steps: int = 0
    landing_log: List[Dict[str, Any]] = field(default_factory=list)
    crash_log: List[Dict[str, Any]] = field(default_factory=list)
    max_steps: int = 50
    separation_steps: int = 2
    weather_timeline: List[Dict] = field(default_factory=list)
