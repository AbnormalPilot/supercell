"""Simplified task scenarios for hackathon."""

from typing import Dict, List, Callable
from models import Flight, Weather, EmergencyLevel, WakeCategory


def _flight_to_dict(f: Flight, idx: int) -> Dict:
    """Convert flight to dict for API."""
    from models import FlightInfo
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
    )


# =============================================================================
# Task Scenarios
# =============================================================================

def build_easy() -> Dict:
    """Easy: 4 flights, clear skies, simple emergency."""
    flights = [
        Flight("UAL891", "B737-800", EmergencyLevel.MAYDAY, 8.0, 180, 12.0, 140, False, 1.0, WakeCategory.MEDIUM),
        Flight("DAL102", "A320", EmergencyLevel.PAN_PAN, 15.0, 150, 18.0, 138, True, 1.0, WakeCategory.MEDIUM),
        Flight("AAL33", "B737-800", EmergencyLevel.NONE, 25.0, 160, 22.0, 140, False, 1.0, WakeCategory.MEDIUM),
        Flight("BAW5", "A321", EmergencyLevel.NONE, 30.0, 200, 28.0, 142, False, 1.0, WakeCategory.MEDIUM),
    ]
    weather = Weather(10.0, 8.0, 3.0, 5000.0, "none", "stable")
    return {
        "task_id": "easy",
        "task_name": "Clear Skies Priority",
        "flights": flights,
        "weather": weather,
        "max_steps": 20,
        "separation_steps": 2,
        "weather_timeline": [],
        "description": "4 inbound flights under clear skies. One MAYDAY fuel emergency and one PAN-PAN with medical passenger.",
    }


def build_medium() -> Dict:
    """Medium: 7 flights, storm approaching."""
    flights = [
        Flight("UAL891", "B787-9", EmergencyLevel.MAYDAY, 6.0, 280, 10.0, 145, False, 1.5, WakeCategory.HEAVY),
        Flight("DAL102", "A330", EmergencyLevel.PAN_PAN, 12.0, 260, 15.0, 148, True, 1.5, WakeCategory.HEAVY),
        Flight("AAL33", "B737-MAX8", EmergencyLevel.PAN_PAN, 18.0, 175, 20.0, 140, False, 1.0, WakeCategory.MEDIUM),
        Flight("BAW5", "A350-900", EmergencyLevel.NONE, 28.0, 320, 25.0, 150, False, 1.5, WakeCategory.HEAVY),
        Flight("KLM601", "B777-200", EmergencyLevel.NONE, 32.0, 300, 30.0, 152, False, 2.0, WakeCategory.HEAVY),
        Flight("QFA9", "B787-9", EmergencyLevel.NONE, 38.0, 290, 35.0, 145, False, 1.5, WakeCategory.HEAVY),
        Flight("SIA21", "A350-1000", EmergencyLevel.NONE, 45.0, 340, 40.0, 155, False, 2.0, WakeCategory.HEAVY),
    ]
    weather = Weather(5.0, 25.0, 18.0, 2000.0, "rain", "deteriorating")
    timeline = [
        {"step": 0, "visibility_nm": 5.0, "trend": "deteriorating", "precipitation": "rain"},
        {"step": 5, "visibility_nm": 3.0, "trend": "deteriorating", "precipitation": "rain"},
        {"step": 10, "visibility_nm": 2.0, "trend": "stable", "precipitation": "thunderstorm"},
    ]
    return {
        "task_id": "medium",
        "task_name": "Storm Window",
        "flights": flights,
        "weather": weather,
        "max_steps": 35,
        "separation_steps": 2,
        "weather_timeline": timeline,
        "description": "7 inbound flights with a storm approaching. Balance fuel urgency against shrinking weather window.",
    }


