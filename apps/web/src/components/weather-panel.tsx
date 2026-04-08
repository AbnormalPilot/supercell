"use client";

import { WeatherInfo } from "@/lib/types";
import {
  Eye,
  Wind,
  ArrowUpRight,
  ArrowRight,
  ArrowDownRight,
  Cloud,
  CloudRain,
  CloudSnow,
  CloudLightning,
  Sun,
  Gauge,
} from "lucide-react";
import clsx from "clsx";

interface WeatherPanelProps {
  weather: WeatherInfo | null;
}

function visColor(nm: number): string {
  if (nm >= 5) return "var(--color-radar-green)";
  if (nm >= 2) return "var(--color-radar-amber)";
  return "var(--color-radar-red)";
}

function windColor(kts: number): string {
  if (kts <= 10) return "var(--color-radar-green)";
  if (kts <= 20) return "var(--color-radar-amber)";
  return "var(--color-radar-red)";
}

function ceilingColor(ft: number): string {
  if (ft >= 3000) return "var(--color-radar-green)";
  if (ft >= 1000) return "var(--color-radar-amber)";
  return "var(--color-radar-red)";
}

function precipLabel(precip: string): string {
  switch (precip.toLowerCase()) {
    case "none":
    case "clear":
      return "CLR";
    case "rain":
      return "RAIN";
    case "snow":
      return "SNOW";
    case "thunderstorm":
    case "tstm":
      return "TSTM";
    default:
      return precip.toUpperCase();
  }
}

function precipColor(precip: string): string {
  const lower = precip.toLowerCase();
  if (lower === "thunderstorm" || lower === "tstm")
    return "var(--color-radar-red)";
  if (lower === "none" || lower === "clear")
    return "var(--color-radar-green)";
  return "var(--color-radar-amber)";
}

function PrecipIcon({ precip }: { precip: string }) {
  const lower = precip.toLowerCase();
  const size = 14;
  const color = precipColor(precip);

  switch (lower) {
    case "none":
    case "clear":
      return <Sun size={size} style={{ color }} />;
    case "rain":
      return <CloudRain size={size} style={{ color }} />;
    case "snow":
      return <CloudSnow size={size} style={{ color }} />;
    case "thunderstorm":
    case "tstm":
      return <CloudLightning size={size} style={{ color }} />;
    default:
      return <Cloud size={size} style={{ color }} />;
  }
}

function trendColor(trend: string): string {
  const lower = trend.toLowerCase();
  if (lower === "improving") return "var(--color-radar-green)";
  if (lower === "stable") return "var(--color-radar-amber)";
  return "var(--color-radar-red)";
}

function TrendIcon({ trend }: { trend: string }) {
  const size = 14;
  const color = trendColor(trend);
  const lower = trend.toLowerCase();

  if (lower === "improving")
    return <ArrowUpRight size={size} style={{ color }} />;
  if (lower === "stable")
    return <ArrowRight size={size} style={{ color }} />;
  return <ArrowDownRight size={size} style={{ color }} />;
}

function trendLabel(trend: string): string {
  const lower = trend.toLowerCase();
  if (lower === "improving") return "IMPROVING";
  if (lower === "stable") return "STABLE";
  if (lower === "deteriorating") return "DETERIOR.";
  return trend.toUpperCase();
}

interface MetricCardProps {
  label: string;
  children: React.ReactNode;
}

function MetricCard({ label, children }: MetricCardProps) {
  return (
    <div
      className="rounded px-2.5 py-2 flex flex-col gap-1"
      style={{
        background: "#0a0e14",
        border: "1px solid var(--color-radar-border)",
      }}
    >
      <span
        style={{
          fontSize: 8,
          fontWeight: 700,
          letterSpacing: "0.12em",
          textTransform: "uppercase" as const,
          color: "var(--color-radar-text-secondary)",
          lineHeight: 1,
        }}
      >
        {label}
      </span>
      <div className="flex items-end gap-1">{children}</div>
    </div>
  );
}

