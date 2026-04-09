"use client";

import clsx from "clsx";
import {
  Play,
  Pause,
  RotateCcw,
  Zap,
  Brain,
  ChevronRight,
  Timer,
} from "lucide-react";
import type { TaskId } from "@/lib/types";

interface ControlPanelProps {
  taskId: TaskId;
  timeStep: number;
  maxTimeSteps: number;
  landedSafely: number;
  crashed: number;
  totalFlights: number;
  reward: number | null;
  cumulativeReward: number;
  done: boolean;
  loading: boolean;
  initialized: boolean;
  aiPlaying: boolean;
  aiSpeed: number;
  onReset: (taskId: TaskId) => void;
  onStep: () => void;
  onToggleAI: () => void;
  onSetAISpeed: (speed: number) => void;
}

const TASKS: { id: TaskId; label: string; flights: string; color: string }[] = [
  { id: "easy", label: "EASY", flights: "4 FLT", color: "var(--color-radar-green)" },
  { id: "medium", label: "MED", flights: "7 FLT", color: "var(--color-radar-amber)" },
  { id: "hard", label: "HARD", flights: "12 FLT", color: "var(--color-radar-red)" },
  { id: "extra_hard", label: "MAX", flights: "20 FLT", color: "var(--color-radar-cyan)" },
];

const SPEEDS = [
  { value: 2000, label: "0.5x" },
  { value: 1000, label: "1x" },
  { value: 500, label: "2x" },
  { value: 200, label: "5x" },
];

