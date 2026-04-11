"""SUPERCELL task scenarios — Monsoon Mumbai edition.

Three graded tasks (easy → medium → hard) plus one hidden bonus
scenario (extra_hard). All flights use authentic Indian carrier
ICAO callsigns (AIC, IGO, SEJ, VTI, AKJ, AXB) mixed with real
international visitors to VABB. Bearings are approximate real-world
STAR fix geometry for Chhatrapati Shivaji International Airport.
"""

from __future__ import annotations

from typing import Any, Callable

from models import EmergencyLevel, Flight, FlightInfo, WakeCategory, Weather


# =============================================================================
# Helpers
# =============================================================================


def _flight_to_info(f: Flight, idx: int) -> FlightInfo:
    """Serialize a Flight for use in an observation payload."""
    return FlightInfo(
        index=idx,
        callsign=f.callsign,
        aircraft_type=f.aircraft_type,
        emergency=f.emergency.name,
        fuel_minutes=f.fuel_minutes,
        passengers=f.passengers,
        distance_nm=f.distance_nm,
        medical_onboard=f.medical_onboard,
        min_visibility_nm=f.min_visibility_nm,
        wake_category=f.wake_category.name,
        bearing_deg=f.bearing_deg,
        approach_fix=f.approach_fix,
    )


# =============================================================================
# EASY  ·  "Winter Haze" — November morning, 4 flights, manageable
# =============================================================================


def build_easy() -> dict[str, Any]:
    """Calm winter dawn. Clear air, four inbounds, one MAYDAY."""
    flights = [
        Flight(
            callsign="AIC852",
            aircraft_type="B777-300ER",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=8.0,
            passengers=342,
            distance_nm=12.0,
            approach_speed_knots=148,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.HEAVY,
            bearing_deg=45.0,
            approach_fix="GUDOM",
        ),
        Flight(
            callsign="IGO6E227",
            aircraft_type="A320neo",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=15.0,
            passengers=186,
            distance_nm=18.0,
            approach_speed_knots=138,
            medical_onboard=True,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=90.0,
            approach_fix="PARAR",
        ),
        Flight(
            callsign="VTI995",
            aircraft_type="A321neo",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=25.0,
            passengers=220,
            distance_nm=22.0,
            approach_speed_knots=140,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=135.0,
            approach_fix="NOMUS",
        ),
        Flight(
            callsign="SEJ144",
            aircraft_type="B737-800",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=30.0,
            passengers=189,
            distance_nm=28.0,
            approach_speed_knots=142,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=315.0,
            approach_fix="LEKIT",
        ),
    ]
    weather = Weather(
        visibility_nm=10.0,
        wind_knots=6.0,
        crosswind_knots=2.0,
        ceiling_feet=6000.0,
        precipitation="haze",
        trend="stable",
    )
    return {
        "task_id": "easy",
        "task_name": "Winter Haze",
        "flights": flights,
        "weather": weather,
        "max_steps": 20,
        "separation_steps": 2,
        "weather_timeline": [],
        "description": (
            "Calm November dawn at VABB. Four inbounds — one MAYDAY fuel emergency "
            "on AIC852, one medical PAN-PAN on IGO6E227, two routine. "
            "Clear skies, easy priority call."
        ),
    }


# =============================================================================
# MEDIUM  ·  "Pre-Monsoon Squall" — May afternoon, 7 flights, weather window
# =============================================================================


