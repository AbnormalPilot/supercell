import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { colors, fullScreen } from "../components/styles";
import { Radar } from "../components/Radar";
import { FlightStrip } from "../components/FlightStrip";

// Flight data for the easy scenario simulation
const FLIGHTS = [
  { id: "UAL441", x: 0.5, y: 0.45, type: "B737-800", emergency: "NONE" as const, fuel: 45, pax: 180, medical: false },
  { id: "DAL892", x: 0.3, y: 0.35, type: "A320neo", emergency: "MAYDAY" as const, fuel: 4, pax: 165, medical: false },
  { id: "AAL217", x: -0.55, y: 0.3, type: "B757-200", emergency: "PAN_PAN" as const, fuel: 30, pax: 210, medical: true },
  { id: "SWA103", x: -0.35, y: -0.5, type: "B737-700", emergency: "NONE" as const, fuel: 50, pax: 143, medical: false },
];

// Simulation timeline: spaced to let TTS narration finish before next decision
// intro=297f, d1=431f, d2=390f, d3=366f, d4=315f, score=426f
const LANDING_FRAMES = [330, 810, 1250, 1660]; // frames when each landing happens
const LANDING_ORDER = [1, 2, 0, 3]; // DAL892, AAL217, UAL441, SWA103

// ---- HUD Panel ----
const HUD: React.FC<{
  timeStep: number;
  landed: number;
  crashed: number;
  reward: number;
  score: number | null;
}> = ({ timeStep, landed, crashed, reward, score }) => (
  <div style={{
    display: "flex", gap: 30, padding: "12px 24px",
    backgroundColor: colors.panel, borderRadius: 10,
    border: `1px solid ${colors.border}`,
  }}>
    {[
      { label: "TIME", value: `${timeStep}`, color: colors.cyan },
      { label: "LANDED", value: `${landed}/4`, color: colors.green },
      { label: "CRASHED", value: `${crashed}`, color: crashed > 0 ? colors.red : colors.text },
      { label: "REWARD", value: reward > 0 ? `+${reward.toFixed(0)}` : `${reward.toFixed(0)}`, color: reward >= 0 ? colors.green : colors.red },
      ...(score !== null ? [{ label: "SCORE", value: `${(score * 100).toFixed(0)}%`, color: colors.cyan }] : []),
    ].map((s, i) => (
      <div key={i} style={{ textAlign: "center" }}>
        <div style={{ fontSize: 10, color: colors.text, letterSpacing: 2, fontFamily: "monospace" }}>{s.label}</div>
        <div style={{ fontSize: 28, fontWeight: 900, color: s.color, fontFamily: "monospace" }}>{s.value}</div>
      </div>
    ))}
  </div>
);