export function ControlPanel({
  taskId,
  timeStep,
  maxTimeSteps,
  landedSafely,
  crashed,
  totalFlights,
  reward,
  cumulativeReward,
  done,
  loading,
  initialized,
  aiPlaying,
  aiSpeed,
  onReset,
  onStep,
  onToggleAI,
  onSetAISpeed,
}: ControlPanelProps) {
  const progress = maxTimeSteps > 0 ? (timeStep / maxTimeSteps) * 100 : 0;
  const progressColor =
    progress > 75
      ? "var(--color-radar-red)"
      : progress > 50
        ? "var(--color-radar-amber)"
        : "var(--color-radar-green)";

  return (
    <div className="atc-panel flex flex-col h-full">
      <div className="atc-panel-header">
        <div className="indicator" />
        CONTROL TOWER
      </div>

      <div className="p-3 flex-1 flex flex-col gap-3">
        {/* Task Selector */}
        <div>
          <div className="text-[9px] text-[var(--color-radar-text)] uppercase tracking-widest mb-1.5">
            Scenario
          </div>
          <div className="flex gap-1.5">
            {TASKS.map((t) => (
              <button
                key={t.id}
                onClick={() => onReset(t.id)}
                disabled={loading}
                className={clsx(
                  "atc-btn flex-1 flex flex-col items-center gap-0.5 py-2",
                  taskId === t.id && "!border-[color:var(--active)]"
                )}
                style={
                  taskId === t.id
                    ? ({
                        "--active": t.color,
                        background: `color-mix(in srgb, ${t.color} 12%, transparent)`,
                        borderColor: `color-mix(in srgb, ${t.color} 40%, transparent)`,
                        color: t.color,
                      } as React.CSSProperties)
                    : undefined
                }
              >
                <span className="text-[10px] font-bold">{t.label}</span>
                <span className="text-[8px] opacity-60">{t.flights}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Time Progress */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1 text-[9px] text-[var(--color-radar-text)] uppercase tracking-widest">
              <Timer size={10} />
              Time
            </div>
            <span
              className="text-[10px] font-bold font-mono"
              style={{ color: progressColor }}
            >
              {timeStep}/{maxTimeSteps}
            </span>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill"
              style={{
                width: `${progress}%`,
                background: progressColor,
              }}
            />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-1.5">
          <StatBox label="Landed" value={landedSafely} color="var(--color-radar-green)" />
          <StatBox
            label="Crashed"
            value={crashed}
            color={crashed > 0 ? "var(--color-radar-red)" : "var(--color-radar-text)"}
            glow={crashed > 0}
          />
          <StatBox label="Total" value={totalFlights} color="var(--color-radar-cyan)" />
        </div>

        {/* Reward Display */}
        {reward !== null && (
          <div className="bg-[var(--color-radar-bg)] rounded p-2 border border-[var(--color-radar-border)]">
            <div className="flex items-center justify-between">
              <span className="text-[8px] text-[var(--color-radar-text)] uppercase tracking-widest">
                Last Reward
              </span>
              <span
                className={clsx(
                  "text-sm font-bold font-mono",
                  reward > 0
                    ? "text-[var(--color-radar-green)]"
                    : reward < 0
                      ? "text-[var(--color-radar-red)]"
                      : "text-[var(--color-radar-text)]"
                )}
              >
                {reward > 0 ? "+" : ""}
                {reward.toFixed(1)}
              </span>
            </div>
            <div className="flex items-center justify-between mt-0.5">
              <span className="text-[8px] text-[var(--color-radar-text)] uppercase tracking-widest">
                Cumulative
              </span>
              <span className="text-[10px] font-mono text-[var(--color-radar-text-secondary)]">
                {cumulativeReward.toFixed(1)}
              </span>
            </div>
          </div>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* AI Auto-Play */}
        <div className="bg-[var(--color-radar-bg)] rounded p-2.5 border border-[var(--color-radar-border)]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <Brain size={12} className="text-[var(--color-radar-cyan)]" />
              <span className="text-[9px] text-[var(--color-radar-text)] uppercase tracking-widest">
                AI Agent
              </span>
            </div>
            {aiPlaying && (
              <span className="text-[8px] text-[var(--color-radar-cyan)] ai-thinking font-bold">
                THINKING
              </span>
            )}
          </div>

          <button
            onClick={onToggleAI}
            disabled={!initialized || done}
            className={clsx(
              "w-full flex items-center justify-center gap-2 py-2 rounded text-[11px] font-bold uppercase tracking-wider transition-all",
              aiPlaying
                ? "bg-[rgba(255,51,51,0.12)] border border-[rgba(255,51,51,0.3)] text-[var(--color-radar-red)] hover:bg-[rgba(255,51,51,0.2)]"
                : "bg-[rgba(0,229,255,0.1)] border border-[rgba(0,229,255,0.25)] text-[var(--color-radar-cyan)] hover:bg-[rgba(0,229,255,0.18)]",
              (!initialized || done) && "opacity-30 cursor-not-allowed"
            )}
          >
            {aiPlaying ? (
              <>
                <Pause size={14} /> Stop AI
              </>
            ) : (
              <>
                <Zap size={14} /> Auto-Play
              </>
            )}
          </button>

          {/* Speed Control */}
          <div className="flex items-center gap-1 mt-2">
            <span className="text-[8px] text-[var(--color-radar-text)] uppercase tracking-widest mr-1">
              Speed
            </span>
            {SPEEDS.map((s) => (
              <button
                key={s.value}
                onClick={() => onSetAISpeed(s.value)}
                className={clsx(
                  "flex-1 text-[9px] py-0.5 rounded transition-all",
                  aiSpeed === s.value
                    ? "bg-[rgba(0,229,255,0.15)] text-[var(--color-radar-cyan)] font-bold"
                    : "text-[var(--color-radar-text)] hover:text-[var(--color-radar-bright)]"
                )}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-1.5">
          <button
            onClick={() => onReset(taskId)}
            disabled={loading}
            className="atc-btn flex items-center gap-1.5 px-3"
          >
            <RotateCcw size={12} />
            Reset
          </button>
          <button
            onClick={onStep}
            disabled={loading || done || !initialized}
            className={clsx(
              "atc-btn atc-btn-primary flex-1 flex items-center justify-center gap-1.5",
              loading && "animate-pulse"
            )}
          >
            {loading ? (
              "Processing..."
            ) : done ? (
              "Complete"
            ) : (
              <>
                <Play size={12} fill="currentColor" />
                Clear Flight
                <ChevronRight size={12} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function StatBox({
  label,
  value,
  color,
  glow,
}: {
  label: string;
  value: number;
  color: string;
  glow?: boolean;
}) {
  return (
    <div className="bg-[var(--color-radar-bg)] rounded p-1.5 border border-[var(--color-radar-border)] text-center">
      <div className="text-[8px] text-[var(--color-radar-text)] uppercase tracking-widest">
        {label}
      </div>
      <div
        className="text-lg font-bold font-mono leading-tight"
        style={{
          color,
          textShadow: glow ? `0 0 8px ${color}` : undefined,
        }}
      >
        {value}
      </div>
    </div>
  );
}
