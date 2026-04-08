import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { colors } from "./styles";

interface FlightDot {
  id: string;
  x: number;
  y: number;
  emergency: "MAYDAY" | "PAN_PAN" | "NONE";
  fuel: number;
  label: string;
  landed?: boolean;
}

interface RadarProps {
  flights: FlightDot[];
  size?: number;
  sweepSpeed?: number;
}

export const Radar: React.FC<RadarProps> = ({
  flights,
  size = 500,
  sweepSpeed = 4,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cx = size / 2;
  const cy = size / 2;
  const maxR = size / 2 - 20;

  const sweepAngle = ((frame / fps) * 360) / sweepSpeed;

  const flightColor = (f: FlightDot) => {
    if (f.landed) return colors.text;
    if (f.emergency === "MAYDAY") return colors.red;
    if (f.emergency === "PAN_PAN") return colors.amber;
    if (f.fuel < 10) return colors.amber;
    return colors.green;
  };

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Background */}
      <circle cx={cx} cy={cy} r={maxR} fill="#040810" stroke={colors.border} strokeWidth={1} />

      {/* Range rings */}
      {[0.25, 0.5, 0.75, 1].map((pct) => (
        <circle
          key={pct}
          cx={cx}
          cy={cy}
          r={maxR * pct}
          fill="none"
          stroke="#0d2218"
          strokeWidth={0.5}
        />
      ))}

      {/* Crosshairs */}
      <line x1={cx} y1={20} x2={cx} y2={size - 20} stroke="#0d2218" strokeWidth={0.5} />
      <line x1={20} y1={cy} x2={size - 20} y2={cy} stroke="#0d2218" strokeWidth={0.5} />

      {/* Runway */}
      <rect x={cx - 12} y={cy - 3} width={24} height={6} fill={colors.green} rx={2} />
      <text x={cx} y={cy + 18} fill={colors.green} fontSize={10} textAnchor="middle" fontFamily="monospace">
        RWY
      </text>

      {/* Sweep line */}
      <line
        x1={cx}
        y1={cy}
        x2={cx + Math.cos((sweepAngle * Math.PI) / 180) * maxR}
        y2={cy - Math.sin((sweepAngle * Math.PI) / 180) * maxR}
        stroke={colors.green}
        strokeWidth={2}
        opacity={0.2}
      />

      {/* Sweep gradient */}
      <defs>
        <linearGradient id="sweepGrad" gradientUnits="userSpaceOnUse"
          x1={cx.toString()} y1={cy.toString()}
          x2={(cx + Math.cos((sweepAngle * Math.PI) / 180) * maxR).toString()}
          y2={(cy - Math.sin((sweepAngle * Math.PI) / 180) * maxR).toString()}>
          <stop offset="0%" stopColor={colors.green} stopOpacity={0.3} />
          <stop offset="100%" stopColor={colors.green} stopOpacity={0} />
        </linearGradient>
      </defs>

      {/* Range labels */}
      {[10, 20, 30].map((nm, i) => (
        <text key={nm} x={cx + 5} y={cy - maxR * ((i + 1) * 0.25) + 4}
          fill="#1a4030" fontSize={9} fontFamily="monospace">
          {nm}nm
        </text>
      ))}

      {/* Flights */}
      {flights.map((f) => {
        const color = flightColor(f);
        const px = cx + f.x * maxR;
        const py = cy - f.y * maxR;
        const isEmergency = f.emergency !== "NONE";
        const blinkOpacity = isEmergency && !f.landed
          ? interpolate(Math.sin(frame * 0.3), [-1, 1], [0.4, 1])
          : 1;
        const dotSize = f.landed ? 3 : isEmergency ? 7 : 5;

        // Animate landing: move toward center
        const finalX = f.landed
          ? cx + interpolate(spring({ frame, fps, config: { damping: 20 } }), [0, 1], [f.x * maxR, 0])
          : px;
        const finalY = f.landed
          ? cy - interpolate(spring({ frame, fps, config: { damping: 20 } }), [0, 1], [f.y * maxR, 0])
          : py;

        return (
          <g key={f.id} opacity={f.landed ? 0.3 : blinkOpacity}>
            <circle cx={finalX} cy={finalY} r={dotSize} fill={color} />
            <text x={finalX + 10} y={finalY - 5} fill={color} fontSize={10} fontFamily="monospace" fontWeight="bold">
              {f.label}
            </text>
            <text x={finalX + 10} y={finalY + 7} fill={color} fontSize={8} fontFamily="monospace" opacity={0.7}>
              {f.fuel}m {f.emergency !== "NONE" ? f.emergency : ""}
            </text>
          </g>
        );
      })}
    </svg>
  );
};