def build_hard() -> Dict:
    """Hard: 12 flights, mass diversion crisis."""
    flights = [
        Flight("UAL891", "B787-10", EmergencyLevel.MAYDAY, 5.0, 320, 8.0, 150, True, 1.5, WakeCategory.HEAVY),
        Flight("DAL102", "A350-1000", EmergencyLevel.MAYDAY, 6.0, 410, 10.0, 152, False, 1.5, WakeCategory.HEAVY),
        Flight("AAL33", "B777-300ER", EmergencyLevel.MAYDAY, 7.0, 396, 12.0, 155, False, 2.0, WakeCategory.HEAVY),
        Flight("BAW5", "A380-800", EmergencyLevel.PAN_PAN, 12.0, 525, 15.0, 158, True, 2.0, WakeCategory.SUPER),
        Flight("KLM601", "B747-8", EmergencyLevel.PAN_PAN, 15.0, 410, 18.0, 156, False, 2.0, WakeCategory.HEAVY),
        Flight("QFA9", "A330-300", EmergencyLevel.NONE, 20.0, 295, 22.0, 145, False, 1.5, WakeCategory.HEAVY),
        Flight("SIA21", "A350-900", EmergencyLevel.NONE, 25.0, 325, 26.0, 148, False, 1.5, WakeCategory.HEAVY),
        Flight("CPA548", "B777-200ER", EmergencyLevel.NONE, 30.0, 317, 30.0, 148, False, 1.5, WakeCategory.HEAVY),
        Flight("ANA177", "B787-9", EmergencyLevel.NONE, 35.0, 292, 34.0, 150, False, 1.5, WakeCategory.HEAVY),
        Flight("JAL62", "B737-MAX9", EmergencyLevel.NONE, 40.0, 178, 38.0, 142, False, 1.0, WakeCategory.MEDIUM),
        Flight("UAE225", "A380-800", EmergencyLevel.NONE, 50.0, 519, 45.0, 155, False, 2.0, WakeCategory.SUPER),
        Flight("LH440", "A340-600", EmergencyLevel.NONE, 55.0, 380, 50.0, 150, False, 2.0, WakeCategory.HEAVY),
    ]
    weather = Weather(4.0, 30.0, 22.0, 1500.0, "rain", "deteriorating")
    timeline = [
        {"step": 0, "visibility_nm": 4.0, "trend": "deteriorating", "precipitation": "rain"},
        {"step": 5, "visibility_nm": 2.5, "trend": "stable", "precipitation": "rain"},
        {"step": 10, "visibility_nm": 1.5, "trend": "deteriorating", "precipitation": "thunderstorm"},
        {"step": 18, "visibility_nm": 3.0, "trend": "improving", "precipitation": "rain"},
        {"step": 28, "visibility_nm": 5.0, "trend": "improving", "precipitation": "none"},
    ]
    return {
        "task_id": "hard",
        "task_name": "Mass Diversion Crisis",
        "flights": flights,
        "weather": weather,
        "max_steps": 50,
        "separation_steps": 2,
        "weather_timeline": timeline,
        "description": "12 aircraft diverted with three MAYDAYs, two PAN-PANs, fuel traps, and oscillating weather.",
    }