export function WeatherPanel({ weather }: WeatherPanelProps) {
  return (
    <div className="atc-panel">
      {/* Panel header */}
      <div className="atc-panel-header">
        <span className="indicator" />
        METAR
      </div>

      {weather === null ? (
        <div
          className="flex items-center justify-center py-8"
          style={{
            fontSize: 10,
            letterSpacing: "0.1em",
            color: "var(--color-radar-text-secondary)",
          }}
        >
          NO DATA
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-1.5 p-2">
          {/* Visibility */}
          <MetricCard label="Visibility">
            <div className="flex flex-col gap-1 w-full">
              <div className="flex items-baseline gap-1">
                <Eye
                  size={12}
                  style={{ color: visColor(weather.visibility_nm), flexShrink: 0, marginBottom: -1 }}
                />
                <span
                  className="font-bold"
                  style={{
                    fontSize: 16,
                    color: visColor(weather.visibility_nm),
                    lineHeight: 1,
                  }}
                >
                  {weather.visibility_nm}
                </span>
                <span
                  style={{
                    fontSize: 9,
                    color: "var(--color-radar-text-secondary)",
                  }}
                >
                  nm
                </span>
              </div>
              {/* Visibility bar */}
              <div
                className="w-full rounded-full overflow-hidden"
                style={{
                  height: 3,
                  background: "var(--color-radar-border)",
                }}
              >
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${Math.min((weather.visibility_nm / 10) * 100, 100)}%`,
                    background: visColor(weather.visibility_nm),
                    boxShadow: `0 0 4px ${visColor(weather.visibility_nm)}`,
                  }}
                />
              </div>
            </div>
          </MetricCard>

          {/* Wind */}
          <MetricCard label="Wind">
            <Wind
              size={12}
              style={{ color: windColor(weather.wind_knots), flexShrink: 0, marginBottom: 1 }}
            />
            <span
              className="font-bold"
              style={{
                fontSize: 16,
                color: windColor(weather.wind_knots),
                lineHeight: 1,
              }}
            >
              {weather.wind_knots}
            </span>
            <span
              style={{
                fontSize: 9,
                color: "var(--color-radar-text-secondary)",
              }}
            >
              kts
            </span>
          </MetricCard>

          {/* Crosswind */}
          <MetricCard label="Crosswind">
            <Gauge
              size={12}
              style={{ color: windColor(weather.crosswind_knots), flexShrink: 0, marginBottom: 1 }}
            />
            <span
              className="font-bold"
              style={{
                fontSize: 16,
                color: windColor(weather.crosswind_knots),
                lineHeight: 1,
              }}
            >
              {weather.crosswind_knots}
            </span>
            <span
              style={{
                fontSize: 9,
                color: "var(--color-radar-text-secondary)",
              }}
            >
              kts
            </span>
          </MetricCard>

          {/* Ceiling */}
          <MetricCard label="Ceiling">
            <Cloud
              size={12}
              style={{ color: ceilingColor(weather.ceiling_feet), flexShrink: 0, marginBottom: 1 }}
            />
            <span
              className={clsx("font-bold")}
              style={{
                fontSize: 16,
                color: ceilingColor(weather.ceiling_feet),
                lineHeight: 1,
              }}
            >
              {weather.ceiling_feet >= 1000
                ? `${(weather.ceiling_feet / 1000).toFixed(1)}k`
                : weather.ceiling_feet}
            </span>
            <span
              style={{
                fontSize: 9,
                color: "var(--color-radar-text-secondary)",
              }}
            >
              ft
            </span>
          </MetricCard>

          {/* Precipitation */}
          <MetricCard label="Precip">
            <PrecipIcon precip={weather.precipitation} />
            <span
              className="font-bold"
              style={{
                fontSize: 16,
                color: precipColor(weather.precipitation),
                lineHeight: 1,
              }}
            >
              {precipLabel(weather.precipitation)}
            </span>
          </MetricCard>

          {/* Trend */}
          <MetricCard label="Trend">
            <TrendIcon trend={weather.trend} />
            <span
              className="font-bold"
              style={{
                fontSize: 14,
                color: trendColor(weather.trend),
                lineHeight: 1,
              }}
            >
              {trendLabel(weather.trend)}
            </span>
          </MetricCard>
        </div>
      )}
    </div>
  );
}