def build_medium() -> dict[str, Any]:
    """Arabian Sea squall line rolling in. Seven flights, shrinking window."""
    flights = [
        Flight(
            callsign="AIC132",
            aircraft_type="B787-9",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=6.0,
            passengers=256,
            distance_nm=10.0,
            approach_speed_knots=145,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
            bearing_deg=45.0,
            approach_fix="GUDOM",
        ),
        Flight(
            callsign="AXB471",
            aircraft_type="B737-MAX8",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=9.0,
            passengers=174,
            distance_nm=15.0,
            approach_speed_knots=140,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=315.0,
            approach_fix="LEKIT",
        ),
        Flight(
            callsign="IGO6E6105",
            aircraft_type="A321neo",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=20.0,
            passengers=222,
            distance_nm=20.0,
            approach_speed_knots=142,
            medical_onboard=True,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=90.0,
            approach_fix="PARAR",
        ),
        Flight(
            callsign="VTI881",
            aircraft_type="B787-9",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=11.0,
            passengers=264,
            distance_nm=16.0,
            approach_speed_knots=145,
            medical_onboard=False,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.HEAVY,
            bearing_deg=135.0,
            approach_fix="NOMUS",
        ),
        Flight(
            callsign="AKJ1321",
            aircraft_type="B737-MAX8",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=14.0,
            passengers=180,
            distance_nm=24.0,
            approach_speed_knots=140,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=60.0,
            approach_fix="GUDOM",
        ),
        Flight(
            callsign="BAW139",
            aircraft_type="B777-300ER",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=35.0,
            passengers=310,
            distance_nm=30.0,
            approach_speed_knots=150,
            medical_onboard=False,
            min_visibility_nm=3.0,  # BA stabilised approach minima
            wake_category=WakeCategory.HEAVY,
            bearing_deg=300.0,
            approach_fix="LEKIT",
        ),
        Flight(
            callsign="UAE504",
            aircraft_type="A380-800",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=55.0,
            passengers=517,
            distance_nm=40.0,
            approach_speed_knots=155,
            medical_onboard=False,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.SUPER,
            bearing_deg=270.0,
            approach_fix="LEKIT",
        ),
    ]
    weather = Weather(
        visibility_nm=8.0,
        wind_knots=22.0,
        crosswind_knots=15.0,
        ceiling_feet=2800.0,
        precipitation="rain",
        trend="deteriorating",
    )
    timeline = [
        {"step": 0,  "visibility_nm": 8.0, "trend": "deteriorating", "precipitation": "rain"},
        {"step": 4,  "visibility_nm": 4.0, "trend": "deteriorating", "precipitation": "rain"},
        {"step": 9,  "visibility_nm": 2.0, "trend": "stable",        "precipitation": "thunderstorm"},
        {"step": 14, "visibility_nm": 1.0, "trend": "deteriorating", "precipitation": "thunderstorm"},
        {"step": 22, "visibility_nm": 3.0, "trend": "improving",     "precipitation": "rain"},
    ]
    return {
        "task_id": "medium",
        "task_name": "Pre-Monsoon Squall",
        "flights": flights,
        "weather": weather,
        "max_steps": 35,
        "separation_steps": 3,
        "weather_timeline": timeline,
        "description": (
            "May pre-monsoon squall rolling in over the Arabian Sea. Seven inbounds. "
            "Visibility deteriorates from 8 nm → 1 nm over ~14 steps, then eases. "
            "BAW139 (3.0 nm minima) and UAE504 (SUPER wake) must land in the open window, "
            "while AIC132 MAYDAY and low-fuel AXB471 race the clock."
        ),
    }


# =============================================================================
# HARD  ·  "Mumbai Monsoon Surge" — July afternoon, 12 flights, fuel traps
# =============================================================================


