"use client";

import type { GradeResult } from "@/lib/types";
import clsx from "clsx";
import {
  Trophy,
  PlaneLanding,
  Flame,
  Clock,
  Zap,
  AlertTriangle,
  Cross,
  Shield,
} from "lucide-react";

interface ScoreBreakdownProps {
  score: GradeResult | null;
  taskId: string;
}

function getScoreColor(score: number): string {
  if (score >= 0.7) return "green";
  if (score >= 0.4) return "amber";
  return "red";
}

function getBarBg(color: string): string {
  switch (color) {
    case "green":
      return "bg-[var(--color-radar-green)] shadow-[0_0_8px_rgba(0,255,65,0.3)]";
    case "amber":
      return "bg-[var(--color-radar-amber)] shadow-[0_0_8px_rgba(255,191,0,0.3)]";
    case "red":
      return "bg-[var(--color-radar-red)] shadow-[0_0_8px_rgba(255,51,51,0.3)]";
    default:
      return "bg-[var(--color-radar-text)]";
  }
}

function getGlowClass(color: string): string {
  switch (color) {
    case "green":
      return "glow-green";
    case "amber":
      return "glow-amber";
    case "red":
      return "glow-red";
    default:
      return "";
  }
}

function EmergencyBadge({ emergency }: { emergency: string }) {
  if (emergency === "MAYDAY") {
    return (
      <span className="badge badge-mayday">
        <AlertTriangle size={8} />
        MAYDAY
      </span>
    );
  }
  if (emergency === "PAN_PAN") {
    return (
      <span className="badge badge-panpan">
        <AlertTriangle size={8} />
        PAN-PAN
      </span>
    );
  }
  return (
    <span className="text-[9px] text-[var(--color-radar-text-secondary)]">
      &mdash;
    </span>
  );
}

