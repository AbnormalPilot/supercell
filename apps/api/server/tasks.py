"""Task scenario definitions for ATC-Triage-v1.

Each task creates a deterministic scenario (given the same seed) with
a set of flights, weather conditions, and constraints.

Difficulty: easy < medium < hard
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models import EmergencyLevel, Flight, WakeCategory, Weather


@dataclass
class Scenario:
    """A fully-specified ATC scenario."""

    task_id: str
    task_name: str
    flights: list[Flight]
    weather: Weather
    max_steps: int
    separation_steps: int  # base runway separation in time-steps
    weather_timeline: list[dict] = field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------
# Weather timelines (step -> weather override)
# ---------------------------------------------------------------------------

_STORM_TIMELINE: list[dict] = [
    {"step": 0, "visibility_nm": 8.0, "trend": "deteriorating", "precipitation": "none"},
    {"step": 6, "visibility_nm": 5.0, "trend": "deteriorating", "precipitation": "rain"},
    {"step": 10, "visibility_nm": 3.0, "trend": "deteriorating", "precipitation": "rain"},
    {"step": 14, "visibility_nm": 1.5, "trend": "stable", "precipitation": "rain"},
    {"step": 20, "visibility_nm": 1.0, "trend": "stable", "precipitation": "thunderstorm"},
]

_CRISIS_TIMELINE: list[dict] = [
    {"step": 0, "visibility_nm": 6.0, "trend": "deteriorating", "precipitation": "rain"},
    {"step": 6, "visibility_nm": 3.0, "trend": "deteriorating", "precipitation": "rain"},
    {"step": 10, "visibility_nm": 1.0, "trend": "stable", "precipitation": "thunderstorm"},
    {"step": 16, "visibility_nm": 3.5, "trend": "improving", "precipitation": "rain"},
    {"step": 20, "visibility_nm": 5.0, "trend": "deteriorating", "precipitation": "rain"},
    {"step": 26, "visibility_nm": 1.5, "trend": "stable", "precipitation": "thunderstorm"},
    {"step": 34, "visibility_nm": 4.0, "trend": "improving", "precipitation": "rain"},
    {"step": 40, "visibility_nm": 6.0, "trend": "stable", "precipitation": "none"},
]


# ---------------------------------------------------------------------------
# Task builders
# ---------------------------------------------------------------------------

def _build_easy() -> Scenario:
    """Clear Skies Priority — 4 flights, obvious emergency ordering."""
    flights = [
        Flight(
            callsign="UAL441",
            aircraft_type="B737-800",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=45.0,
            passengers=180,
            distance_nm=20.0,
            approach_speed_knots=140,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
        ),
        Flight(
            callsign="DAL892",
            aircraft_type="A320neo",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=4.0,
            passengers=165,
            distance_nm=12.0,
            approach_speed_knots=135,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
        ),
        Flight(
            callsign="AAL217",
            aircraft_type="B757-200",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=30.0,
            passengers=210,
            distance_nm=25.0,
            approach_speed_knots=145,
            medical_onboard=True,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
        ),
        Flight(
            callsign="SWA103",
            aircraft_type="B737-700",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=50.0,
            passengers=143,
            distance_nm=18.0,
            approach_speed_knots=138,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
        ),
    ]

    weather = Weather(
        visibility_nm=10.0,
        wind_knots=8.0,
        crosswind_knots=3.0,
        ceiling_feet=5000.0,
        precipitation="none",
        trend="stable",
    )

    return Scenario(
        task_id="easy",
        task_name="Clear Skies Priority",
        flights=flights,
        weather=weather,
        max_steps=15,
        separation_steps=2,
        weather_timeline=[],
        description=(
            "4 inbound flights under clear skies. One MAYDAY fuel emergency "
            "(4 min fuel) and one PAN-PAN with medical passenger. "
            "Prioritize correctly to avoid a crash."
        ),
    )


def _build_medium() -> Scenario:
    """Storm Window — 7 flights, deteriorating weather, competing priorities."""
    flights = [
        Flight(
            callsign="DLH401",
            aircraft_type="A340-300",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=35.0,
            passengers=280,
            distance_nm=30.0,
            approach_speed_knots=150,
            medical_onboard=False,
            min_visibility_nm=3.0,  # needs CAT-II or better
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="BAW119",
            aircraft_type="B777-200",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=6.0,
            passengers=310,
            distance_nm=15.0,
            approach_speed_knots=148,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="AFR882",
            aircraft_type="A220-300",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=8.0,
            passengers=140,
            distance_nm=22.0,
            approach_speed_knots=130,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
        ),
        Flight(
            callsign="JBU562",
            aircraft_type="A321neo",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=20.0,
            passengers=195,
            distance_nm=18.0,
            approach_speed_knots=140,
            medical_onboard=True,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
        ),
        Flight(
            callsign="UAE205",
            aircraft_type="A380-800",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=55.0,
            passengers=490,
            distance_nm=35.0,
            approach_speed_knots=155,
            medical_onboard=False,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.SUPER,
        ),
        Flight(
            callsign="NKS447",
            aircraft_type="A320neo",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=12.0,
            passengers=186,
            distance_nm=20.0,
            approach_speed_knots=135,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.MEDIUM,
        ),
        Flight(
            callsign="SKW3341",
            aircraft_type="CRJ-700",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=10.0,
            passengers=65,
            distance_nm=12.0,
            approach_speed_knots=125,
            medical_onboard=False,
            min_visibility_nm=2.0,  # regional — higher minimums
            wake_category=WakeCategory.LIGHT,
        ),
    ]

    weather = Weather(
        visibility_nm=8.0,
        wind_knots=18.0,
        crosswind_knots=12.0,
        ceiling_feet=3000.0,
        precipitation="none",
        trend="deteriorating",
    )

    return Scenario(
        task_id="medium",
        task_name="Storm Window",
        flights=flights,
        weather=weather,
        max_steps=30,
        separation_steps=2,
        weather_timeline=_STORM_TIMELINE,
        description=(
            "7 inbound flights with a storm approaching. Visibility will "
            "drop from 8 nm to 1 nm over ~20 steps. A fuel-critical B777 "
            "MAYDAY, two PAN-PANs, and weather-sensitive heavy aircraft "
            "that must land before the ceiling drops. Balance urgency "
            "against the shrinking weather window."
        ),
    )


def _build_hard() -> Scenario:
    """Mass Diversion Crisis — 12 flights, oscillating weather, cascading emergencies."""
    flights = [
        Flight(
            callsign="UAL921",
            aircraft_type="B787-9",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=5.0,
            passengers=285,
            distance_nm=10.0,
            approach_speed_knots=150,
            medical_onboard=True,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="DAL550",
            aircraft_type="A330-300",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=7.0,
            passengers=260,
            distance_nm=14.0,
            approach_speed_knots=145,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="AAL018",
            aircraft_type="B777-300ER",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=9.0,
            passengers=350,
            distance_nm=18.0,
            approach_speed_knots=152,
            medical_onboard=False,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="SWA655",
            aircraft_type="B737-MAX8",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=10.0,
            passengers=175,
            distance_nm=16.0,
            approach_speed_knots=140,
            medical_onboard=True,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
        ),
        Flight(
            callsign="JBU788",
            aircraft_type="A321neo",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=14.0,
            passengers=200,
            distance_nm=20.0,
            approach_speed_knots=140,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
        ),
        Flight(
            callsign="NKS221",
            aircraft_type="A320neo",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=6.0,
            passengers=186,
            distance_nm=22.0,
            approach_speed_knots=135,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
        ),
        Flight(
            callsign="FDX801",
            aircraft_type="B767-300F",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=18.0,
            passengers=0,  # cargo
            distance_nm=25.0,
            approach_speed_knots=145,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="SKW4412",
            aircraft_type="E175",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=8.0,
            passengers=76,
            distance_nm=12.0,
            approach_speed_knots=125,
            medical_onboard=False,
            min_visibility_nm=2.5,  # regional, higher minimums
            wake_category=WakeCategory.LIGHT,
        ),
        Flight(
            callsign="BAW287",
            aircraft_type="A380-800",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=40.0,
            passengers=475,
            distance_nm=35.0,
            approach_speed_knots=155,
            medical_onboard=False,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.SUPER,
        ),
        Flight(
            callsign="DLH470",
            aircraft_type="A350-900",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=25.0,
            passengers=305,
            distance_nm=28.0,
            approach_speed_knots=148,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="EJA742",
            aircraft_type="CL-350",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=12.0,
            passengers=9,
            distance_nm=15.0,
            approach_speed_knots=120,
            medical_onboard=False,
            min_visibility_nm=3.0,  # VFR-only biz jet
            wake_category=WakeCategory.LIGHT,
        ),
        Flight(
            callsign="AFR991",
            aircraft_type="B787-10",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=15.0,
            passengers=330,
            distance_nm=30.0,
            approach_speed_knots=150,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
    ]

    weather = Weather(
        visibility_nm=6.0,
        wind_knots=25.0,
        crosswind_knots=18.0,
        ceiling_feet=2000.0,
        precipitation="rain",
        trend="deteriorating",
    )

    return Scenario(
        task_id="hard",
        task_name="Mass Diversion Crisis",
        flights=flights,
        weather=weather,
        max_steps=50,
        separation_steps=2,
        weather_timeline=_CRISIS_TIMELINE,
        description=(
            "12 aircraft diverted to your airport after a nearby hub closed. "
            "Three MAYDAY declarations, two PAN-PANs, four fuel-critical "
            "flights, and a weather window that opens and closes. A VFR "
            "business jet and a regional need higher visibility. Cargo "
            "flights carry no passengers. Expect cascading failures if "
            "you don't triage aggressively."
        ),
    )


# Chaos Timeline — rapid, extreme weather swings
_CHAOS_TIMELINE: list[dict] = [
    {"step": 0, "visibility_nm": 3.0, "trend": "deteriorating", "precipitation": "rain"},
    {"step": 4, "visibility_nm": 1.0, "trend": "stable", "precipitation": "thunderstorm"},
    {"step": 8, "visibility_nm": 5.0, "trend": "improving", "precipitation": "rain"},
    {"step": 12, "visibility_nm": 2.0, "trend": "deteriorating", "precipitation": "snow"},
    {"step": 16, "visibility_nm": 0.5, "trend": "stable", "precipitation": "thunderstorm"},
    {"step": 22, "visibility_nm": 4.0, "trend": "improving", "precipitation": "rain"},
    {"step": 28, "visibility_nm": 6.0, "trend": "stable", "precipitation": "none"},
    {"step": 34, "visibility_nm": 2.5, "trend": "deteriorating", "precipitation": "snow"},
    {"step": 40, "visibility_nm": 1.5, "trend": "stable", "precipitation": "rain"},
]


def _build_extra_hard() -> Scenario:
    """Total System Chaos — 20 flights, extreme weather volatility, cascading emergencies."""
    flights = [
        # MAYDAY cluster — 5 critical emergencies
        Flight(
            callsign="UAL891",
            aircraft_type="B787-10",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=3.0,
            passengers=320,
            distance_nm=8.0,
            approach_speed_knots=150,
            medical_onboard=True,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="DAL102",
            aircraft_type="A350-1000",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=4.0,
            passengers=410,
            distance_nm=10.0,
            approach_speed_knots=152,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="AAL33",
            aircraft_type="B777-300ER",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=5.0,
            passengers=396,
            distance_nm=12.0,
            approach_speed_knots=155,
            medical_onboard=False,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="BAW5",
            aircraft_type="A380-800",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=6.0,
            passengers=525,
            distance_nm=14.0,
            approach_speed_knots=158,
            medical_onboard=True,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.SUPER,
        ),
        Flight(
            callsign="KLM601",
            aircraft_type="B747-8",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=7.0,
            passengers=410,
            distance_nm=16.0,
            approach_speed_knots=156,
            medical_onboard=False,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.HEAVY,
        ),
        # PAN-PAN cluster — 4 urgent but stable
        Flight(
            callsign="QFA9",
            aircraft_type="A330-300",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=8.0,
            passengers=295,
            distance_nm=18.0,
            approach_speed_knots=145,
            medical_onboard=True,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="SIA21",
            aircraft_type="A350-900",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=9.0,
            passengers=325,
            distance_nm=20.0,
            approach_speed_knots=148,
            medical_onboard=True,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="CPA548",
            aircraft_type="B777-200ER",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=11.0,
            passengers=317,
            distance_nm=22.0,
            approach_speed_knots=148,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="ANA177",
            aircraft_type="B787-9",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=13.0,
            passengers=292,
            distance_nm=24.0,
            approach_speed_knots=150,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        # Regular flights with challenging constraints
        Flight(
            callsign="JAL62",
            aircraft_type="B737-MAX9",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=15.0,
            passengers=178,
            distance_nm=26.0,
            approach_speed_knots=142,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
        ),
        Flight(
            callsign="UAE225",
            aircraft_type="A380-800",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=45.0,
            passengers=519,
            distance_nm=40.0,
            approach_speed_knots=155,
            medical_onboard=False,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.SUPER,
        ),
        Flight(
            callsign="LH440",
            aircraft_type="A340-600",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=18.0,
            passengers=380,
            distance_nm=30.0,
            approach_speed_knots=150,
            medical_onboard=False,
            min_visibility_nm=3.0,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="AF66",
            aircraft_type="B777-300ER",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=22.0,
            passengers=472,
            distance_nm=35.0,
            approach_speed_knots=152,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="VS3",
            aircraft_type="A350-1000",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=35.0,
            passengers=335,
            distance_nm=32.0,
            approach_speed_knots=153,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        # Regional aircraft with higher visibility minimums
        Flight(
            callsign="SKW4451",
            aircraft_type="E175",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=14.0,
            passengers=76,
            distance_nm=15.0,
            approach_speed_knots=125,
            medical_onboard=False,
            min_visibility_nm=2.5,
            wake_category=WakeCategory.LIGHT,
        ),
        Flight(
            callsign="ASH5842",
            aircraft_type="CRJ-900",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=12.0,
            passengers=76,
            distance_nm=18.0,
            approach_speed_knots=135,
            medical_onboard=False,
            min_visibility_nm=3.0,
            wake_category=WakeCategory.LIGHT,
        ),
        # VFR aircraft — very challenging
        Flight(
            callsign="N551GA",
            aircraft_type="Cirrus SR22",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=10.0,
            passengers=4,
            distance_nm=8.0,
            approach_speed_knots=120,
            medical_onboard=False,
            min_visibility_nm=5.0,
            wake_category=WakeCategory.LIGHT,
        ),
        Flight(
            callsign="N8721F",
            aircraft_type="Cessna 208",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=16.0,
            passengers=9,
            distance_nm=20.0,
            approach_speed_knots=140,
            medical_onboard=False,
            min_visibility_nm=4.0,
            wake_category=WakeCategory.LIGHT,
        ),
        # Cargo flights
        Flight(
            callsign="FDX907",
            aircraft_type="B767-300F",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=28.0,
            passengers=0,
            distance_nm=28.0,
            approach_speed_knots=145,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
        ),
        Flight(
            callsign="UPS29",
            aircraft_type="MD-11F",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=25.0,
            passengers=0,
            distance_nm=30.0,
            approach_speed_knots=148,
            medical_onboard=False,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.HEAVY,
        ),
    ]

    weather = Weather(
        visibility_nm=3.0,
        wind_knots=35.0,
        crosswind_knots=25.0,
        ceiling_feet=1500.0,
        precipitation="rain",
        trend="deteriorating",
    )

    return Scenario(
        task_id="extra_hard",
        task_name="Total System Chaos",
        flights=flights,
        weather=weather,
        max_steps=80,
        separation_steps=2,
        weather_timeline=_CHAOS_TIMELINE,
        description=(
            "20 aircraft in a total system failure scenario. Five MAYDAYs with fuel "
            "critical (<8 min), four PAN-PANs with medical emergencies, VFR aircraft "
            "that need 4-5nm visibility, and extreme weather volatility (snow, "
            "thunderstorms, rapid visibility swings 0.5-6nm). Crosswinds up to 35kt. "
            "Cargo flights have no passengers. Only expert triage can prevent mass casualties."
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

TASKS: dict[str, callable] = {
    "easy": _build_easy,
    "medium": _build_medium,
    "hard": _build_hard,
    "extra_hard": _build_extra_hard,
}


def get_task_scenario(task_id: str, seed: int | None = None) -> Scenario:
    """Return a fully-built scenario for the given task_id."""
    builder = TASKS.get(task_id)
    if builder is None:
        raise ValueError(
            f"Unknown task_id '{task_id}'. Choose from: {list(TASKS.keys())}"
        )
    return builder()


def list_tasks() -> list[dict]:
    """Return metadata for all available tasks."""
    return [
        {
            "task_id": tid,
            "id": tid,
            "task_name": builder().task_name,
            "name": builder().task_name,
            "description": builder().description,
            "num_flights": len(builder().flights),
            "max_steps": builder().max_steps,
            # Explicit grader metadata for external validators that require
            # tasks to declare grading support.
            "has_grader": True,
            "grader_id": tid,
            "grader": {
                "id": tid,
                "type": "deterministic",
                "endpoint": "/grade",
                "scoring_range": [0.0, 1.0],
            },
        }
        for tid, builder in TASKS.items()
    ]