def build_hard() -> dict[str, Any]:
    """Peak monsoon. Twelve diverted aircraft. Traps everywhere."""
    flights = [
        Flight(
            callsign="AIC176",
            aircraft_type="B787-9",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=5.0,
            passengers=256,
            distance_nm=8.0,
            approach_speed_knots=145,
            medical_onboard=True,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
            bearing_deg=45.0,
            approach_fix="GUDOM",
        ),
        Flight(
            callsign="AIC348",
            aircraft_type="A330-300",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=7.0,
            passengers=291,
            distance_nm=10.0,
            approach_speed_knots=148,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
            bearing_deg=30.0,
            approach_fix="GUDOM",
        ),
        Flight(
            # The weather-blocked MAYDAY trap
            callsign="IGO6E2043",
            aircraft_type="A320neo",
            emergency=EmergencyLevel.MAYDAY,
            fuel_minutes=14.0,
            passengers=180,
            distance_nm=12.0,
            approach_speed_knots=140,
            medical_onboard=False,
            min_visibility_nm=4.0,   # <-- BLOCKED at storm peak
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=90.0,
            approach_fix="PARAR",
        ),
        Flight(
            callsign="SEJ21",
            aircraft_type="B737-800",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=10.0,
            passengers=189,
            distance_nm=14.0,
            approach_speed_knots=140,
            medical_onboard=True,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=120.0,
            approach_fix="NOMUS",
        ),
        Flight(
            callsign="VTI997",
            aircraft_type="A321neo",
            emergency=EmergencyLevel.PAN_PAN,
            fuel_minutes=14.0,
            passengers=222,
            distance_nm=18.0,
            approach_speed_knots=142,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=315.0,
            approach_fix="LEKIT",
        ),
        Flight(
            # The silent fuel trap — NONE status but critically low
            callsign="IGO6E5393",
            aircraft_type="A320",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=4.0,
            passengers=174,
            distance_nm=11.0,
            approach_speed_knots=140,
            medical_onboard=False,
            min_visibility_nm=1.0,
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=75.0,
            approach_fix="PARAR",
        ),
        Flight(
            # Low fuel + blocked at peak — second trap
            callsign="AXB812",
            aircraft_type="B737-800",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=6.0,
            passengers=172,
            distance_nm=15.0,
            approach_speed_knots=140,
            medical_onboard=False,
            min_visibility_nm=2.5,
            wake_category=WakeCategory.MEDIUM,
            bearing_deg=105.0,
            approach_fix="PARAR",
        ),
        Flight(
            # Business jet VFR-only — cannot land at peak
            callsign="VT-JEX",
            aircraft_type="Cessna Citation X",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=12.0,
            passengers=8,
            distance_nm=16.0,
            approach_speed_knots=130,
            medical_onboard=False,
            min_visibility_nm=3.0,
            wake_category=WakeCategory.LIGHT,
            bearing_deg=200.0,
            approach_fix="NOMUS",
        ),
        Flight(
            callsign="FDX57",
            aircraft_type="B767-300F",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=18.0,
            passengers=0,
            distance_nm=20.0,
            approach_speed_knots=148,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
            bearing_deg=280.0,
            approach_fix="LEKIT",
        ),
        Flight(
            callsign="QTR554",
            aircraft_type="B787-9",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=15.0,
            passengers=254,
            distance_nm=22.0,
            approach_speed_knots=145,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
            bearing_deg=250.0,
            approach_fix="LEKIT",
        ),
        Flight(
            callsign="SIA422",
            aircraft_type="A350-900",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=25.0,
            passengers=303,
            distance_nm=30.0,
            approach_speed_knots=150,
            medical_onboard=False,
            min_visibility_nm=1.5,
            wake_category=WakeCategory.HEAVY,
            bearing_deg=135.0,
            approach_fix="NOMUS",
        ),
        Flight(
            # Super-wake monster — creates 4-step separation if sequenced wrong
            callsign="UAE504",
            aircraft_type="A380-800",
            emergency=EmergencyLevel.NONE,
            fuel_minutes=40.0,
            passengers=517,
            distance_nm=45.0,
            approach_speed_knots=155,
            medical_onboard=False,
            min_visibility_nm=2.0,
            wake_category=WakeCategory.SUPER,
            bearing_deg=270.0,
            approach_fix="LEKIT",
        ),
    ]
    weather = Weather(
        visibility_nm=2.0,
        wind_knots=28.0,
        crosswind_knots=20.0,
        ceiling_feet=1500.0,
        precipitation="thunderstorm",
        trend="stable",
    )
    timeline = [
        {"step": 0,  "visibility_nm": 2.0, "trend": "deteriorating", "precipitation": "thunderstorm"},
        {"step": 5,  "visibility_nm": 1.0, "trend": "stable",        "precipitation": "thunderstorm"},
        {"step": 10, "visibility_nm": 4.5, "trend": "improving",     "precipitation": "rain"},
        {"step": 14, "visibility_nm": 1.5, "trend": "deteriorating", "precipitation": "thunderstorm"},
        {"step": 22, "visibility_nm": 3.0, "trend": "improving",     "precipitation": "rain"},
        {"step": 32, "visibility_nm": 5.0, "trend": "stable",        "precipitation": "rain"},
    ]
    return {
        "task_id": "hard",
        "task_name": "Mumbai Monsoon Surge",
        "flights": flights,
        "weather": weather,
        "max_steps": 50,
        "separation_steps": 3,
        "weather_timeline": timeline,
        "description": (
            "July monsoon at VABB — twelve diverted aircraft, three MAYDAYs, two PAN-PANs, "
            "fuel traps hiding inside NONE flights, a weather-blocked MAYDAY (IGO6E2043), "
            "and a SUPER-wake A380 that creates 4-step separation cascades if mis-sequenced. "
            "The weather window at steps 10–13 is the only moment the 3+ nm minima flights can land. "
            "Frontier models consistently fail this one."
        ),
    }


