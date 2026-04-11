"""SUPERCELL — VABB Mumbai ATC Emergency Triage Environment.

Implements the canonical `openenv.core.env_server.interfaces.Environment`
contract so that `create_app()` from `openenv.core.env_server.http_server`
can wire `/reset`, `/step`, `/state`, `/schema`, `/health`, `/metadata`,
`/mcp`, and `/ws` for free.

The reward function is dense and partial-progress — it signals fuel
management, priority handling, medical urgency, and weather-aware
sequencing throughout the trajectory, not just at termination.
"""

from __future__ import annotations

from typing import Any, Optional

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from graders import grade_episode
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
from tasks import (
    CANONICAL_IDS,
    PUBLIC_TASK_ORDER,
    TASKS,
    canonical_task_id,
    list_tasks,
    resolve_task_id,
)


# =============================================================================
# Wake-turbulence separation (leader → follower) — ICAO Doc 4444
# =============================================================================

_WAKE_SEPARATION: dict[tuple[WakeCategory, WakeCategory], int] = {
    (WakeCategory.SUPER, WakeCategory.LIGHT): 4,
    (WakeCategory.SUPER, WakeCategory.MEDIUM): 4,
    (WakeCategory.SUPER, WakeCategory.HEAVY): 3,
    (WakeCategory.SUPER, WakeCategory.SUPER): 2,
    (WakeCategory.HEAVY, WakeCategory.LIGHT): 3,
    (WakeCategory.HEAVY, WakeCategory.MEDIUM): 3,
    (WakeCategory.HEAVY, WakeCategory.HEAVY): 2,
    (WakeCategory.HEAVY, WakeCategory.SUPER): 2,
    (WakeCategory.MEDIUM, WakeCategory.LIGHT): 3,
    (WakeCategory.MEDIUM, WakeCategory.MEDIUM): 2,
    (WakeCategory.MEDIUM, WakeCategory.HEAVY): 2,
    (WakeCategory.MEDIUM, WakeCategory.SUPER): 2,
    (WakeCategory.LIGHT, WakeCategory.LIGHT): 2,
    (WakeCategory.LIGHT, WakeCategory.MEDIUM): 2,
    (WakeCategory.LIGHT, WakeCategory.HEAVY): 2,
    (WakeCategory.LIGHT, WakeCategory.SUPER): 2,
}


INSTRUCTIONS = (
    "You are the Tower Controller at VABB (Chhatrapati Shivaji Intl, "
    "Mumbai) during monsoon operations. Inbound flights are on approach "
    "via STAR fixes PARAR, GUDOM, NOMUS, LEKIT. Your job is to sequence "
    "landings on a single active runway under fuel, weather, and "
    "emergency constraints.\n\n"
    "RULES:\n"
    "  1. Landing takes 1 time step.\n"
    "  2. After a landing, the runway is blocked for wake-separation steps.\n"
    "  3. A flight cannot land if airport visibility < its min_visibility_nm.\n"
    "  4. Every step, every airborne flight burns 1 min of fuel. Fuel<=0 crashes.\n\n"
    "PRIORITY (soft — agent decides):\n"
    "  MAYDAY > PAN-PAN > medical_onboard > low fuel > passenger count.\n\n"
    "ACTION: return {\"flight_index\": i} where i is the 0-based "
    "position into observation.flights."
)


def _build_task_dict(internal_id: str) -> dict[str, Any]:
    """Build a hackathon-style task dict (list-of-dicts form) for an id."""
    data = TASKS[internal_id]()
    canonical = canonical_task_id(internal_id)
    difficulty_map = {
        "easy": "easy",
        "medium": "medium",
        "hard": "hard",
        "extra_hard": "hard",
    }
    return {
        "id": canonical,
        "internal_id": internal_id,
        "name": data["task_name"],
        "difficulty": difficulty_map.get(internal_id, "medium"),
        "description": data["description"],
        "max_steps": data["max_steps"],
        "num_flights": len(data["flights"]),
        "reward_range": [0.01, 0.99],
        "grader": {
            "id": canonical,
            "type": "deterministic",
            "endpoint": "/grader",
            "reward_range": [0.01, 0.99],
        },
    }


# Module-level list that the hackathon validator can introspect via
#     from environment import ATCEnvironment; ATCEnvironment.TASKS
# It's a list of dicts (matching the reference's StockExchangeEnv.TASKS)
# rather than the dict-of-builders used internally.
_ATC_TASKS_LIST: list[dict[str, Any]] = [
    _build_task_dict(internal_id)
    for internal_id in ("easy", "medium", "hard", "extra_hard")
]