export function ScoreBreakdown({ score, taskId }: ScoreBreakdownProps) {
  if (!score) return null;

  const scoreColor = getScoreColor(score.score);
  const scorePercent = (score.score * 100).toFixed(1);
  const landedCount = score.landing_log.length;
  const crashedCount = score.crash_log.length;

  return (
    <div className="atc-panel score-reveal">
      <div className="atc-panel-header">
        <div className="indicator" />
        <Trophy size={11} className="text-[var(--color-radar-amber)]" />
        <span>Mission Report</span>
        <span className="ml-auto text-[9px] font-mono text-[var(--color-radar-text-secondary)] uppercase">
          {taskId}
        </span>
      </div>

      <div className="p-4 space-y-4">
        {/* Large score display */}
        <div className="text-center py-3">
          <div className="text-[9px] uppercase tracking-[0.2em] text-[var(--color-radar-text-secondary)] mb-2">
            Episode Score
          </div>
          <div
            className={clsx(
              "text-5xl font-bold font-mono tracking-tight",
              "glow-cyan"
            )}
          >
            {scorePercent}
            <span className="text-2xl opacity-70">%</span>
          </div>
          <div className="text-[10px] text-[var(--color-radar-text)] mt-2 font-mono">
            Episode Reward:{" "}
            <span
              className={clsx(
                "font-bold",
                score.episode_reward >= 0
                  ? "text-[var(--color-radar-green)]"
                  : "text-[var(--color-radar-red)]"
              )}
            >
              {score.episode_reward >= 0 ? "+" : ""}
              {score.episode_reward.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Score bar */}
        <div>
          <div className="flex justify-between text-[9px] uppercase tracking-wider text-[var(--color-radar-text-secondary)] mb-1.5">
            <span>Performance</span>
            <span className={getGlowClass(scoreColor)}>
              {scorePercent}%
            </span>
          </div>
          <div className="progress-track">
            <div
              className={clsx("progress-fill", getBarBg(scoreColor))}
              style={{ width: `${Math.min(score.score * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-4 gap-2">
          <div className="bg-[var(--color-radar-surface)] rounded p-2 text-center border border-[var(--color-radar-border)]">
            <PlaneLanding
              size={12}
              className="mx-auto mb-1 text-[var(--color-radar-green)] opacity-70"
            />
            <div className="text-lg font-bold font-mono text-[var(--color-radar-green)]">
              {landedCount}
            </div>
            <div className="text-[8px] uppercase tracking-wider text-[var(--color-radar-text-secondary)]">
              Landed
            </div>
          </div>

          <div className="bg-[var(--color-radar-surface)] rounded p-2 text-center border border-[var(--color-radar-border)]">
            <Flame
              size={12}
              className={clsx(
                "mx-auto mb-1 opacity-70",
                crashedCount > 0
                  ? "text-[var(--color-radar-red)]"
                  : "text-[var(--color-radar-text-secondary)]"
              )}
            />
            <div
              className={clsx(
                "text-lg font-bold font-mono",
                crashedCount > 0
                  ? "text-[var(--color-radar-red)]"
                  : "text-[var(--color-radar-text-secondary)]"
              )}
            >
              {crashedCount}
            </div>
            <div className="text-[8px] uppercase tracking-wider text-[var(--color-radar-text-secondary)]">
              Crashed
            </div>
          </div>

          <div className="bg-[var(--color-radar-surface)] rounded p-2 text-center border border-[var(--color-radar-border)]">
            <Clock
              size={12}
              className="mx-auto mb-1 text-[var(--color-radar-cyan)] opacity-70"
            />
            <div className="text-lg font-bold font-mono text-[var(--color-radar-cyan)]">
              {score.steps_used}
            </div>
            <div className="text-[8px] uppercase tracking-wider text-[var(--color-radar-text-secondary)]">
              Steps
            </div>
          </div>

          <div className="bg-[var(--color-radar-surface)] rounded p-2 text-center border border-[var(--color-radar-border)]">
            <Zap
              size={12}
              className={clsx(
                "mx-auto mb-1 opacity-70",
                score.episode_reward >= 0
                  ? "text-[var(--color-radar-amber)]"
                  : "text-[var(--color-radar-red)]"
              )}
            />
            <div
              className={clsx(
                "text-lg font-bold font-mono",
                score.episode_reward >= 0
                  ? "text-[var(--color-radar-amber)]"
                  : "text-[var(--color-radar-red)]"
              )}
            >
              {score.episode_reward >= 0 ? "+" : ""}
              {score.episode_reward.toFixed(1)}
            </div>
            <div className="text-[8px] uppercase tracking-wider text-[var(--color-radar-text-secondary)]">
              Reward
            </div>
          </div>
        </div>

        {/* Landing log */}
        {landedCount > 0 && (
          <div>
            <div className="text-[9px] uppercase tracking-wider text-[var(--color-radar-text-secondary)] mb-1.5 flex items-center gap-1.5">
              <Shield size={9} className="text-[var(--color-radar-green)]" />
              Landing Log
            </div>
            <div className="bg-[var(--color-radar-surface)] rounded border border-[var(--color-radar-border)] overflow-hidden">
              {/* Table header */}
              <div className="grid grid-cols-[1fr_50px_50px_60px_40px] gap-1 px-2 py-1 text-[8px] uppercase tracking-wider text-[var(--color-radar-text-secondary)] border-b border-[var(--color-radar-border)]">
                <span>Callsign</span>
                <span className="text-right">Step</span>
                <span className="text-right">Fuel</span>
                <span className="text-center">Emrg</span>
                <span className="text-center">Med</span>
              </div>

              {/* Table rows */}
              <div className="max-h-[120px] overflow-y-auto atc-scroll">
                {score.landing_log.map((entry, i) => (
                  <div
                    key={`${entry.callsign}-${i}`}
                    className={clsx(
                      "grid grid-cols-[1fr_50px_50px_60px_40px] gap-1 px-2 py-1 text-[10px] items-center",
                      i % 2 === 0
                        ? "bg-transparent"
                        : "bg-[var(--color-radar-panel)]"
                    )}
                  >
                    <span className="font-bold text-[var(--color-radar-green)] truncate">
                      {entry.callsign}
                    </span>
                    <span className="text-right font-mono text-[var(--color-radar-text)]">
                      T:{entry.step}
                    </span>
                    <span
                      className={clsx(
                        "text-right font-mono",
                        entry.fuel_remaining < 5
                          ? "text-[var(--color-radar-red)]"
                          : entry.fuel_remaining < 15
                            ? "text-[var(--color-radar-amber)]"
                            : "text-[var(--color-radar-text)]"
                      )}
                    >
                      {entry.fuel_remaining}m
                    </span>
                    <span className="text-center">
                      <EmergencyBadge emergency={entry.emergency} />
                    </span>
                    <span className="text-center">
                      {entry.medical && (
                        <Cross
                          size={9}
                          className="inline text-[var(--color-radar-cyan)]"
                        />
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Crash log */}
        {crashedCount > 0 && (
          <div>
            <div className="text-[9px] uppercase tracking-wider text-[var(--color-radar-red)] mb-1.5 flex items-center gap-1.5">
              <Flame size={9} />
              Crash Log
            </div>
            <div className="bg-[rgba(255,51,51,0.05)] rounded border border-[rgba(255,51,51,0.2)] overflow-hidden">
              {score.crash_log.map((entry, i) => (
                <div
                  key={`${entry.callsign}-crash-${i}`}
                  className={clsx(
                    "flex items-center justify-between px-2 py-1.5 text-[10px]",
                    i > 0 && "border-t border-[rgba(255,51,51,0.1)]"
                  )}
                >
                  <span className="font-bold text-[var(--color-radar-red)]">
                    {entry.callsign}
                  </span>
                  <span className="font-mono text-[var(--color-radar-text-secondary)]">
                    T:{entry.step}
                  </span>
                  <EmergencyBadge emergency={entry.emergency} />
                  <span className="text-[var(--color-radar-text-secondary)] font-mono">
                    {entry.passengers} pax
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