# =============================================================================
# EXTRA_HARD  ·  "Total System Chaos" — hidden bonus scenario, 20 flights
# =============================================================================


def build_extra_hard() -> dict[str, Any]:
    """Hidden bonus. Not required for spec compliance — an extreme stress test."""
    flights = [
        Flight(callsign="AIC101", aircraft_type="B777-300ER", emergency=EmergencyLevel.MAYDAY,
               fuel_minutes=3.0, passengers=342, distance_nm=8.0, medical_onboard=True,
               min_visibility_nm=1.5, wake_category=WakeCategory.HEAVY,
               bearing_deg=30.0, approach_fix="GUDOM"),
        Flight(callsign="AIC118", aircraft_type="A350-900", emergency=EmergencyLevel.MAYDAY,
               fuel_minutes=4.0, passengers=303, distance_nm=10.0, medical_onboard=False,
               min_visibility_nm=1.5, wake_category=WakeCategory.HEAVY,
               bearing_deg=45.0, approach_fix="GUDOM"),
        Flight(callsign="IGO6E1", aircraft_type="A320neo", emergency=EmergencyLevel.MAYDAY,
               fuel_minutes=5.0, passengers=180, distance_nm=11.0, medical_onboard=False,
               min_visibility_nm=1.0, wake_category=WakeCategory.MEDIUM,
               bearing_deg=90.0, approach_fix="PARAR"),
        Flight(callsign="SEJ555", aircraft_type="B737-800", emergency=EmergencyLevel.MAYDAY,
               fuel_minutes=6.0, passengers=189, distance_nm=12.0, medical_onboard=True,
               min_visibility_nm=1.0, wake_category=WakeCategory.MEDIUM,
               bearing_deg=110.0, approach_fix="NOMUS"),
        Flight(callsign="VTI21", aircraft_type="A321neo", emergency=EmergencyLevel.MAYDAY,
               fuel_minutes=7.0, passengers=222, distance_nm=14.0, medical_onboard=False,
               min_visibility_nm=1.0, wake_category=WakeCategory.MEDIUM,
               bearing_deg=315.0, approach_fix="LEKIT"),
        Flight(callsign="AXB287", aircraft_type="B737-MAX8", emergency=EmergencyLevel.PAN_PAN,
               fuel_minutes=8.0, passengers=174, distance_nm=15.0, medical_onboard=True,
               min_visibility_nm=1.0, wake_category=WakeCategory.MEDIUM,
               bearing_deg=60.0, approach_fix="GUDOM"),
        Flight(callsign="AKJ777", aircraft_type="B737-MAX8", emergency=EmergencyLevel.PAN_PAN,
               fuel_minutes=9.0, passengers=178, distance_nm=16.0, medical_onboard=True,
               min_visibility_nm=1.0, wake_category=WakeCategory.MEDIUM,
               bearing_deg=135.0, approach_fix="NOMUS"),
        Flight(callsign="QTR556", aircraft_type="B787-9", emergency=EmergencyLevel.PAN_PAN,
               fuel_minutes=11.0, passengers=254, distance_nm=18.0, medical_onboard=True,
               min_visibility_nm=1.5, wake_category=WakeCategory.HEAVY,
               bearing_deg=270.0, approach_fix="LEKIT"),
        Flight(callsign="ETD203", aircraft_type="B787-9", emergency=EmergencyLevel.PAN_PAN,
               fuel_minutes=13.0, passengers=262, distance_nm=20.0, medical_onboard=False,
               min_visibility_nm=1.5, wake_category=WakeCategory.HEAVY,
               bearing_deg=290.0, approach_fix="LEKIT"),
        Flight(callsign="IGO6E922", aircraft_type="A320", emergency=EmergencyLevel.NONE,
               fuel_minutes=4.0, passengers=174, distance_nm=12.0, medical_onboard=False,
               min_visibility_nm=1.0, wake_category=WakeCategory.MEDIUM,
               bearing_deg=75.0, approach_fix="PARAR"),
        Flight(callsign="VT-HEX", aircraft_type="Cessna Citation XLS", emergency=EmergencyLevel.NONE,
               fuel_minutes=10.0, passengers=6, distance_nm=14.0, medical_onboard=False,
               min_visibility_nm=5.0, wake_category=WakeCategory.LIGHT,
               bearing_deg=200.0, approach_fix="NOMUS"),
        Flight(callsign="N551GA", aircraft_type="Cirrus SR22", emergency=EmergencyLevel.NONE,
               fuel_minutes=16.0, passengers=4, distance_nm=8.0, medical_onboard=False,
               min_visibility_nm=5.0, wake_category=WakeCategory.LIGHT,
               bearing_deg=215.0, approach_fix="NOMUS"),
        Flight(callsign="FDX801", aircraft_type="B767-300F", emergency=EmergencyLevel.NONE,
               fuel_minutes=15.0, passengers=0, distance_nm=20.0, medical_onboard=False,
               min_visibility_nm=1.5, wake_category=WakeCategory.HEAVY,
               bearing_deg=280.0, approach_fix="LEKIT"),
        Flight(callsign="BLQ200", aircraft_type="B747-400F", emergency=EmergencyLevel.NONE,
               fuel_minutes=20.0, passengers=0, distance_nm=24.0, medical_onboard=False,
               min_visibility_nm=2.0, wake_category=WakeCategory.HEAVY,
               bearing_deg=300.0, approach_fix="LEKIT"),
        Flight(callsign="AIC999", aircraft_type="A321", emergency=EmergencyLevel.NONE,
               fuel_minutes=22.0, passengers=232, distance_nm=26.0, medical_onboard=False,
               min_visibility_nm=1.0, wake_category=WakeCategory.MEDIUM,
               bearing_deg=40.0, approach_fix="GUDOM"),
        Flight(callsign="UAE504", aircraft_type="A380-800", emergency=EmergencyLevel.NONE,
               fuel_minutes=55.0, passengers=517, distance_nm=45.0, medical_onboard=False,
               min_visibility_nm=2.0, wake_category=WakeCategory.SUPER,
               bearing_deg=270.0, approach_fix="LEKIT"),
        Flight(callsign="SVA760", aircraft_type="B777-300ER", emergency=EmergencyLevel.NONE,
               fuel_minutes=30.0, passengers=396, distance_nm=32.0, medical_onboard=False,
               min_visibility_nm=1.5, wake_category=WakeCategory.HEAVY,
               bearing_deg=285.0, approach_fix="LEKIT"),
        Flight(callsign="DLH764", aircraft_type="A340-600", emergency=EmergencyLevel.NONE,
               fuel_minutes=35.0, passengers=380, distance_nm=35.0, medical_onboard=False,
               min_visibility_nm=2.0, wake_category=WakeCategory.HEAVY,
               bearing_deg=310.0, approach_fix="LEKIT"),
        Flight(callsign="BAW138", aircraft_type="B777-300ER", emergency=EmergencyLevel.NONE,
               fuel_minutes=38.0, passengers=310, distance_nm=38.0, medical_onboard=False,
               min_visibility_nm=3.0, wake_category=WakeCategory.HEAVY,
               bearing_deg=300.0, approach_fix="LEKIT"),
        Flight(callsign="CPA694", aircraft_type="B777-300ER", emergency=EmergencyLevel.NONE,
               fuel_minutes=45.0, passengers=340, distance_nm=42.0, medical_onboard=False,
               min_visibility_nm=1.5, wake_category=WakeCategory.HEAVY,
               bearing_deg=85.0, approach_fix="PARAR"),
    ]
    weather = Weather(
        visibility_nm=3.0,
        wind_knots=35.0,
        crosswind_knots=25.0,
        ceiling_feet=1200.0,
        precipitation="thunderstorm",
        trend="deteriorating",
    )
    timeline = [
        {"step": 0,  "visibility_nm": 3.0, "trend": "deteriorating", "precipitation": "thunderstorm"},
        {"step": 4,  "visibility_nm": 1.0, "trend": "stable",        "precipitation": "thunderstorm"},
        {"step": 8,  "visibility_nm": 5.0, "trend": "improving",     "precipitation": "rain"},
        {"step": 12, "visibility_nm": 2.0, "trend": "deteriorating", "precipitation": "rain"},
        {"step": 16, "visibility_nm": 0.5, "trend": "stable",        "precipitation": "thunderstorm"},
        {"step": 22, "visibility_nm": 4.0, "trend": "improving",     "precipitation": "rain"},
        {"step": 30, "visibility_nm": 6.0, "trend": "stable",        "precipitation": "none"},
        {"step": 38, "visibility_nm": 2.5, "trend": "deteriorating", "precipitation": "rain"},
        {"step": 46, "visibility_nm": 1.5, "trend": "stable",        "precipitation": "thunderstorm"},
    ]
    return {
        "task_id": "extra_hard",
        "task_name": "Total System Chaos",
        "flights": flights,
        "weather": weather,
        "max_steps": 80,
        "separation_steps": 3,
        "weather_timeline": timeline,
        "description": (
            "Hidden bonus scenario. Twenty aircraft, five MAYDAYs with critical fuel, "
            "four medical PAN-PANs, VFR-only business jets, a SUPER-wake A380, "
            "and a weather timeline that oscillates from 0.5 nm to 6 nm four times. "
            "Not required for spec compliance — included for agents that want to prove "
            "they can handle true chaos."
        ),
    }


