"""Core ATC-Triage-v1 environment implementation.

Simulates an air traffic control scenario where an agent must
prioritize landing order for inbound flights under constraints
(fuel, weather, emergencies, wake-turbulence separation).
"""

from __future__ import annotations

import copy
import sys
import os

# Ensure project root is on path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    ATCAction,
    ATCObservation,
    ATCState,
    EmergencyLevel,
    Flight,
    FlightInfo,
    Weather,
    WeatherInfo,
    WakeCategory,
)
from server.tasks import Scenario, get_task_scenario
from server.graders import grade_episode

try:
    from openenv.core.env_server.types import Environment
except ImportError:
    from abc import ABC, abstractmethod
    from typing import Generic, TypeVar

    ActT = TypeVar("ActT")
    ObsT = TypeVar("ObsT")
    StateT = TypeVar("StateT")

    class Environment(ABC, Generic[ActT, ObsT, StateT]):
        """Minimal fallback base class when openenv-core is not installed."""

        def __init__(self, **kwargs):
            pass

        @abstractmethod
        def reset(self, seed=None, episode_id=None, **kwargs) -> ObsT: ...

        @abstractmethod
        def step(self, action: ActT, **kwargs) -> ObsT: ...

        @property
        @abstractmethod
        def state(self) -> StateT: ...


# ---------------------------------------------------------------------------
# Wake-turbulence separation matrix (steps between landings)
# Rows = leader category, Cols = follower category
# Index: LIGHT=1, MEDIUM=2, HEAVY=3, SUPER=4
# ---------------------------------------------------------------------------
_SEPARATION: dict[tuple[int, int], int] = {
    # (leader, follower) -> extra separation steps
    (4, 4): 3, (4, 3): 3, (4, 2): 4, (4, 1): 4,
    (3, 4): 2, (3, 3): 2, (3, 2): 3, (3, 1): 3,
    (2, 4): 1, (2, 3): 1, (2, 2): 2, (2, 1): 2,
    (1, 4): 1, (1, 3): 1, (1, 2): 1, (1, 1): 2,
}


