import type { CSSProperties } from "react";

export const colors = {
  bg: "#0a0e14",
  panel: "#111822",
  green: "#00ff41",
  amber: "#ffbf00",
  red: "#ff3333",
  cyan: "#00e5ff",
  text: "#8899aa",
  bright: "#e0e8f0",
  border: "#1e2a3a",
  purple: "#bc8cff",
};

export const fullScreen: CSSProperties = {
  width: "100%",
  height: "100%",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', monospace",
  backgroundColor: colors.bg,
  overflow: "hidden",
};

export const heading: CSSProperties = {
  fontSize: 64,
  fontWeight: 800,
  letterSpacing: 4,
  color: colors.cyan,
  textAlign: "center" as const,
};

export const subheading: CSSProperties = {
  fontSize: 28,
  color: colors.text,
  letterSpacing: 2,
  textAlign: "center" as const,
};

export const label: CSSProperties = {
  fontSize: 14,
  color: colors.text,
  letterSpacing: 3,
  textTransform: "uppercase" as const,
};