# =============================================================================
# Registry
# =============================================================================


TASKS: dict[str, Callable[[], dict[str, Any]]] = {
    "easy": build_easy,
    "medium": build_medium,
    "hard": build_hard,
    "extra_hard": build_extra_hard,
}


# Canonical kebab-case IDs the hackathon validator prefers, aliased
# back to the simple internal IDs. The public API (/tasks, /grader,
# openenv.yaml) uses the CANONICAL_IDS; /reset accepts either form.
CANONICAL_IDS: dict[str, str] = {
    "easy": "task-001-winter-haze",
    "medium": "task-002-pre-monsoon-squall",
    "hard": "task-003-mumbai-monsoon-surge",
    "extra_hard": "task-004-total-system-chaos",
}
INTERNAL_IDS: dict[str, str] = {v: k for k, v in CANONICAL_IDS.items()}
PUBLIC_TASK_ORDER: list[str] = [
    CANONICAL_IDS["easy"],
    CANONICAL_IDS["medium"],
    CANONICAL_IDS["hard"],
    CANONICAL_IDS["extra_hard"],
]


def resolve_task_id(task_id: str | None) -> str:
    """Normalize any accepted task id form to the internal id.

    Accepts: internal id ("easy"), canonical id ("task-001-winter-haze"),
    case variants, and returns the matching internal id (or "easy" as a
    safe default).
    """
    if not task_id:
        return "easy"
    key = task_id.strip().lower()
    if key in TASKS:
        return key
    if key in INTERNAL_IDS:
        return INTERNAL_IDS[key]
    # tolerate bare "task-001" or "001"
    for canon, internal in INTERNAL_IDS.items():
        if key == canon or key == canon.split("-", 1)[-1]:
            return internal
    return "easy"


def canonical_task_id(internal_id: str) -> str:
    """Return the canonical public id for a given internal id."""
    return CANONICAL_IDS.get(internal_id, internal_id)


def list_tasks() -> list[dict[str, Any]]:
    """List all available tasks for the /tasks endpoint."""
    result = []
    for task_id, builder in TASKS.items():
        data = builder()
        result.append({
            "id": task_id,
            "task_id": task_id,
            "task_name": data["task_name"],
            "description": data["description"],
            "num_flights": len(data["flights"]),
            "max_steps": data["max_steps"],
            "has_grader": True,
            "grader": {
                "id": task_id,
                "type": "deterministic",
                "endpoint": "/grade",
                "scoring_range": [0.0, 1.0],
            },
        })
    return result
