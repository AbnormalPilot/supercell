import React from "react";
import { colors } from "./styles";

interface FlightStripProps {
  callsign: string;
  type: string;
  emergency: "MAYDAY" | "PAN_PAN" | "NONE";
  fuel: number;
  passengers: number;
  medical: boolean;
  active?: boolean;
  landed?: boolean;
  opacity?: number;
}

export const FlightStrip: React.FC<FlightStripProps> = ({
  callsign,
  type,
  emergency,
  fuel,
  passengers,
  medical,
  active = false,
  landed = false,
  opacity = 1,
}) => {
  const borderColor =
    emergency === "MAYDAY" ? colors.red
    : emergency === "PAN_PAN" ? colors.amber
    : active ? colors.green
    : colors.border;

  const bgColor = landed ? "#0a0e1440" : active ? borderColor + "12" : colors.panel;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "10px 16px",
        border: `2px solid ${borderColor}`,
        borderRadius: 8,
        backgroundColor: bgColor,
        fontFamily: "monospace",
        opacity,
        textDecoration: landed ? "line-through" : "none",
      }}
    >
      <div style={{ color: borderColor, fontSize: 18, fontWeight: 800, minWidth: 90 }}>
        {callsign}
      </div>
      <div style={{ color: colors.text, fontSize: 12, minWidth: 80 }}>{type}</div>
      {emergency !== "NONE" && (
        <div
          style={{
            padding: "2px 8px",
            borderRadius: 4,
            backgroundColor: borderColor + "25",
            color: borderColor,
            fontSize: 11,
            fontWeight: 800,
          }}
        >
          {emergency === "MAYDAY" ? "MAYDAY" : "PAN-PAN"}
        </div>
      )}
      {medical && (
        <div
          style={{
            padding: "2px 8px",
            borderRadius: 4,
            backgroundColor: colors.cyan + "25",
            color: colors.cyan,
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          MED
        </div>
      )}
      <div style={{ color: fuel < 10 ? colors.red : fuel < 20 ? colors.amber : colors.text, fontSize: 14, fontWeight: 700, marginLeft: "auto" }}>
        {fuel}m fuel
      </div>
      <div style={{ color: colors.text, fontSize: 12 }}>{passengers} pax</div>
    </div>
  );
};
