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
  Easing,
} from "remotion";
import { colors, fullScreen } from "../components/styles";
import { Radar } from "../components/Radar";
import { FlightStrip } from "../components/FlightStrip";

// ---- Scene 1: Title ----
const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleY = interpolate(spring({ frame, fps, config: { damping: 15 } }), [0, 1], [60, 0]);
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const subOpacity = interpolate(frame, [15, 35], [0, 1], { extrapolateRight: "clamp" });
  const tagOpacity = interpolate(frame, [40, 60], [0, 1], { extrapolateRight: "clamp" });
  const glowPulse = interpolate(Math.sin(frame * 0.08), [-1, 1], [0.3, 0.8]);

  return (
    <AbsoluteFill style={fullScreen}>
      {/* Glow */}
      <div style={{
        position: "absolute", width: 400, height: 400, borderRadius: "50%",
        background: `radial-gradient(circle, ${colors.cyan}${Math.round(glowPulse * 40).toString(16).padStart(2, "0")} 0%, transparent 70%)`,
        top: "30%", left: "50%", transform: "translate(-50%, -50%)",
      }} />

      <div style={{ ...fullScreen, position: "relative", zIndex: 1 }}>
        <div style={{ opacity: titleOpacity, transform: `translateY(${titleY}px)` }}>
          <div style={{ fontSize: 80, fontWeight: 900, color: colors.cyan, letterSpacing: 6 }}>
            ATC-TRIAGE-v1
          </div>
        </div>
        <div style={{ opacity: subOpacity, marginTop: 20 }}>
          <div style={{ fontSize: 30, color: colors.bright, letterSpacing: 3 }}>
            Air Traffic Control Emergency Prioritization
          </div>
        </div>
        <div style={{ opacity: tagOpacity, marginTop: 40 }}>
          <div style={{ fontSize: 18, color: colors.text, letterSpacing: 4 }}>
            OPENENV-COMPLIANT RL ENVIRONMENT
          </div>
        </div>
        <div style={{ opacity: tagOpacity, marginTop: 30, display: "flex", gap: 30 }}>
          {["Python", "FastAPI", "Next.js", "Turborepo", "Docker"].map((t) => (
            <div key={t} style={{
              padding: "6px 16px", border: `1px solid ${colors.border}`, borderRadius: 6,
              color: colors.green, fontSize: 14, letterSpacing: 2,
            }}>
              {t}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---- Scene 2: The Problem ----
const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();

  const items = [
    { text: "3 flights declaring emergencies", color: colors.red, icon: "!" },
    { text: "2 running out of fuel", color: colors.amber, icon: "F" },
    { text: "Thunderstorm closing in", color: colors.purple, icon: "W" },
    { text: "Which one lands first?", color: colors.cyan, icon: "?" },
  ];

  return (
    <AbsoluteFill style={fullScreen}>
      <div style={{ fontSize: 48, fontWeight: 800, color: colors.cyan, letterSpacing: 3, marginBottom: 50 }}>
        THE PROBLEM
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 800 }}>
        {items.map((item, i) => {
          const itemOpacity = interpolate(frame, [i * 20, i * 20 + 15], [0, 1], { extrapolateRight: "clamp" });
          const itemX = interpolate(frame, [i * 20, i * 20 + 15], [-40, 0], { extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              opacity: itemOpacity, transform: `translateX(${itemX}px)`,
              display: "flex", alignItems: "center", gap: 20,
            }}>
              <div style={{
                width: 50, height: 50, borderRadius: 12, display: "flex", alignItems: "center",
                justifyContent: "center", backgroundColor: item.color + "20", border: `2px solid ${item.color}`,
                color: item.color, fontSize: 24, fontWeight: 900,
              }}>
                {item.icon}
              </div>
              <div style={{ fontSize: 28, color: colors.bright }}>{item.text}</div>
            </div>
          );
        })}
      </div>
      <div style={{
        marginTop: 50, fontSize: 20, color: colors.text, maxWidth: 700, textAlign: "center",
        opacity: interpolate(frame, [80, 100], [0, 1], { extrapolateRight: "clamp" }),
      }}>
        AI agents learn to triage landing priorities under real-world constraints:
        fuel, weather, emergencies, and wake turbulence separation
      </div>
    </AbsoluteFill>
  );
};

