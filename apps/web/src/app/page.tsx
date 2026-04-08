"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type {
  FlightInfo,
  WeatherInfo,
  Observation,
  GradeResult,
  LogEntry,
  TaskId,
} from "@/lib/types";
import { Header } from "@/components/header";
import { RadarScope } from "@/components/radar-scope";
import { FlightStrips } from "@/components/flight-strips";
import { WeatherPanel } from "@/components/weather-panel";
import { ControlPanel } from "@/components/control-panel";
import { EventLog } from "@/components/event-log";
import { ScoreBreakdown } from "@/components/score-breakdown";

export default function ATCDashboard() {
  // --- State ---
  const [connected, setConnected] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<TaskId>("easy");
  const [flights, setFlights] = useState<FlightInfo[]>([]);
  const [weather, setWeather] = useState<WeatherInfo | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [timeStep, setTimeStep] = useState(0);
  const [maxTimeSteps, setMaxTimeSteps] = useState(0);
  const [landedSafely, setLandedSafely] = useState(0);
  const [crashed, setCrashed] = useState(0);
  const [totalFlights, setTotalFlights] = useState(0);
  const [reward, setReward] = useState<number | null>(null);
  const [cumulativeReward, setCumulativeReward] = useState(0);
  const [score, setScore] = useState<GradeResult | null>(null);
  const [done, setDone] = useState(false);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [aiPlaying, setAiPlaying] = useState(false);
  const [aiSpeed, setAiSpeed] = useState(1000);

  const aiRef = useRef(false);
  const prevFlightsRef = useRef<FlightInfo[]>([]);

  // --- Helpers ---
  const addLog = useCallback(
    (type: LogEntry["type"], message: string, detail?: string) => {
      setLog((prev) =>
        [{ time: 0, type, message, detail }, ...prev].slice(0, 50)
      );
    },
    []
  );

  const applyObs = useCallback(
    (obs: Observation, prevFlights: FlightInfo[]) => {
      // Detect landings and crashes from flight list changes
      const currentCallsigns = new Set(obs.flights.map((f) => f.callsign));
      for (const pf of prevFlights) {
        if (!currentCallsigns.has(pf.callsign)) {
          if (obs.crashed > prevFlightsRef.current.filter(() => false).length) {
            // Flight disappeared — could be landed or crashed
          }
        }
      }

      setFlights(obs.flights);
      setWeather(obs.weather);
      setTimeStep(obs.time_step);
      setMaxTimeSteps(obs.max_time_steps);
      setLandedSafely(obs.landed_safely);
      setCrashed(obs.crashed);
      setTotalFlights(obs.total_flights);
      setTaskId(obs.task_id as TaskId);
      setDone(obs.done);
      prevFlightsRef.current = obs.flights;

      // Auto-select first flight if nothing selected
      if (obs.flights.length > 0) {
        setSelectedIndex((prev) => {
          if (prev === null) return obs.flights[0].index;
          const stillExists = obs.flights.some((f) => f.index === prev);
          return stillExists ? prev : obs.flights[0].index;
        });
      } else {
        setSelectedIndex(null);
      }
    },
    []
  );

  // --- Actions ---
  const handleReset = useCallback(
    async (tid: TaskId) => {
      setLoading(true);
      setScore(null);
      setReward(null);
      setCumulativeReward(0);
      setSelectedIndex(null);
      setLog([]);
      setDone(false);
      setAiPlaying(false);
      aiRef.current = false;

      try {
        const resp = await api.reset(tid);
        const obs = resp.observation as unknown as Observation;
        applyObs(obs, []);
        setInitialized(true);
        setConnected(true);
        addLog(
          "system",
          `Scenario loaded: ${tid.toUpperCase()}`,
          `${obs.flights.length} flights, ${obs.max_time_steps} max steps`
        );
      } catch (e) {
        addLog("system", `Connection error: ${e}`);
        setConnected(false);
      } finally {
        setLoading(false);
      }
    },
    [applyObs, addLog]
  );

  const handleStep = useCallback(async () => {
    if (selectedIndex === null || done || loading) return;
    setLoading(true);

    const selectedFlight = flights.find((f) => f.index === selectedIndex);

    try {
      const resp = await api.step(selectedIndex);
      const obs = resp.observation as unknown as Observation;
      const rwd = resp.reward ?? 0;

      setReward(rwd);
      setCumulativeReward((prev) => prev + rwd);

      // Log the action
      const callsign = selectedFlight?.callsign ?? `#${selectedIndex}`;
      if (rwd >= 0) {
        addLog(
          "land",
          `${callsign} cleared for landing`,
          `reward: ${rwd > 0 ? "+" : ""}${rwd.toFixed(1)}${selectedFlight?.emergency === "MAYDAY" ? " MAYDAY" : selectedFlight?.emergency === "PAN_PAN" ? " PAN-PAN" : ""}${selectedFlight?.medical_onboard ? " MED" : ""}`
        );
      } else {
        addLog(
          "action",
          `${callsign} action result`,
          `reward: ${rwd.toFixed(1)}`
        );
      }

      // Check for crashes (compare counts)
      if (obs.crashed > crashed) {
        const newCrashes = obs.crashed - crashed;
        addLog(
          "crash",
          `${newCrashes} flight${newCrashes > 1 ? "s" : ""} crashed — fuel exhaustion`
        );
      }

      applyObs(obs, flights);

      // Check weather changes
      if (
        weather &&
        obs.weather.visibility_nm !== weather.visibility_nm
      ) {
        addLog(
          "weather",
          `Visibility changed: ${weather.visibility_nm}nm → ${obs.weather.visibility_nm}nm`,
          obs.weather.trend
        );
      }

      // Grade if done
      if (resp.done || obs.done) {
        setAiPlaying(false);
        aiRef.current = false;
        try {
          const grade = await api.grade();
          setScore(grade);
          addLog(
            "system",
            `Mission complete — Score: ${(grade.score * 100).toFixed(1)}%`,
            `${grade.landing_log.length} landed, ${grade.crash_log.length} crashed, ${grade.steps_used} steps`
          );
        } catch {
          addLog("system", "Failed to retrieve grade");
        }
      }
    } catch (e) {
      addLog("system", `Error: ${e}`);
    } finally {
      setLoading(false);
    }
  }, [
    selectedIndex,
    done,
    loading,
    flights,
    crashed,
    weather,
    applyObs,
    addLog,
  ]);

  // --- AI Auto-Play ---
  const handleToggleAI = useCallback(() => {
    setAiPlaying((prev) => {
      const next = !prev;
      aiRef.current = next;
      if (next) {
        addLog("ai", "AI Agent activated", "Auto-selecting optimal flights");
      } else {
        addLog("ai", "AI Agent paused");
      }
      return next;
    });
  }, [addLog]);

  useEffect(() => {
    if (!aiPlaying || done || loading) return;

    const timer = setTimeout(() => {
      if (aiRef.current && !done) {
        // Simple AI: prioritize MAYDAY > PAN_PAN > lowest fuel > first available
        const sorted = [...flights].sort((a, b) => {
          const emergencyOrder = { MAYDAY: 0, PAN_PAN: 1, NONE: 2 };
          const ea = emergencyOrder[a.emergency] ?? 2;
          const eb = emergencyOrder[b.emergency] ?? 2;
          if (ea !== eb) return ea - eb;
          // Among same emergency, pick lowest fuel first
          if (a.fuel_minutes !== b.fuel_minutes)
            return a.fuel_minutes - b.fuel_minutes;
          // Prefer those that can land now
          if (a.can_land_now !== b.can_land_now) return a.can_land_now ? -1 : 1;
          return 0;
        });

        const best = sorted.find((f) => f.can_land_now) ?? sorted[0];
        if (best) {
          setSelectedIndex(best.index);
          // Trigger step after brief delay for visual feedback
          setTimeout(() => {
            if (aiRef.current) {
              handleStep();
            }
          }, 200);
        }
      }
    }, aiSpeed);

    return () => clearTimeout(timer);
  }, [aiPlaying, done, loading, flights, aiSpeed, handleStep]);

  // --- Connect on mount ---
  useEffect(() => {
    api
      .health()
      .then(() => {
        setConnected(true);
        handleReset("easy");
      })
      .catch(() => setConnected(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Keyboard shortcuts ---
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement) return;

      switch (e.key) {
        case " ":
        case "Enter":
          e.preventDefault();
          handleStep();
          break;
        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((prev) => {
            if (!flights.length) return null;
            const idx = flights.findIndex((f) => f.index === prev);
            const next = idx <= 0 ? flights.length - 1 : idx - 1;
            return flights[next].index;
          });
          break;
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((prev) => {
            if (!flights.length) return null;
            const idx = flights.findIndex((f) => f.index === prev);
            const next = idx >= flights.length - 1 ? 0 : idx + 1;
            return flights[next].index;
          });
          break;
        case "a":
          if (!e.metaKey && !e.ctrlKey) handleToggleAI();
          break;
        case "1":
          handleReset("easy");
          break;
        case "2":
          handleReset("medium");
          break;
        case "3":
          handleReset("hard");
          break;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleStep, handleToggleAI, handleReset, flights]);

  // Update log timestamps
  useEffect(() => {
    setLog((prev) =>
      prev.map((entry, i) =>
        i === 0 ? { ...entry, time: timeStep } : entry
      )
    );
  }, [timeStep]);

  // --- Render ---
  if (!connected) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center space-y-6 max-w-md">
          <div className="w-16 h-16 mx-auto rounded-full border-2 border-[var(--color-radar-red)] flex items-center justify-center">
            <div className="w-3 h-3 rounded-full bg-[var(--color-radar-red)] pulse-mayday" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[var(--color-radar-red)] mb-2">
              NO SERVER CONNECTION
            </h1>
            <p className="text-[var(--color-radar-text)] text-sm">
              Start the environment server to begin:
            </p>
            <code className="block mt-3 bg-[var(--color-radar-panel)] border border-[var(--color-radar-border)] p-3 rounded text-[var(--color-radar-green)] text-sm">
              uv run python -m server.app
            </code>
          </div>
          <button
            onClick={() => handleReset("easy")}
            className="atc-btn atc-btn-primary px-6 py-2"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* CRT Overlay */}
      <div className="crt-overlay" />

      {/* Header */}
      <Header
        connected={connected}
        taskId={taskId}
        timeStep={timeStep}
        maxTimeSteps={maxTimeSteps}
        landedSafely={landedSafely}
        crashed={crashed}
        totalFlights={totalFlights}
        done={done}
        aiPlaying={aiPlaying}
      />

      {/* Main Grid */}
      <div className="flex-1 grid grid-cols-12 gap-2 p-2 min-h-0">
        {/* Left Column: Radar + Weather */}
        <div className="col-span-4 flex flex-col gap-2 min-h-0">
          <div className="flex-1 min-h-0">
            <RadarScope
              flights={flights}
              selectedIndex={selectedIndex}
              onSelect={setSelectedIndex}
              className="h-full"
            />
          </div>
          <WeatherPanel weather={weather} />
        </div>

        {/* Center Column: Flight Strips + Event Log */}
        <div className="col-span-5 flex flex-col gap-2 min-h-0">
          <div className="flex-[3] min-h-0">
            <FlightStrips
              flights={flights}
              selectedIndex={selectedIndex}
              onSelect={setSelectedIndex}
              onClear={handleStep}
              done={done}
              loading={loading}
            />
          </div>
          <div className="flex-[1] min-h-0">
            {score ? (
              <ScoreBreakdown score={score} taskId={taskId} />
            ) : (
              <EventLog log={log} />
            )}
          </div>
        </div>

        {/* Right Column: Controls */}
        <div className="col-span-3 min-h-0">
          <ControlPanel
            taskId={taskId}
            timeStep={timeStep}
            maxTimeSteps={maxTimeSteps}
            landedSafely={landedSafely}
            crashed={crashed}
            totalFlights={totalFlights}
            reward={reward}
            cumulativeReward={cumulativeReward}
            done={done}
            loading={loading}
            initialized={initialized}
            aiPlaying={aiPlaying}
            aiSpeed={aiSpeed}
            onReset={handleReset}
            onStep={handleStep}
            onToggleAI={handleToggleAI}
            onSetAISpeed={setAiSpeed}
          />
        </div>
      </div>

      {/* Keyboard hints */}
      <div className="flex items-center justify-center gap-4 py-1 border-t border-[var(--color-radar-border)] bg-[var(--color-radar-panel)]">
        <span className="text-[8px] text-[var(--color-radar-text)] uppercase tracking-widest">
          <kbd className="px-1 py-0.5 bg-[var(--color-radar-bg)] rounded text-[var(--color-radar-text-secondary)] border border-[var(--color-radar-border)]">
            Space
          </kbd>{" "}
          Clear
        </span>
        <span className="text-[8px] text-[var(--color-radar-text)] uppercase tracking-widest">
          <kbd className="px-1 py-0.5 bg-[var(--color-radar-bg)] rounded text-[var(--color-radar-text-secondary)] border border-[var(--color-radar-border)]">
            ↑↓
          </kbd>{" "}
          Select
        </span>
        <span className="text-[8px] text-[var(--color-radar-text)] uppercase tracking-widest">
          <kbd className="px-1 py-0.5 bg-[var(--color-radar-bg)] rounded text-[var(--color-radar-text-secondary)] border border-[var(--color-radar-border)]">
            A
          </kbd>{" "}
          AI Toggle
        </span>
        <span className="text-[8px] text-[var(--color-radar-text)] uppercase tracking-widest">
          <kbd className="px-1 py-0.5 bg-[var(--color-radar-bg)] rounded text-[var(--color-radar-text-secondary)] border border-[var(--color-radar-border)]">
            1-3
          </kbd>{" "}
          Task
        </span>
      </div>
    </div>
  );
}
