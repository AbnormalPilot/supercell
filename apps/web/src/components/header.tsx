"use client";

import clsx from "clsx";

interface HeaderProps {
  connected: boolean;
  taskId: string;
  timeStep: number;
  maxTimeSteps: number;
  landedSafely: number;
  crashed: number;
  totalFlights: number;
  done: boolean;
  aiPlaying: boolean;
}

function taskColor(taskId: string): string {
  switch (taskId.toLowerCase()) {
    case "easy":
      return "var(--color-radar-green)";
    case "medium":
      return "var(--color-radar-amber)";
    case "hard":
      return "var(--color-radar-red)";
    case "extra_hard":
      return "var(--color-radar-cyan)";
    default:
      return "var(--color-radar-text)";
  }
}

function taskBgColor(taskId: string): string {
  switch (taskId.toLowerCase()) {
    case "easy":
      return "rgba(0, 255, 65, 0.1)";
    case "medium":
      return "rgba(255, 191, 0, 0.1)";
    case "hard":
      return "rgba(255, 51, 51, 0.1)";
    case "extra_hard":
      return "rgba(0, 229, 255, 0.1)";
    default:
      return "rgba(106, 125, 141, 0.1)";
  }
}

function taskBorderColor(taskId: string): string {
  switch (taskId.toLowerCase()) {
    case "easy":
      return "rgba(0, 255, 65, 0.25)";
    case "medium":
      return "rgba(255, 191, 0, 0.25)";
    case "hard":
      return "rgba(255, 51, 51, 0.25)";
    case "extra_hard":
      return "rgba(0, 229, 255, 0.25)";
    default:
      return "rgba(106, 125, 141, 0.25)";
  }
}