class ATCEnvironment(Environment[ATCAction, ATCObservation, ATCState]):
    """VABB Mumbai ATC emergency triage environment (OpenEnv-compliant)."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = False

    # Class attribute exposing tasks as a list-of-dicts — mirrors the
    # passing reference submission's `StockExchangeEnv.TASKS` pattern.
    # Each entry has id (canonical kebab-case), name, difficulty,
    # description, reward_range, and a nested grader descriptor.
    TASKS: list[dict[str, Any]] = _ATC_TASKS_LIST

    def __init__(self) -> None:
        super().__init__()
        self._state: ATCState = ATCState()
        self._last_landed_wake: Optional[WakeCategory] = None

    # ------------------------------------------------------------------
    # Canonical Environment contract
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> ATCObservation:
        """Load a task scenario and return the initial observation.

        `episode_id` accepts either the internal id (easy/medium/hard/
        extra_hard) or the canonical kebab-case id (task-001-winter-haze,
        task-002-pre-monsoon-squall, task-003-mumbai-monsoon-surge,
        task-004-total-system-chaos).
        """
        task_id = resolve_task_id(episode_id or "easy")

        data = TASKS[task_id]()
        self._state = ATCState(
            episode_id=task_id,
            step_count=0,
            task_id=task_id,
            task_name=data["task_name"],
            time_step=0,
            landed_safely=0,
            crashed=0,
            total_flights=len(data["flights"]),
            flights=list(data["flights"]),
            weather=data["weather"],
            runway_free_in_steps=0,
            landing_log=[],
            crash_log=[],
            max_steps=data["max_steps"],
            separation_steps=data["separation_steps"],
            weather_timeline=list(data.get("weather_timeline", [])),
            episode_reward=0.0,
        )
        self._last_landed_wake = None
        self._apply_weather_timeline(step=0)
        return self._build_observation(reward=0.0, done=False)

    def step(
        self,
        action: ATCAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> ATCObservation:
        """Execute one ATC decision and advance the simulation by one step."""
        # If episode already finished, return a terminal observation.
        if (
            len(self._state.flights) == 0
            or self._state.time_step >= self._state.max_steps
        ):
            return self._build_observation(reward=0.0, done=True)

        idx = action.flight_index

        # Invalid index — penalize but still advance time
        if idx < 0 or idx >= len(self._state.flights):
            reward = -5.0
            reward -= 0.5 * len(self._state.flights)
            crashes = self._advance_time()
            if crashes > 0:
                reward -= 100.0 * crashes
            self._state.episode_reward += reward
            self._state.step_count += 1
            done = (
                len(self._state.flights) == 0
                or self._state.time_step >= self._state.max_steps
            )
            return self._build_observation(reward=reward, done=done)

        flight = self._state.flights[idx]
        reward = 0.0

        can_land, reason = self._can_land(flight)
        if can_land:
            reward += self._landing_reward(flight)
            self._state.landed_safely += 1
            self._state.runway_free_in_steps = self._separation_for(flight.wake_category)
            self._last_landed_wake = flight.wake_category
            self._state.landing_log.append({
                "step": self._state.time_step,
                "callsign": flight.callsign,
                "emergency": flight.emergency.name,
                "medical_onboard": flight.medical_onboard,
                "fuel_on_landing": flight.fuel_minutes,
                "passengers": flight.passengers,
                "wake_category": flight.wake_category.name,
                "landed_safely": True,
            })
            self._state.flights.pop(idx)
        else:
            if reason == "weather":
                reward -= 3.0
            else:
                reward -= 1.0

        # Dense holding cost — time pressure scales with queue length
        reward -= 0.5 * len(self._state.flights)

        crashes = self._advance_time()
        if crashes > 0:
            reward -= 100.0 * crashes

        done = (
            len(self._state.flights) == 0
            or self._state.time_step >= self._state.max_steps
        )
        if done and len(self._state.flights) == 0 and self._state.crashed == 0:
            reward += 50.0  # Perfect episode bonus

        self._state.episode_reward += reward
        self._state.step_count += 1
        return self._build_observation(reward=reward, done=done)

    @property
    def state(self) -> ATCState:
        """Current internal state (exposed via /state)."""
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="supercell",
            description=(
                "SUPERCELL — Monsoon Mumbai ATC Emergency Triage. "
                "An OpenEnv-compliant environment set at VABB (Chhatrapati "
                "Shivaji Intl, Mumbai) where the agent plays Tower Controller "
                "during monsoon operations, sequencing landings under fuel, "
                "weather, wake-turbulence, and emergency constraints."
            ),
            version="1.0.0",
            author="SUPERCELL Team",
        )

    def close(self) -> None:
        """No-op — environment state persists across HTTP calls in simulation mode."""
        return None

    # ------------------------------------------------------------------
    # Custom (not part of OpenEnv base contract)
    # ------------------------------------------------------------------

    def grade(self) -> float:
        """Deterministic [0, 1] score for the current episode."""
        return grade_episode(
            self._state.landing_log,
            self._state.crash_log,
            self._state.total_flights,
            self._state.time_step,
            self._state.max_steps,
            self._state.task_id,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _can_land(self, flight: Flight) -> tuple[bool, str]:
        if self._state.runway_free_in_steps > 0:
            return (False, "runway")
        if self._state.weather.visibility_nm < flight.min_visibility_nm:
            return (False, "weather")
        return (True, "ok")

    def _separation_for(self, follower_wake: WakeCategory) -> int:
        if self._last_landed_wake is None:
            return self._state.separation_steps
        leader = self._last_landed_wake
        return _WAKE_SEPARATION.get((leader, follower_wake), self._state.separation_steps)

    def _landing_reward(self, flight: Flight) -> float:
        base = 10.0
        if flight.emergency == EmergencyLevel.MAYDAY:
            base += 25.0
        elif flight.emergency == EmergencyLevel.PAN_PAN:
            base += 12.0
        if flight.medical_onboard:
            base += 10.0
        if flight.fuel_minutes < 5:
            base += 15.0
        elif flight.fuel_minutes < 10:
            base += 5.0
        base += min(10.0, flight.passengers / 50.0)
        return base

    def _advance_time(self) -> int:
        self._state.time_step += 1
        if self._state.runway_free_in_steps > 0:
            self._state.runway_free_in_steps -= 1
        self._apply_weather_timeline(step=self._state.time_step)

        crashed_indices: list[int] = []
        for i, flight in enumerate(self._state.flights):
            flight.fuel_minutes -= 1.0
            if flight.fuel_minutes <= 0:
                crashed_indices.append(i)
                self._state.crash_log.append({
                    "step": self._state.time_step,
                    "callsign": flight.callsign,
                    "reason": "fuel_exhaustion",
                    "emergency": flight.emergency.name,
                    "medical_onboard": flight.medical_onboard,
                    "passengers": flight.passengers,
                })
        for i in reversed(crashed_indices):
            self._state.flights.pop(i)
            self._state.crashed += 1
        return len(crashed_indices)

    def _apply_weather_timeline(self, step: int) -> None:
        for entry in self._state.weather_timeline:
            if entry.get("step") == step:
                if "visibility_nm" in entry:
                    self._state.weather.visibility_nm = entry["visibility_nm"]
                if "trend" in entry:
                    self._state.weather.trend = entry["trend"]
                if "precipitation" in entry:
                    self._state.weather.precipitation = entry["precipitation"]
                break

    def _build_observation(self, reward: float, done: bool) -> ATCObservation:
        flights_info = [
            FlightInfo(
                index=i,
                callsign=f.callsign,
                aircraft_type=f.aircraft_type,
                emergency=f.emergency.name,
                fuel_minutes=f.fuel_minutes,
                passengers=f.passengers,
                distance_nm=f.distance_nm,
                medical_onboard=f.medical_onboard,
                min_visibility_nm=f.min_visibility_nm,
                wake_category=f.wake_category.name,
                can_land_now=self._can_land(f)[0],
                bearing_deg=f.bearing_deg,
                approach_fix=f.approach_fix,
            )
            for i, f in enumerate(self._state.flights)
        ]
        w = self._state.weather
        weather_info = WeatherInfo(
            visibility_nm=w.visibility_nm,
            wind_knots=w.wind_knots,
            crosswind_knots=w.crosswind_knots,
            ceiling_feet=w.ceiling_feet,
            precipitation=w.precipitation,
            trend=w.trend,
        )
        return ATCObservation(
            done=done,
            reward=reward,
            flights=flights_info,
            weather=weather_info,
            runway_free_in_steps=self._state.runway_free_in_steps,
            time_step=self._state.time_step,
            max_time_steps=self._state.max_steps,
            landed_safely=self._state.landed_safely,
            crashed=self._state.crashed,
            total_flights=self._state.total_flights,
            task_id=canonical_task_id(self._state.task_id),
            task_name=self._state.task_name,
            episode_reward=self._state.episode_reward,
            instructions=INSTRUCTIONS,
        )
