"""Simplified ATC environment for hackathon."""

from typing import Optional, List, Dict, Any
from dataclasses import replace

from models import ATCState, ATCObservation, ATCAction, Flight, Weather, FlightInfo, WeatherInfo, EmergencyLevel
from tasks import TASKS
from graders import grade_episode


class ATCEnvironment:
    """ATC Triage Environment - simplified for hackathon."""
    
    INSTRUCTIONS = """
You are an Air Traffic Controller managing emergency landings.

TASK: Prioritize landing order for inbound flights under fuel, weather, and emergency constraints.

RULES:
1. Landing takes 1 time step per flight
2. After landing, runway is blocked for separation steps (wake turbulence)
3. Flights CANNOT land if weather visibility < aircraft minimum visibility
4. Flights with fuel < 0 CRASH

PRIORITIES (highest first):
1. MAYDAY (life-threatening emergency)
2. PAN-PAN (urgent but stable)  
3. Medical onboard
4. Low fuel
5. Passenger count

STRATEGY:
- Land MAYDAYs immediately if weather permits
- Check weather vs aircraft minimums before landing
- Manage runway separation (heavy aircraft block longer)
- Balance fuel urgency with weather windows

ACTION: Provide flight_index (0-based position in flights list) to land next.
"""
    
    def __init__(self):
        self.state: ATCState = ATCState()
    
    def reset(self, seed: Optional[int] = None, episode_id: Optional[str] = None) -> ATCObservation:
        """Reset environment with selected task."""
        task_id = episode_id or "easy"
        if task_id not in TASKS:
            task_id = "easy"
        
        task_data = TASKS[task_id]()
        
        self.state = ATCState(
            task_id=task_id,
            task_name=task_data["task_name"],
            time_step=0,
            landed_safely=0,
            crashed=0,
            total_flights=len(task_data["flights"]),
            flights=task_data["flights"][:],
            weather=task_data["weather"],
            runway_free_in_steps=0,
            landing_log=[],
            crash_log=[],
            max_steps=task_data["max_steps"],
            separation_steps=task_data["separation_steps"],
            weather_timeline=task_data.get("weather_timeline", []),
            episode_reward=0.0,
        )
        
        return self._get_observation()
    
    def step(self, action: ATCAction) -> ATCObservation:
        """Execute one step: land a flight."""
        if not self.state.flights:
            return self._get_observation()
        
        idx = action.flight_index
        if idx < 0 or idx >= len(self.state.flights):
            idx = 0
        
        flight = self.state.flights[idx]
        
        # Check if can land (weather, runway)
        can_land = self._can_land(flight)
        
        if can_land:
            # Land the flight
            self.state.landed_safely += 1
            self.state.runway_free_in_steps = self.state.separation_steps
            
            # Log landing
            self.state.landing_log.append({
                "step": self.state.time_step,
                "callsign": flight.callsign,
                "emergency": flight.emergency.name,
                "medical_onboard": flight.medical_onboard,
                "fuel_on_landing": flight.fuel_minutes,
                "landed_safely": True,
            })
            
            # Remove flight
            self.state.flights.pop(idx)
            reward = 1.0
        else:
            # Cannot land - time passes, fuel burns
            reward = -0.1
        
        # Advance time
        self._advance_time()
        
        # Update episode reward
        self.state.episode_reward += reward
        
        # Check done
        done = len(self.state.flights) == 0 or self.state.time_step >= self.state.max_steps
        
        obs = self._get_observation()
        obs.done = done
        obs.reward = reward
        return obs
    
    def _can_land(self, flight: Flight) -> bool:
        """Check if flight can land."""
        # Runway must be free
        if self.state.runway_free_in_steps > 0:
            return False
        
        # Weather must be above minimum
        if self.state.weather.visibility_nm < flight.min_visibility_nm:
            return False
        
        return True
    
    def _advance_time(self):
        """Advance time step, update fuel, weather, check crashes."""
        self.state.time_step += 1
        
        # Decrement runway timer
        if self.state.runway_free_in_steps > 0:
            self.state.runway_free_in_steps -= 1
        
        # Update weather from timeline
        for entry in self.state.weather_timeline:
            if entry["step"] == self.state.time_step:
                self.state.weather.visibility_nm = entry["visibility_nm"]
                self.state.weather.trend = entry["trend"]
                self.state.weather.precipitation = entry["precipitation"]
                break
        
        # Burn fuel, check crashes
        crashed = []
        for i, flight in enumerate(self.state.flights):
            flight.fuel_minutes -= 1.0
            if flight.fuel_minutes <= 0:
                crashed.append(i)
                self.state.crash_log.append({
                    "step": self.state.time_step,
                    "callsign": flight.callsign,
                    "reason": "out_of_fuel",
                    "emergency": flight.emergency.name,
                })
        
        # Remove crashed flights (reverse order)
        for i in reversed(crashed):
            self.state.flights.pop(i)
            self.state.crashed += 1
    
    def _get_observation(self) -> ATCObservation:
        """Build observation from current state."""
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
                can_land_now=self._can_land(f),
            )
            for i, f in enumerate(self.state.flights)
        ]
        
        w = self.state.weather
        weather_info = WeatherInfo(
            visibility_nm=w.visibility_nm,
            wind_knots=w.wind_knots,
            crosswind_knots=w.crosswind_knots,
            ceiling_feet=w.ceiling_feet,
            precipitation=w.precipitation,
            trend=w.trend,
        )
        
        return ATCObservation(
            flights=flights_info,
            weather=weather_info,
            runway_free_in_steps=self.state.runway_free_in_steps,
            time_step=self.state.time_step,
            max_time_steps=self.state.max_steps,
            landed_safely=self.state.landed_safely,
            crashed=self.state.crashed,
            total_flights=self.state.total_flights,
            task_id=self.state.task_id,
            task_name=self.state.task_name,
            done=len(self.state.flights) == 0 or self.state.time_step >= self.state.max_steps,
            reward=0.0,
            episode_reward=self.state.episode_reward,
            instructions=self.INSTRUCTIONS,
        )
    
    def grade(self) -> float:
        """Grade the current episode."""
        return grade_episode(
            self.state.landing_log,
            self.state.crash_log,
            self.state.total_flights,
            self.state.time_step,
            self.state.max_steps,
            self.state.task_id,
        )