export function Header({
  connected,
  taskId,
  timeStep,
  maxTimeSteps,
  landedSafely,
  crashed,
  totalFlights,
  done,
  aiPlaying,
}: HeaderProps) {
  const timeProgress = maxTimeSteps > 0 ? (timeStep / maxTimeSteps) * 100 : 0;
  const timeColor =
    timeProgress > 80
      ? "var(--color-radar-red)"
      : timeProgress > 60
        ? "var(--color-radar-amber)"
        : "var(--color-radar-bright)";

  return (
    <header
      className="flex items-center justify-between px-4 w-full select-none"
      style={{
        height: 44,
        background: "var(--color-radar-panel)",
        borderBottom: "1px solid var(--color-radar-border)",
      }}
    >
      {/* Left section: Branding */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Status dot */}
        <span
          className="inline-block rounded-full shrink-0"
          style={{
            width: 6,
            height: 6,
            background: done
              ? "var(--color-radar-amber)"
              : "var(--color-radar-green)",
            boxShadow: done
              ? "0 0 6px var(--color-radar-amber)"
              : "0 0 6px var(--color-radar-green)",
          }}
        />
        <span
          className="font-bold"
          style={{
            fontSize: 11,
            letterSpacing: "0.08em",
            color: "var(--color-radar-bright)",
          }}
        >
          SUPERCELL
        </span>
        <span
          className="font-semibold"
          style={{
            fontSize: 9,
            letterSpacing: "0.1em",
            color: "var(--color-radar-cyan)",
          }}
        >
          v1
        </span>
        <span
          style={{
            width: 1,
            height: 16,
            background: "var(--color-radar-border)",
          }}
        />
        <span
          className="font-bold"
          style={{
            fontSize: 9,
            letterSpacing: "0.12em",
            color: "var(--color-radar-cyan)",
            opacity: 0.7,
          }}
        >
          OPENENV
        </span>
      </div>

      {/* Center section: Status indicators */}
      <div className="flex items-center gap-4">
        {/* Connection status */}
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block rounded-full shrink-0"
            style={{
              width: 5,
              height: 5,
              background: connected
                ? "var(--color-radar-green)"
                : "var(--color-radar-red)",
              boxShadow: connected
                ? "0 0 6px var(--color-radar-green)"
                : "0 0 4px var(--color-radar-red)",
            }}
          />
          <span
            style={{
              fontSize: 10,
              letterSpacing: "0.08em",
              textTransform: "uppercase" as const,
              color: connected
                ? "var(--color-radar-green)"
                : "var(--color-radar-red)",
            }}
          >
            {connected ? "CONNECTED" : "OFFLINE"}
          </span>
        </div>

        {/* Separator */}
        <span
          style={{
            width: 1,
            height: 16,
            background: "var(--color-radar-border)",
          }}
        />

        {/* Task badge */}
        <div
          className="badge"
          style={{
            background: taskBgColor(taskId),
            color: taskColor(taskId),
            border: `1px solid ${taskBorderColor(taskId)}`,
            fontSize: 9,
          }}
        >
          TASK: {taskId.toUpperCase()}
        </div>

        {/* Separator */}
        <span
          style={{
            width: 1,
            height: 16,
            background: "var(--color-radar-border)",
          }}
        />

        {/* Time step */}
        <div className="flex items-center gap-1.5">
          <span
            style={{
              fontSize: 10,
              letterSpacing: "0.08em",
              color: "var(--color-radar-text)",
            }}
          >
            T:
          </span>
          <span
            className="font-bold"
            style={{
              fontSize: 11,
              letterSpacing: "0.05em",
              color: timeColor,
            }}
          >
            {timeStep}
          </span>
          <span
            style={{
              fontSize: 10,
              color: "var(--color-radar-text-secondary)",
            }}
          >
            /
          </span>
          <span
            style={{
              fontSize: 10,
              color: "var(--color-radar-text)",
            }}
          >
            {maxTimeSteps}
          </span>
        </div>
      </div>

      {/* Right section: Counts + AI */}
      <div className="flex items-center gap-4 shrink-0">
        {/* Landed count */}
        <div className="flex items-center gap-1.5">
          <span
            style={{
              fontSize: 11,
              color: "var(--color-radar-green)",
            }}
          >
            &#9650;
          </span>
          <span
            className="font-bold"
            style={{
              fontSize: 11,
              letterSpacing: "0.05em",
              color: "var(--color-radar-green)",
            }}
          >
            {landedSafely}
          </span>
          <span
            style={{
              fontSize: 9,
              letterSpacing: "0.08em",
              color: "var(--color-radar-text-secondary)",
            }}
          >
            LANDED
          </span>
        </div>

        {/* Crashed count */}
        <div className="flex items-center gap-1.5">
          <span
            style={{
              fontSize: 11,
              color:
                crashed > 0
                  ? "var(--color-radar-red)"
                  : "var(--color-radar-text-secondary)",
            }}
          >
            &#10005;
          </span>
          <span
            className={clsx("font-bold", crashed > 0 && "glow-red")}
            style={{
              fontSize: 11,
              letterSpacing: "0.05em",
              color:
                crashed > 0
                  ? "var(--color-radar-red)"
                  : "var(--color-radar-text-secondary)",
            }}
          >
            {crashed}
          </span>
          <span
            style={{
              fontSize: 9,
              letterSpacing: "0.08em",
              color: "var(--color-radar-text-secondary)",
            }}
          >
            CRASHED
          </span>
        </div>

        {/* Separator */}
        <span
          style={{
            width: 1,
            height: 16,
            background: "var(--color-radar-border)",
          }}
        />

        {/* Total flights */}
        <span
          style={{
            fontSize: 10,
            letterSpacing: "0.08em",
            color: "var(--color-radar-text)",
          }}
        >
          {totalFlights} FLT
        </span>

        {/* Separator */}
        <span
          style={{
            width: 1,
            height: 16,
            background: "var(--color-radar-border)",
          }}
        />

        {/* AI indicator */}
        <div className="flex items-center gap-1.5 relative">
          <span
            className={clsx(
              "inline-block rounded-full shrink-0",
              aiPlaying && "ai-thinking"
            )}
            style={{
              width: 6,
              height: 6,
              background: aiPlaying
                ? "var(--color-radar-cyan)"
                : "var(--color-radar-text-secondary)",
              boxShadow: aiPlaying
                ? "0 0 8px var(--color-radar-cyan)"
                : "none",
            }}
          />
          <span
            style={{
              fontSize: 10,
              letterSpacing: "0.08em",
              fontWeight: 700,
              color: aiPlaying
                ? "var(--color-radar-cyan)"
                : "var(--color-radar-text-secondary)",
            }}
          >
            AI &#9670;
          </span>
        </div>
      </div>
    </header>
  );
}
