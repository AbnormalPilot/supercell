"use client";

import { useRef, useEffect } from "react";
import type { FlightInfo } from "@/lib/types";
import clsx from "clsx";
import {
  Plane,
  AlertTriangle,
  Fuel,
  Users,
  Navigation,
  Eye,
  Wind,
  Cross,
  ChevronRight,
  Radio,
} from "lucide-react";

interface FlightStripsProps {
  flights: FlightInfo[];
  selectedIndex: number | null;
  onSelect: (index: number) => void;
  onClear: () => void;
  done: boolean;
  loading: boolean;
}

function getFuelLevel(fuelMinutes: number): "critical" | "low" | "normal" {
  if (fuelMinutes < 10) return "critical";
  if (fuelMinutes < 20) return "low";
  return "normal";
}

function getFuelPercent(fuelMinutes: number): number {
  return Math.min((fuelMinutes / 60) * 100, 100);
}

function getWakeLabel(wake: FlightInfo["wake_category"]): string {
  switch (wake) {
    case "SUPER":
      return "SUP";
    case "HEAVY":
      return "HVY";
    case "MEDIUM":
      return "MED";
    case "LIGHT":
      return "LGT";
  }
}

function FlightStripCard({
  flight,
  isSelected,
  onSelect,
  onClear,
  loading,
}: {
  flight: FlightInfo;
  isSelected: boolean;
  onSelect: () => void;
  onClear: () => void;
  loading: boolean;
}) {
  const isMayday = flight.emergency === "MAYDAY";
  const isPanPan = flight.emergency === "PAN_PAN";
  const fuelLevel = getFuelLevel(flight.fuel_minutes);
  const fuelPercent = getFuelPercent(flight.fuel_minutes);

  return (
    <div
      onClick={onSelect}
      className={clsx(
        "flight-strip",
        isMayday && "mayday",
        isPanPan && "panpan",
        isSelected && "selected",
        isMayday && "pulse-mayday",
        isPanPan && "pulse-panpan"
      )}
    >
      {/* Top row: Emergency badge, callsign, aircraft, index */}
      <div className="flex items-center gap-2 mb-1.5">
        {isMayday && (
          <span className="badge badge-mayday">
            <AlertTriangle size={9} />
            MAYDAY
          </span>
        )}
        {isPanPan && (
          <span className="badge badge-panpan">
            <AlertTriangle size={9} />
            PAN-PAN
          </span>
        )}

        <span
          className={clsx(
            "text-[13px] font-bold tracking-wide",
            isMayday
              ? "text-[var(--color-radar-red)]"
              : isPanPan
                ? "text-[var(--color-radar-amber)]"
                : "text-[var(--color-radar-bright)]"
          )}
        >
          {flight.callsign}
        </span>

        <span className="text-[10px] text-[var(--color-radar-text-secondary)] tracking-wider flex items-center gap-1">
          <Plane size={10} className="opacity-50" />
          {flight.aircraft_type}
        </span>

        <span className="ml-auto text-[10px] text-[var(--color-radar-text-secondary)] font-mono">
          #{flight.index}
        </span>
      </div>

      {/* Divider */}
      <div className="border-t border-dashed border-[var(--color-radar-border)] mb-1.5" />

      {/* Middle row: Fuel bar, PAX, distance */}
      <div className="flex items-center gap-3 mb-1.5">
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          <Fuel
            size={10}
            className={clsx(
              fuelLevel === "critical"
                ? "text-[var(--color-radar-red)]"
                : fuelLevel === "low"
                  ? "text-[var(--color-radar-amber)]"
                  : "text-[var(--color-radar-text-secondary)]"
            )}
          />
          <div className="fuel-bar flex-1">
            <div
              className={clsx("fuel-bar-fill", fuelLevel)}
              style={{ width: `${fuelPercent}%` }}
            />
          </div>
          <span
            className={clsx(
              "text-[10px] font-mono font-bold min-w-[32px] text-right",
              fuelLevel === "critical"
                ? "text-[var(--color-radar-red)]"
                : fuelLevel === "low"
                  ? "text-[var(--color-radar-amber)]"
                  : "text-[var(--color-radar-text)]"
            )}
          >
            {flight.fuel_minutes}m
          </span>
        </div>

        <div className="flex items-center gap-1 text-[10px] text-[var(--color-radar-text)]">
          <Users size={10} className="opacity-60" />
          <span className="font-mono">{flight.passengers}</span>
        </div>

        <div className="flex items-center gap-1 text-[10px] text-[var(--color-radar-text)]">
          <Navigation size={10} className="opacity-60" />
          <span className="font-mono">{flight.distance_nm.toFixed(1)}nm</span>
        </div>
      </div>

      {/* Bottom row: Visibility, wake, status, medical, clear button */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 text-[10px] text-[var(--color-radar-text-secondary)]">
          <Eye size={9} className="opacity-50" />
          <span className="font-mono">{flight.min_visibility_nm}nm</span>
        </div>

        <span className="text-[9px] font-bold tracking-wider text-[var(--color-radar-text-secondary)] px-1.5 py-0.5 rounded bg-[var(--color-radar-border)] bg-opacity-40">
          <Wind size={8} className="inline-block mr-0.5 -mt-px" />
          {getWakeLabel(flight.wake_category)}
        </span>

        <div className="border-l border-[var(--color-radar-border)] h-3 mx-0.5" />

        {flight.can_land_now ? (
          <span className="badge badge-ready">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-radar-green)] shadow-[0_0_4px_var(--color-radar-green)]" />
            READY
          </span>
        ) : (
          <span className="badge badge-hold">
            <span className="text-[9px]">&#8856;</span>
            WX HOLD
          </span>
        )}

        {flight.medical_onboard && (
          <span className="badge badge-medical">
            <Cross size={8} />
            MED
          </span>
        )}

        <div className="ml-auto">
          {isSelected && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClear();
              }}
              disabled={loading}
              className={clsx(
                "atc-btn atc-btn-primary flex items-center gap-1 text-[10px] py-1 px-3",
                loading && "opacity-50 cursor-not-allowed animate-pulse"
              )}
            >
              CLEAR
              <ChevronRight size={10} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function FlightStrips({
  flights,
  selectedIndex,
  onSelect,
  onClear,
  done,
  loading,
}: FlightStripsProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to selected strip
  useEffect(() => {
    if (selectedIndex === null || !scrollRef.current) return;
    const selected = scrollRef.current.querySelector(
      `[data-strip-index="${selectedIndex}"]`
    );
    if (selected) {
      selected.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedIndex]);

  const pendingCount = flights.length;

  return (
    <div className="atc-panel h-full flex flex-col">
      <div className="atc-panel-header">
        <div className="indicator" />
        <span>
          Flight Strip Board{" "}
          <span className="text-[var(--color-radar-text-secondary)]">
            &mdash; {pendingCount} Pending
          </span>
        </span>
        {loading && (
          <Radio
            size={11}
            className="ml-auto text-[var(--color-radar-cyan)] ai-thinking"
          />
        )}
      </div>

      {flights.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-12 gap-3">
          <Plane
            size={28}
            className={clsx(
              done
                ? "text-[var(--color-radar-green)] opacity-60"
                : "text-[var(--color-radar-text-secondary)] opacity-40"
            )}
          />
          <span
            className={clsx(
              "text-[11px] font-bold uppercase tracking-widest",
              done
                ? "glow-green"
                : "text-[var(--color-radar-text-secondary)]"
            )}
          >
            {done ? "All Flights Processed" : "Awaiting Traffic"}
          </span>
        </div>
      ) : (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto atc-scroll p-2 space-y-2"
        >
          {flights.map((flight) => (
            <div key={flight.callsign} data-strip-index={flight.index}>
              <FlightStripCard
                flight={flight}
                isSelected={selectedIndex === flight.index}
                onSelect={() => onSelect(flight.index)}
                onClear={onClear}
                loading={loading}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