def build_extra_hard() -> Dict:
    """Extra Hard: 20 flights, total system chaos."""
    flights = [
        Flight("UAL891", "B787-10", EmergencyLevel.MAYDAY, 3.0, 320, 8.0, 150, True, 1.5, WakeCategory.HEAVY),
        Flight("DAL102", "A350-1000", EmergencyLevel.MAYDAY, 4.0, 410, 10.0, 152, False, 1.5, WakeCategory.HEAVY),
        Flight("AAL33", "B777-300ER", EmergencyLevel.MAYDAY, 5.0, 396, 12.0, 155, False, 2.0, WakeCategory.HEAVY),
        Flight("BAW5", "A380-800", EmergencyLevel.MAYDAY, 6.0, 525, 14.0, 158, True, 2.0, WakeCategory.SUPER),
        Flight("KLM601", "B747-8", EmergencyLevel.MAYDAY, 7.0, 410, 16.0, 156, False, 2.0, WakeCategory.HEAVY),
        Flight("QFA9", "A330-300", EmergencyLevel.PAN_PAN, 8.0, 295, 18.0, 145, True, 1.5, WakeCategory.HEAVY),
        Flight("SIA21", "A350-900", EmergencyLevel.PAN_PAN, 9.0, 325, 20.0, 148, True, 1.5, WakeCategory.HEAVY),
        Flight("CPA548", "B777-200ER", EmergencyLevel.PAN_PAN, 11.0, 317, 22.0, 148, False, 1.5, WakeCategory.HEAVY),
        Flight("ANA177", "B787-9", EmergencyLevel.PAN_PAN, 13.0, 292, 24.0, 150, False, 1.5, WakeCategory.HEAVY),
        Flight("JAL62", "B737-MAX9", EmergencyLevel.NONE, 15.0, 178, 26.0, 142, False, 1.0, WakeCategory.MEDIUM),
        Flight("UAE225", "A380-800", EmergencyLevel.NONE, 45.0, 519, 40.0, 155, False, 2.0, WakeCategory.SUPER),
        Flight("LH440", "A340-600", EmergencyLevel.NONE, 18.0, 380, 30.0, 150, False, 2.0, WakeCategory.HEAVY),
        Flight("AF66", "B777-300ER", EmergencyLevel.NONE, 22.0, 472, 35.0, 152, False, 1.5, WakeCategory.HEAVY),
        Flight("VS3", "A350-1000", EmergencyLevel.NONE, 35.0, 335, 32.0, 153, False, 1.5, WakeCategory.HEAVY),
        Flight("SKW4451", "E175", EmergencyLevel.NONE, 14.0, 76, 15.0, 125, False, 2.5, WakeCategory.LIGHT),
        Flight("ASH5842", "CRJ-900", EmergencyLevel.NONE, 12.0, 76, 18.0, 135, False, 3.0, WakeCategory.LIGHT),
        Flight("N551GA", "Cirrus SR22", EmergencyLevel.NONE, 10.0, 4, 8.0, 120, False, 5.0, WakeCategory.LIGHT),
        Flight("N8721F", "Cessna 208", EmergencyLevel.NONE, 16.0, 9, 20.0, 140, False, 4.0, WakeCategory.LIGHT),
        Flight("FDX907", "B767-300F", EmergencyLevel.NONE, 28.0, 0, 28.0, 145, False, 1.5, WakeCategory.HEAVY),
        Flight("UPS29", "MD-11F", EmergencyLevel.NONE, 25.0, 0, 30.0, 148, False, 2.0, WakeCategory.HEAVY),
    ]
    weather = Weather(3.0, 35.0, 25.0, 1500.0, "rain", "deteriorating")
    timeline = [
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
    return {
        "task_id": "extra_hard",
        "task_name": "Total System Chaos",
        "flights": flights,
        "weather": weather,
        "max_steps": 80,
        "separation_steps": 2,
        "weather_timeline": timeline,
        "description": "20 aircraft in a total system failure scenario. Five MAYDAYs with fuel critical, four PAN-PANs with medical emergencies, VFR aircraft, and extreme weather volatility.",
    }


# Task registry
TASKS: Dict[str, Callable] = {
    "easy": build_easy,
    "medium": build_medium,
    "hard": build_hard,
    "extra_hard": build_extra_hard,
}


def list_tasks() -> List[Dict]:
    """List all available tasks."""
    return [
        {
            "id": task_id,
            "task_id": task_id,
            "task_name": builder()["task_name"],
            "description": builder()["description"],
            "num_flights": len(builder()["flights"]),
            "max_steps": builder()["max_steps"],
            "has_grader": True,
            "grader": {
                "id": task_id,
                "type": "deterministic",
                "endpoint": "/grade",
                "scoring_range": [0.0, 1.0],
            },
        }
        for task_id, builder in TASKS.items()
    ]