// ---- Decision callout ----
const Decision: React.FC<{ text: string; color: string }> = ({ text, color }) => {
  const frame = useCurrentFrame();
  // Stay visible for the full narration, fade in/out at edges
  const opacity = interpolate(frame, [0, 15, 350, 400], [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const y = interpolate(frame, [0, 20], [20, 0], { extrapolateRight: "clamp" });

  return (
    <div style={{
      opacity,
      position: "absolute", bottom: 180, left: "50%",
      transform: `translateX(-50%) translateY(${y}px)`,
      padding: "12px 30px", borderRadius: 10,
      border: `2px solid ${color}`, backgroundColor: color + "15",
      fontSize: 20, fontWeight: 700, color, fontFamily: "monospace",
      letterSpacing: 2,
    }}>
      {text}
    </div>
  );
};

// ---- Weather widget ----
const WeatherWidget: React.FC<{ visibility: number; wind: number; trend: string }> = ({ visibility, wind, trend }) => (
  <div style={{
    padding: "12px 20px", backgroundColor: colors.panel, borderRadius: 10,
    border: `1px solid ${colors.border}`, fontFamily: "monospace",
  }}>
    <div style={{ fontSize: 10, color: colors.text, letterSpacing: 2, marginBottom: 6 }}>WEATHER</div>
    <div style={{ display: "flex", gap: 20 }}>
      <div>
        <div style={{ fontSize: 24, fontWeight: 900, color: visibility >= 5 ? colors.green : visibility >= 2 ? colors.amber : colors.red }}>
          {visibility}nm
        </div>
        <div style={{ fontSize: 9, color: colors.text }}>VIS</div>
      </div>
      <div>
        <div style={{ fontSize: 24, fontWeight: 900, color: colors.text }}>{wind}kt</div>
        <div style={{ fontSize: 9, color: colors.text }}>WIND</div>
      </div>
      <div>
        <div style={{ fontSize: 14, fontWeight: 700, color: colors.green, marginTop: 5 }}>{trend}</div>
        <div style={{ fontSize: 9, color: colors.text }}>TREND</div>
      </div>
    </div>
  </div>
);

// ---- Main Simulation Composition ----
export const ATCSimulation: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Determine which flights have landed based on frame
  const landedSet = new Set<number>();
  let currentReward = 0;
  let currentLanding = -1;

  for (let i = 0; i < LANDING_ORDER.length; i++) {
    if (frame >= LANDING_FRAMES[i]) {
      landedSet.add(LANDING_ORDER[i]);
      currentLanding = i;
    }
  }

  // Cumulative rewards (approximate)
  const rewards = [67.75, 48.5, 15.2, 12.8];
  for (let i = 0; i <= currentLanding; i++) {
    if (i >= 0) currentReward += rewards[i];
  }

  // Time step (approx)
  const timeStep = Math.min(8, Math.floor(landedSet.size * 2));

  // Fuel burn for non-landed flights
  const getFuel = (idx: number) => {
    if (landedSet.has(idx)) return FLIGHTS[idx].fuel;
    return Math.max(0, FLIGHTS[idx].fuel - timeStep);
  };

  // Build radar flights
  const radarFlights = FLIGHTS.map((f, i) => ({
    id: f.id,
    x: f.x,
    y: f.y,
    emergency: f.emergency,
    fuel: getFuel(i),
    label: f.id,
    landed: landedSet.has(i),
  }));

  // Score appears at end
  const allLanded = landedSet.size === 4;
  const score = allLanded && frame > LANDING_FRAMES[3] + 60 ? 1.0 : null;

  // Title fade in
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const titleFade = interpolate(frame, [80, 100], [1, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, fontFamily: "monospace" }}>
      {/* Title overlay */}
      {frame < 100 && (
        <div style={{
          position: "absolute", inset: 0, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", zIndex: 10,
          opacity: titleOpacity * titleFade,
        }}>
          <div style={{ fontSize: 48, fontWeight: 900, color: colors.cyan, letterSpacing: 4 }}>
            LIVE SIMULATION
          </div>
          <div style={{ fontSize: 22, color: colors.text, marginTop: 10 }}>
            Easy Task — Clear Skies Priority — 4 Flights
          </div>
        </div>
      )}

      {/* Main layout */}
      <div style={{
        display: "flex", width: "100%", height: "100%", padding: 30, gap: 30,
        opacity: interpolate(frame, [60, 100], [0, 1], { extrapolateRight: "clamp" }),
      }}>
        {/* Left: Radar */}
        <div style={{ flex: "0 0 550px", display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontSize: 12, color: colors.text, letterSpacing: 3 }}>APPROACH RADAR</div>
          <div style={{
            backgroundColor: "#040810", borderRadius: 16, padding: 20,
            border: `1px solid ${colors.border}`,
          }}>
            <Radar flights={radarFlights} size={500} />
          </div>
          <WeatherWidget visibility={10} wind={8} trend="STABLE" />
        </div>

        {/* Right: Flight strips + HUD */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontSize: 12, color: colors.text, letterSpacing: 3 }}>FLIGHT STRIPS</div>

          {FLIGHTS.map((f, i) => {
            const isLanded = landedSet.has(i);
            const isActive = !isLanded && LANDING_ORDER[landedSet.size] === i;
            const stripOpacity = isLanded ? 0.35 : 1;

            return (
              <FlightStrip
                key={f.id}
                callsign={f.id}
                type={f.type}
                emergency={f.emergency}
                fuel={getFuel(i)}
                passengers={f.pax}
                medical={f.medical}
                active={isActive}
                landed={isLanded}
                opacity={stripOpacity}
              />
            );
          })}

          <div style={{ marginTop: "auto" }}>
            <HUD
              timeStep={timeStep}
              landed={landedSet.size}
              crashed={0}
              reward={Math.round(currentReward)}
              score={score}
            />
          </div>
        </div>
      </div>

      {/* Intro narration */}
      <Sequence from={0} durationInFrames={320} name="Intro Audio">
        <Audio src={staticFile("audio/simulation_01_intro.mp3")} />
      </Sequence>

      {/* Decision callouts with narration — durations match TTS audio */}
      <Sequence from={300} durationInFrames={460} name="Decision 1">
        <Decision text="CLEAR DAL892 — MAYDAY FUEL EMERGENCY" color={colors.red} />
        <Audio src={staticFile("audio/simulation_02_decision1.mp3")} />
      </Sequence>
      <Sequence from={780} durationInFrames={420} name="Decision 2">
        <Decision text="CLEAR AAL217 — PAN-PAN + MEDICAL ONBOARD" color={colors.amber} />
        <Audio src={staticFile("audio/simulation_03_decision2.mp3")} />
      </Sequence>
      <Sequence from={1220} durationInFrames={400} name="Decision 3">
        <Decision text="CLEAR UAL441 — NORMAL PRIORITY" color={colors.green} />
        <Audio src={staticFile("audio/simulation_04_decision3.mp3")} />
      </Sequence>
      <Sequence from={1630} durationInFrames={350} name="Decision 4">
        <Decision text="CLEAR SWA103 — FINAL APPROACH" color={colors.green} />
        <Audio src={staticFile("audio/simulation_05_decision4.mp3")} />
      </Sequence>

      {/* Score reveal */}
      {score !== null && (
        <Sequence from={LANDING_FRAMES[3] + 60} durationInFrames={460} name="Score">
          <Audio src={staticFile("audio/simulation_06_score.mp3")} />
          <div style={{
            position: "absolute", inset: 0, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            backgroundColor: colors.bg + "dd", zIndex: 20,
          }}>
            <div style={{
              opacity: interpolate(frame - LANDING_FRAMES[3] - 60, [0, 30], [0, 1], { extrapolateRight: "clamp" }),
            }}>
              <div style={{ fontSize: 24, color: colors.text, letterSpacing: 4 }}>EPISODE COMPLETE</div>
              <div style={{ fontSize: 120, fontWeight: 900, color: colors.cyan, marginTop: 20 }}>
                100%
              </div>
              <div style={{ fontSize: 20, color: colors.green, marginTop: 10, letterSpacing: 3 }}>
                ALL FLIGHTS LANDED SAFELY
              </div>
              <div style={{ fontSize: 16, color: colors.text, marginTop: 30 }}>
                4/4 landed  |  0 crashed  |  4 steps  |  reward: +194
              </div>
            </div>
          </div>
        </Sequence>
      )}
    </AbsoluteFill>
  );
};