class ATCEnvironment(Environment):
    """Air Traffic Control emergency triage environment."""

    SUPPORTS_CONCURRENT_SESSIONS = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._scenario: Scenario | None = None
        self._pending: list[Flight] = []
        self._landed: list[Flight] = []
        self._crashed: list[Flight] = []
        self._weather: Weather = Weather()
        self._time_step: int = 0
        self._step_count: int = 0
        self._max_time_steps: int = 50
        self._separation_steps: int = 2
        self._runway_free_at: int = 0
        self._last_landed_wake: int = WakeCategory.MEDIUM
        self._done: bool = False
        self._episode_reward: float = 0.0
        self._landing_log: list[dict] = []
        self._crash_log: list[dict] = []
        self._task_id: str = "easy"
        self._episode_id: str | None = None
        self._weather_timeline: list[dict] = []
        self._total_flights: int = 0

    # ------------------------------------------------------------------
    # OpenEnv API
    # ------------------------------------------------------------------

    def reset(self, seed: int | None = None, episode_id: str | None = None, **kwargs) -> ATCObservation:
        task_id = episode_id or "easy"
        # Support "task:easy" format as well
        if task_id.startswith("task:"):
            task_id = task_id[5:]

        self._scenario = get_task_scenario(task_id, seed)
        self._pending = [copy.deepcopy(f) for f in self._scenario.flights]
        self._landed = []
        self._crashed = []
        self._weather = copy.deepcopy(self._scenario.weather)
        self._time_step = 0
        self._step_count = 0
        self._max_time_steps = self._scenario.max_steps
        self._separation_steps = self._scenario.separation_steps
        self._runway_free_at = 0
        self._last_landed_wake = WakeCategory.MEDIUM
        self._done = False
        self._episode_reward = 0.0
        self._landing_log = []
        self._crash_log = []
        self._task_id = task_id
        self._episode_id = episode_id
        self._weather_timeline = self._scenario.weather_timeline
        self._total_flights = len(self._scenario.flights)

        return self._make_observation(step_reward=0.0)

    def step(self, action: ATCAction, **kwargs) -> ATCObservation:
        if self._done:
            return self._make_observation(step_reward=0.0)

        idx = action.flight_index
        self._step_count += 1

        # ---- Validate action ----
        if idx < 0 or idx >= len(self._pending):
            reward = self._apply_invalid_action()
            return self._make_observation(step_reward=reward)

        selected = self._pending[idx]

        # ---- Check weather minimums ----
        if not self._can_land(selected):
            reward = self._apply_weather_reject(selected)
            return self._make_observation(step_reward=reward)

        # ---- Execute landing sequence ----
        reward = self._execute_landing(idx, selected)
        return self._make_observation(step_reward=reward)

    @property
    def state(self) -> ATCState:
        return ATCState(
            episode_id=self._episode_id,
            step_count=self._step_count,
            task_id=self._task_id,
            time_step=self._time_step,
            landed_safely=len(self._landed),
            crashed=len(self._crashed),
            total_flights=self._total_flights,
            episode_reward=round(self._episode_reward, 4),
            landing_log=self._landing_log,
            crash_log=self._crash_log,
        )

    # ------------------------------------------------------------------
    # Episode grading
    # ------------------------------------------------------------------

    def grade(self) -> float:
        """Return final grade for the episode [0.0, 1.0]."""
        return grade_episode(
            task_id=self._task_id,
            landing_log=self._landing_log,
            crash_log=self._crash_log,
            total_flights=self._total_flights,
            steps_used=self._step_count,
            max_steps=self._max_time_steps,
        )

    # ------------------------------------------------------------------
    # Internal mechanics
    # ------------------------------------------------------------------

    def _execute_landing(self, idx: int, flight: Flight) -> float:
        """Clear a flight for landing. Returns step reward."""
        # Calculate wait + separation
        wait = max(0, self._runway_free_at - self._time_step)
        sep = _SEPARATION.get(
            (self._last_landed_wake, flight.wake_category.value),
            self._separation_steps,
        )
        advance = max(wait + sep, self._separation_steps)

        # Advance time — burn fuel for all pending flights
        self._advance_time(advance, exclude_callsign=flight.callsign)

        # Land the flight
        fuel_at_landing = flight.fuel_minutes  # fuel after others burned, but selected didn't burn extra
        self._pending.pop(idx)
        self._landed.append(flight)

        self._runway_free_at = self._time_step
        self._last_landed_wake = flight.wake_category.value

        # Record landing
        self._landing_log.append({
            "callsign": flight.callsign,
            "emergency": flight.emergency.name,
            "fuel_at_landing": round(fuel_at_landing, 1),
            "fuel_at_clear": round(flight.fuel_minutes, 1),
            "passengers": flight.passengers,
            "medical_onboard": flight.medical_onboard,
            "landed_at_step": self._step_count,
            "landed_at_time": self._time_step,
            "landing_position": len(self._landing_log),
        })

        # Calculate reward
        reward = self._reward_for_landing(flight, fuel_at_landing)

        # Check for crashes after time advance
        self._check_fuel_exhaustion()

        # Check episode end
        self._check_done()

        return reward

    def _advance_time(self, steps: int, exclude_callsign: str | None = None) -> None:
        """Advance simulation by N time-steps. Burns fuel, updates weather."""
        for _ in range(steps):
            self._time_step += 1
            # Burn fuel for all pending flights (except the one landing)
            for f in self._pending:
                if f.callsign != exclude_callsign:
                    f.fuel_minutes -= 1.0
            # Update weather
            self._update_weather()

    def _update_weather(self) -> None:
        """Apply weather timeline changes."""
        if not self._weather_timeline:
            return
        for entry in self._weather_timeline:
            if self._time_step == entry["step"]:
                if "visibility_nm" in entry:
                    self._weather.visibility_nm = entry["visibility_nm"]
                if "trend" in entry:
                    self._weather.trend = entry["trend"]
                if "precipitation" in entry:
                    self._weather.precipitation = entry["precipitation"]
                if "wind_knots" in entry:
                    self._weather.wind_knots = entry["wind_knots"]
                if "crosswind_knots" in entry:
                    self._weather.crosswind_knots = entry["crosswind_knots"]
                break

    def _check_fuel_exhaustion(self) -> None:
        """Check if any pending flight has run out of fuel (crash)."""
        still_pending = []
        for f in self._pending:
            if f.fuel_minutes <= 0:
                self._crashed.append(f)
                self._crash_log.append({
                    "callsign": f.callsign,
                    "emergency": f.emergency.name,
                    "passengers": f.passengers,
                    "crashed_at_time": self._time_step,
                    "crashed_at_step": self._step_count,
                })
                self._episode_reward -= 100.0
            else:
                still_pending.append(f)
        self._pending = still_pending

    def _check_done(self) -> None:
        """Determine if the episode has ended."""
        if not self._pending:
            self._done = True
            # Completion bonus
            if not self._crashed:
                bonus = 50.0
                self._episode_reward += bonus
        elif self._time_step >= self._max_time_steps:
            self._done = True
            # Remaining flights crash due to timeout
            for f in list(self._pending):
                self._crashed.append(f)
                self._crash_log.append({
                    "callsign": f.callsign,
                    "emergency": f.emergency.name,
                    "passengers": f.passengers,
                    "crashed_at_time": self._time_step,
                    "crashed_at_step": self._step_count,
                })
            self._pending = []
        elif self._step_count >= self._max_time_steps:
            self._done = True

    def _can_land(self, flight: Flight) -> bool:
        """Check if a flight can land in current weather."""
        return self._weather.visibility_nm >= flight.min_visibility_nm

    def _apply_invalid_action(self) -> float:
        """Handle an out-of-range flight_index."""
        penalty = -5.0
        self._episode_reward += penalty
        self._advance_time(1)
        self._check_fuel_exhaustion()
        self._check_done()
        return penalty

    def _apply_weather_reject(self, flight: Flight) -> float:
        """Handle selecting a flight that can't land in current weather."""
        penalty = -3.0
        self._episode_reward += penalty
        self._advance_time(1)
        self._check_fuel_exhaustion()
        self._check_done()
        return penalty

    def _reward_for_landing(self, flight: Flight, fuel_left: float) -> float:
        """Calculate reward for a successful landing."""
        base = 10.0

        # Emergency bonus
        if flight.emergency == EmergencyLevel.MAYDAY:
            base += 25.0
        elif flight.emergency == EmergencyLevel.PAN_PAN:
            base += 12.0

        # Medical bonus
        if flight.medical_onboard:
            base += 10.0

        # Passenger factor (more passengers = more important)
        pax_factor = 1.0 + (flight.passengers / 300.0)
        reward = base * pax_factor

        # Fuel risk factor — reward landing with tight fuel
        if fuel_left < 5:
            reward += 15.0  # saved from near-crash
        elif fuel_left < 10:
            reward += 5.0

        # Holding cost — small penalty for each remaining flight still waiting
        reward -= len(self._pending) * 0.5

        self._episode_reward += reward
        return round(reward, 2)

    # ------------------------------------------------------------------
    # Observation builder
    # ------------------------------------------------------------------

    def _make_observation(self, step_reward: float = 0.0) -> ATCObservation:
        flights = []
        for i, f in enumerate(self._pending):
            flights.append(
                FlightInfo(
                    index=i,
                    callsign=f.callsign,
                    aircraft_type=f.aircraft_type,
                    emergency=f.emergency.name,
                    fuel_minutes=round(f.fuel_minutes, 1),
                    passengers=f.passengers,
                    distance_nm=f.distance_nm,
                    medical_onboard=f.medical_onboard,
                    min_visibility_nm=f.min_visibility_nm,
                    wake_category=f.wake_category.name,
                    can_land_now=self._can_land(f),
                )
            )

        weather_info = WeatherInfo(
            visibility_nm=self._weather.visibility_nm,
            wind_knots=self._weather.wind_knots,
            crosswind_knots=self._weather.crosswind_knots,
            ceiling_feet=self._weather.ceiling_feet,
            precipitation=self._weather.precipitation,
            trend=self._weather.trend,
        )

        instructions = (
            "You are an air traffic controller managing emergency landings. "
            "Select the index (flight_index) of the next flight to clear for landing. "
            "Consider: (1) MAYDAY = immediate danger, land ASAP; "
            "(2) low fuel = will crash if not landed soon; "
            "(3) PAN_PAN/medical = urgent but not immediately life-threatening; "
            "(4) weather minimums = some aircraft need better visibility; "
            "(5) wake turbulence = heavy aircraft cause longer separation delays. "
            "Respond with: {\"flight_index\": <index>}"
        )

        return ATCObservation(
            flights=flights,
            weather=weather_info,
            runway_free_in_steps=max(0, self._runway_free_at - self._time_step),
            time_step=self._time_step,
            max_time_steps=self._max_time_steps,
            landed_safely=len(self._landed),
            crashed=len(self._crashed),
            total_flights=self._total_flights,
            task_id=self._task_id,
            instructions=instructions,
            done=self._done,
            reward=step_reward,
        )