// ---- Scene 3: Architecture ----
const ArchScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const boxes = [
    { x: 100, y: 350, w: 250, h: 120, label: "LLM Agent", sub: "GPT-4o / Claude", color: colors.purple },
    { x: 500, y: 200, w: 300, h: 100, label: "FastAPI Server", sub: "/reset /step /state", color: colors.cyan },
    { x: 500, y: 380, w: 300, h: 120, label: "ATCEnvironment", sub: "Simulation Core", color: colors.green },
    { x: 500, y: 580, w: 130, h: 90, label: "Tasks", sub: "3 scenarios", color: colors.amber },
    { x: 670, y: 580, w: 130, h: 90, label: "Graders", sub: "0.0-1.0", color: colors.red },
    { x: 950, y: 350, w: 250, h: 120, label: "Pydantic Models", sub: "Action/Obs/State", color: colors.cyan },
    { x: 1350, y: 350, w: 250, h: 120, label: "Next.js Dashboard", sub: "Radar + Controls", color: colors.green },
  ];

  return (
    <AbsoluteFill style={{ ...fullScreen, justifyContent: "flex-start", paddingTop: 60 }}>
      <div style={{ fontSize: 48, fontWeight: 800, color: colors.cyan, letterSpacing: 3, marginBottom: 30 }}>
        SYSTEM ARCHITECTURE
      </div>
      <svg width={1700} height={700} style={{ marginTop: 20 }}>
        {/* Arrows */}
        {[
          [350, 410, 500, 440, colors.purple],
          [500, 460, 350, 430, colors.green],
          [650, 300, 650, 380, colors.cyan],
          [600, 500, 570, 580, colors.amber],
          [700, 500, 730, 580, colors.red],
          [800, 410, 950, 410, colors.cyan],
          [1200, 410, 1350, 410, colors.green],
        ].map(([x1, y1, x2, y2, c], i) => {
          const arrowOpacity = interpolate(frame, [30 + i * 8, 40 + i * 8], [0, 0.6], { extrapolateRight: "clamp" });
          return (
            <line key={i} x1={x1 as number} y1={y1 as number} x2={x2 as number} y2={y2 as number}
              stroke={c as string} strokeWidth={2} opacity={arrowOpacity}
              markerEnd="url(#arrowhead)" />
          );
        })}
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill={colors.text} />
          </marker>
        </defs>

        {/* Boxes */}
        {boxes.map((b, i) => {
          const boxOpacity = interpolate(frame, [i * 10, i * 10 + 15], [0, 1], { extrapolateRight: "clamp" });
          const boxScale = interpolate(spring({ frame: Math.max(0, frame - i * 10), fps, config: { damping: 12 } }), [0, 1], [0.8, 1]);
          return (
            <g key={i} opacity={boxOpacity} transform={`translate(${b.x + b.w/2}, ${b.y + b.h/2}) scale(${boxScale}) translate(${-(b.x + b.w/2)}, ${-(b.y + b.h/2)})`}>
              <rect x={b.x} y={b.y} width={b.w} height={b.h} rx={12}
                fill={b.color + "15"} stroke={b.color} strokeWidth={2} />
              <text x={b.x + b.w/2} y={b.y + b.h/2 - 5} textAnchor="middle"
                fill={b.color} fontSize={18} fontWeight="bold" fontFamily="monospace">
                {b.label}
              </text>
              <text x={b.x + b.w/2} y={b.y + b.h/2 + 18} textAnchor="middle"
                fill={colors.text} fontSize={12} fontFamily="monospace">
                {b.sub}
              </text>
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};

// ---- Scene 4: How It Works (RL Loop) ----
const RLLoopScene: React.FC = () => {
  const frame = useCurrentFrame();

  const steps = [
    { label: "1. reset(task_id)", desc: "Initialize scenario with flights + weather", color: colors.green },
    { label: "2. Observe", desc: "Flights, fuel, emergencies, weather conditions", color: colors.cyan },
    { label: "3. Decide", desc: "Agent selects flight_index to clear", color: colors.purple },
    { label: "4. step(action)", desc: "Land flight, burn fuel, update weather", color: colors.amber },
    { label: "5. Reward", desc: "+10 to +60 per landing, -100 for crash", color: colors.green },
    { label: "6. grade()", desc: "Final score 0.0 - 1.0 when done", color: colors.cyan },
  ];

  return (
    <AbsoluteFill style={fullScreen}>
      <div style={{ fontSize: 48, fontWeight: 800, color: colors.cyan, letterSpacing: 3, marginBottom: 40 }}>
        HOW IT WORKS
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 900 }}>
        {steps.map((s, i) => {
          const delay = i * 15;
          const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
          const x = interpolate(frame, [delay, delay + 12], [50, 0], { extrapolateRight: "clamp" });
          const active = Math.floor((frame % 120) / 20) === i;

          return (
            <div key={i} style={{
              opacity, transform: `translateX(${x}px)`,
              display: "flex", alignItems: "center", gap: 20,
              padding: "12px 20px", borderRadius: 10,
              border: `2px solid ${active ? s.color : colors.border}`,
              backgroundColor: active ? s.color + "10" : "transparent",
              transition: "all 0.3s",
            }}>
              <div style={{
                fontSize: 18, fontWeight: 900, color: s.color, minWidth: 220,
                fontFamily: "monospace",
              }}>
                {s.label}
              </div>
              <div style={{ fontSize: 18, color: colors.bright }}>{s.desc}</div>
            </div>
          );
        })}
      </div>

      <div style={{
        marginTop: 40, fontSize: 16, color: colors.text,
        opacity: interpolate(frame, [90, 110], [0, 1], { extrapolateRight: "clamp" }),
      }}>
        Loop repeats until all flights landed, crashed, or episode timeout
      </div>
    </AbsoluteFill>
  );
};

// ---- Scene 5: Tasks ----
const TasksScene: React.FC = () => {
  const frame = useCurrentFrame();

  const tasks = [
    {
      name: "EASY", subtitle: "Clear Skies Priority", flights: 4, maydays: 1, panpans: 1,
      weather: "CLEAR", color: colors.green, desc: "Land the MAYDAY first. Don't overthink it.",
    },
    {
      name: "MEDIUM", subtitle: "Storm Window", flights: 7, maydays: 1, panpans: 2,
      weather: "DETERIORATING", color: colors.amber, desc: "Visibility drops from 8nm to 1nm. Race the storm.",
    },
    {
      name: "HARD", subtitle: "Mass Diversion Crisis", flights: 12, maydays: 3, panpans: 2,
      weather: "OSCILLATING", color: colors.red, desc: "12 diverted flights. Weather opens and closes. Chaos.",
    },
  ];

  return (
    <AbsoluteFill style={{ ...fullScreen, justifyContent: "flex-start", paddingTop: 60 }}>
      <div style={{ fontSize: 48, fontWeight: 800, color: colors.cyan, letterSpacing: 3, marginBottom: 40 }}>
        THREE TASKS
      </div>
      <div style={{ display: "flex", gap: 30 }}>
        {tasks.map((t, i) => {
          const delay = i * 25;
          const opacity = interpolate(frame, [delay, delay + 20], [0, 1], { extrapolateRight: "clamp" });
          const scale = interpolate(spring({ frame: Math.max(0, frame - delay), fps: 30, config: { damping: 12 } }), [0, 1], [0.85, 1]);

          return (
            <div key={i} style={{
              opacity, transform: `scale(${scale})`,
              width: 480, padding: 30, borderRadius: 16,
              border: `2px solid ${t.color}`, backgroundColor: t.color + "08",
              display: "flex", flexDirection: "column", gap: 16,
            }}>
              <div style={{ fontSize: 36, fontWeight: 900, color: t.color }}>{t.name}</div>
              <div style={{ fontSize: 16, color: colors.text }}>{t.subtitle}</div>
              <div style={{ display: "flex", gap: 20, marginTop: 10 }}>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 42, fontWeight: 900, color: t.color }}>{t.flights}</div>
                  <div style={{ fontSize: 11, color: colors.text }}>FLIGHTS</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 42, fontWeight: 900, color: colors.red }}>{t.maydays}</div>
                  <div style={{ fontSize: 11, color: colors.text }}>MAYDAY</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 42, fontWeight: 900, color: colors.amber }}>{t.panpans}</div>
                  <div style={{ fontSize: 11, color: colors.text }}>PAN-PAN</div>
                </div>
              </div>
              <div style={{
                padding: "4px 10px", borderRadius: 6, backgroundColor: t.color + "20",
                color: t.color, fontSize: 12, fontWeight: 700, alignSelf: "flex-start",
              }}>
                WX: {t.weather}
              </div>
              <div style={{ fontSize: 15, color: colors.bright, marginTop: 8 }}>{t.desc}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---- Scene 6: Scoring ----
const ScoringScene: React.FC = () => {
  const frame = useCurrentFrame();

  const scores = [
    { strategy: "Urgency (Optimal)", easy: 1.0, med: 0.9, hard: 0.68 },
    { strategy: "First-In (Naive)", easy: 0.86, med: 0.63, hard: 0.42 },
    { strategy: "Last-In (Worst)", easy: 0.7, med: 0.52, hard: 0.3 },
  ];

  const barHeight = 30;
  const maxWidth = 500;

  return (
    <AbsoluteFill style={{ ...fullScreen, justifyContent: "flex-start", paddingTop: 60 }}>
      <div style={{ fontSize: 48, fontWeight: 800, color: colors.cyan, letterSpacing: 3, marginBottom: 40 }}>
        BASELINE SCORES
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 40, maxWidth: 1200 }}>
        {scores.map((s, si) => {
          const delay = si * 30;
          const opacity = interpolate(frame, [delay, delay + 20], [0, 1], { extrapolateRight: "clamp" });

          return (
            <div key={si} style={{ opacity }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: colors.bright, marginBottom: 12 }}>
                {s.strategy}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  { label: "Easy", val: s.easy, color: colors.green },
                  { label: "Medium", val: s.med, color: colors.amber },
                  { label: "Hard", val: s.hard, color: colors.red },
                ].map((bar, bi) => {
                  const barProg = interpolate(frame, [delay + bi * 8, delay + bi * 8 + 25], [0, 1], { extrapolateRight: "clamp" });
                  const width = bar.val * maxWidth * barProg;

                  return (
                    <div key={bi} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <div style={{ fontSize: 13, color: colors.text, width: 60, textAlign: "right" }}>{bar.label}</div>
                      <div style={{
                        width: maxWidth, height: barHeight, backgroundColor: colors.panel,
                        borderRadius: 6, border: `1px solid ${colors.border}`, overflow: "hidden",
                      }}>
                        <div style={{
                          width, height: "100%", backgroundColor: bar.color + "80",
                          borderRadius: 6, borderRight: `2px solid ${bar.color}`,
                        }} />
                      </div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: bar.color, width: 50 }}>
                        {(bar.val * barProg).toFixed(2)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---- Scene 7: Outro ----
const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ ...fullScreen, opacity }}>
      <div style={{ fontSize: 56, fontWeight: 900, color: colors.cyan, letterSpacing: 4 }}>
        ATC-TRIAGE-v1
      </div>
      <div style={{ fontSize: 22, color: colors.text, marginTop: 20, letterSpacing: 2 }}>
        Built for the OpenEnv Hackathon
      </div>
      <div style={{ display: "flex", gap: 40, marginTop: 60 }}>
        {[
          { val: "213", label: "Tests Passing" },
          { val: "3", label: "Task Levels" },
          { val: "7", label: "API Endpoints" },
          { val: "12", label: "Max Flights" },
        ].map((s, i) => (
          <div key={i} style={{ textAlign: "center" }}>
            <div style={{ fontSize: 48, fontWeight: 900, color: colors.green }}>{s.val}</div>
            <div style={{ fontSize: 13, color: colors.text, letterSpacing: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>
      <div style={{
        marginTop: 60, padding: "12px 30px", border: `2px solid ${colors.green}`,
        borderRadius: 10, fontSize: 16, color: colors.green, letterSpacing: 2,
      }}>
        docker compose up  &  uv run python inference.py
      </div>
    </AbsoluteFill>
  );
};

// ---- Main Composition ----
// Scene durations matched to TTS audio length + 30 frame padding
export const ATCExplainer: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <Sequence from={0} durationInFrames={430} name="Title">
        <TitleScene />
        <Audio src={staticFile("audio/explainer_01_title.mp3")} />
      </Sequence>
      <Sequence from={430} durationInFrames={780} name="Problem">
        <ProblemScene />
        <Audio src={staticFile("audio/explainer_02_problem.mp3")} />
      </Sequence>
      <Sequence from={1210} durationInFrames={990} name="Architecture">
        <ArchScene />
        <Audio src={staticFile("audio/explainer_03_architecture.mp3")} />
      </Sequence>
      <Sequence from={2200} durationInFrames={1020} name="RL Loop">
        <RLLoopScene />
        <Audio src={staticFile("audio/explainer_04_loop.mp3")} />
      </Sequence>
      <Sequence from={3220} durationInFrames={960} name="Tasks">
        <TasksScene />
        <Audio src={staticFile("audio/explainer_05_tasks.mp3")} />
      </Sequence>
      <Sequence from={4180} durationInFrames={800} name="Scoring">
        <ScoringScene />
        <Audio src={staticFile("audio/explainer_06_scoring.mp3")} />
      </Sequence>
      <Sequence from={4980} durationInFrames={680} name="Outro">
        <OutroScene />
        <Audio src={staticFile("audio/explainer_07_outro.mp3")} />
      </Sequence>
    </AbsoluteFill>
  );
};
