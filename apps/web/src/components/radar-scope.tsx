"use client";

import { FlightInfo } from "@/lib/types";
import clsx from "clsx";
import { useMemo } from "react";

interface RadarScopeProps {
  flights: FlightInfo[];
  selectedIndex: number | null;
  onSelect: (index: number) => void;
  className?: string;
}

/** Deterministic angle from callsign string */
function callsignAngle(callsign: string): number {
  const hash = callsign
    .split("")
    .reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  return ((hash * 137.508) % 360) * (Math.PI / 180);
}

function flightColor(flight: FlightInfo): string {
  if (flight.emergency === "MAYDAY") return "var(--color-radar-red)";
  if (flight.emergency === "PAN_PAN") return "var(--color-radar-amber)";
  return "var(--color-radar-green)";
}

function flightColorRaw(flight: FlightInfo): string {
  if (flight.emergency === "MAYDAY") return "#ff3333";
  if (flight.emergency === "PAN_PAN") return "#ffbf00";
  return "#00ff41";
}

const CX = 250;
const CY = 250;
const MAX_RADIUS = 220;
const MAX_NM = 20;
const RING_NM = [5, 10, 15, 20];

export function RadarScope({
  flights,
  selectedIndex,
  onSelect,
  className,
}: RadarScopeProps) {
  const flightPositions = useMemo(
    () =>
      flights.map((f) => {
        const angle = callsignAngle(f.callsign);
        const distRatio = Math.min(f.distance_nm / MAX_NM, 1);
        const r = distRatio * MAX_RADIUS;
        return {
          x: CX + Math.cos(angle) * r,
          y: CY - Math.sin(angle) * r,
        };
      }),
    [flights]
  );

  return (
    <div className={clsx("relative", className)}>
      <svg
        viewBox="0 0 500 500"
        className="w-full"
        style={{ background: "#060a10", borderRadius: 6 }}
      >
        <defs>
          {/* Radar sweep gradient */}
          <linearGradient
            id="sweepGrad"
            x1="0"
            y1="0"
            x2="0"
            y2="1"
          >
            <stop offset="0%" stopColor="#00ff41" stopOpacity="0.35" />
            <stop offset="60%" stopColor="#00ff41" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#00ff41" stopOpacity="0" />
          </linearGradient>

          {/* Subtle grid pattern */}
          <pattern
            id="radarGrid"
            width="25"
            height="25"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 25 0 L 0 0 0 25"
              fill="none"
              stroke="#0d1a14"
              strokeWidth="0.3"
            />
          </pattern>

          {/* Glow filter for selected blips */}
          <filter id="blipGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Grid background */}
        <rect width="500" height="500" fill="url(#radarGrid)" />

        {/* Range rings */}
        {RING_NM.map((nm) => {
          const r = (nm / MAX_NM) * MAX_RADIUS;
          return (
            <g key={nm}>
              <circle
                cx={CX}
                cy={CY}
                r={r}
                fill="none"
                stroke="#0d2a1c"
                strokeWidth={nm === 20 ? 0.8 : 0.5}
                strokeDasharray={nm === 20 ? "none" : "2 4"}
              />
              <text
                x={CX + r + 3}
                y={CY - 3}
                fill="#1a4030"
                fontSize={9}
                fontFamily="monospace"
              >
                {nm}
              </text>
            </g>
          );
        })}

        {/* Crosshair lines */}
        <line
          x1={CX}
          y1={CY - MAX_RADIUS - 10}
          x2={CX}
          y2={CY + MAX_RADIUS + 10}
          stroke="#0d2a1c"
          strokeWidth={0.5}
        />
        <line
          x1={CX - MAX_RADIUS - 10}
          y1={CY}
          x2={CX + MAX_RADIUS + 10}
          y2={CY}
          stroke="#0d2a1c"
          strokeWidth={0.5}
        />

        {/* Compass rose markers */}
        <text
          x={CX}
          y={CY - MAX_RADIUS - 16}
          fill="#1a5038"
          fontSize={10}
          fontFamily="monospace"
          fontWeight={700}
          textAnchor="middle"
        >
          N
        </text>
        <text
          x={CX}
          y={CY + MAX_RADIUS + 24}
          fill="#1a5038"
          fontSize={10}
          fontFamily="monospace"
          fontWeight={700}
          textAnchor="middle"
        >
          S
        </text>
        <text
          x={CX + MAX_RADIUS + 18}
          y={CY + 4}
          fill="#1a5038"
          fontSize={10}
          fontFamily="monospace"
          fontWeight={700}
          textAnchor="middle"
        >
          E
        </text>
        <text
          x={CX - MAX_RADIUS - 18}
          y={CY + 4}
          fill="#1a5038"
          fontSize={10}
          fontFamily="monospace"
          fontWeight={700}
          textAnchor="middle"
        >
          W
        </text>

        {/* Airport / Runway center marker */}
        <rect
          x={CX - 4}
          y={CY - 1.5}
          width={8}
          height={3}
          fill="#00ff41"
          rx={0.5}
          opacity={0.9}
        />
        <text
          x={CX}
          y={CY + 14}
          fill="#00ff41"
          fontSize={7}
          fontFamily="monospace"
          fontWeight={700}
          textAnchor="middle"
          opacity={0.7}
        >
          RWY
        </text>

        {/* Sweep line (rotating) */}
        <line
          x1={CX}
          y1={CY}
          x2={CX}
          y2={CY - MAX_RADIUS}
          stroke="url(#sweepGrad)"
          strokeWidth={2}
          className="radar-sweep"
          style={{ transformOrigin: `${CX}px ${CY}px` }}
        />

        {/* Flight blips */}
        {flights.map((flight, i) => {
          const pos = flightPositions[i];
          if (!pos) return null;

          const color = flightColor(flight);
          const rawColor = flightColorRaw(flight);
          const isSelected = selectedIndex === flight.index;
          const isEmergency =
            flight.emergency === "MAYDAY" || flight.emergency === "PAN_PAN";
          const blipR = isEmergency ? 6 : 5;

          return (
            <g
              key={flight.callsign}
              onClick={() => onSelect(flight.index)}
              className="cursor-pointer radar-blip"
              filter={isSelected ? "url(#blipGlow)" : undefined}
            >
              {/* Selection ring */}
              {isSelected && (
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={12}
                  fill="none"
                  stroke={color}
                  strokeWidth={1.5}
                  opacity={0.5}
                  strokeDasharray="3 2"
                />
              )}

              {/* Blip circle */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={blipR}
                fill={color}
                opacity={0.9}
                className={
                  flight.emergency === "MAYDAY"
                    ? "pulse-mayday"
                    : flight.emergency === "PAN_PAN"
                      ? "pulse-panpan"
                      : ""
                }
              />

              {/* Inner blip dot for depth */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={2}
                fill="#fff"
                opacity={0.4}
              />

              {/* Cannot land X marker */}
              {!flight.can_land_now && (
                <g opacity={0.8}>
                  <line
                    x1={pos.x - 4}
                    y1={pos.y - 4}
                    x2={pos.x + 4}
                    y2={pos.y + 4}
                    stroke="var(--color-radar-red)"
                    strokeWidth={1.5}
                  />
                  <line
                    x1={pos.x + 4}
                    y1={pos.y - 4}
                    x2={pos.x - 4}
                    y2={pos.y + 4}
                    stroke="var(--color-radar-red)"
                    strokeWidth={1.5}
                  />
                </g>
              )}

              {/* Medical indicator (+) */}
              {flight.medical_onboard && (
                <text
                  x={pos.x + blipR + 2}
                  y={pos.y + 1}
                  fill="var(--color-radar-cyan)"
                  fontSize={10}
                  fontFamily="monospace"
                  fontWeight={700}
                >
                  +
                </text>
              )}

              {/* Callsign label */}
              <text
                x={pos.x + blipR + (flight.medical_onboard ? 12 : 4)}
                y={pos.y - 5}
                fill={color}
                fontSize={8}
                fontFamily="monospace"
                fontWeight={600}
              >
                {flight.callsign}
              </text>

              {/* Fuel display below callsign */}
              <text
                x={pos.x + blipR + (flight.medical_onboard ? 12 : 4)}
                y={pos.y + 4}
                fill={rawColor}
                fontSize={7}
                fontFamily="monospace"
                opacity={0.6}
              >
                {flight.fuel_minutes}m
                {flight.distance_nm > 0 && ` ${flight.distance_nm.toFixed(0)}nm`}
              </text>

              {/* Invisible hit area for easier clicking */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={16}
                fill="transparent"
              />
            </g>
          );
        })}
      </svg>
    </div>
  );
}
