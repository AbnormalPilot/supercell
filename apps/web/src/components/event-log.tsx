"use client";

import { useRef, useEffect, useState } from "react";
import type { LogEntry } from "@/lib/types";
import clsx from "clsx";
import {
  PlaneLanding,
  Flame,
  Cloud,
  TerminalSquare,
  Cpu,
  Zap,
} from "lucide-react";

interface EventLogProps {
  log: LogEntry[];
}

const TYPE_CONFIG: Record<
  LogEntry["type"],
  {
    dotClass: string;
    textClass: string;
    icon: React.ReactNode;
    prefix?: string;
  }
> = {
  land: {
    dotClass: "bg-[var(--color-radar-green)] shadow-[0_0_6px_var(--color-radar-green)]",
    textClass: "text-[var(--color-radar-green)]",
    icon: <PlaneLanding size={9} className="text-[var(--color-radar-green)]" />,
  },
  crash: {
    dotClass: "bg-[var(--color-radar-red)] shadow-[0_0_6px_var(--color-radar-red)]",
    textClass: "text-[var(--color-radar-red)] font-bold",
    icon: <Flame size={9} className="text-[var(--color-radar-red)]" />,
  },
  weather: {
    dotClass: "bg-[var(--color-radar-amber)] shadow-[0_0_4px_var(--color-radar-amber)]",
    textClass: "text-[var(--color-radar-amber)]",
    icon: <Cloud size={9} className="text-[var(--color-radar-amber)]" />,
  },
  action: {
    dotClass: "bg-[var(--color-radar-cyan)] shadow-[0_0_4px_var(--color-radar-cyan)]",
    textClass: "text-[var(--color-radar-cyan)]",
    icon: <Zap size={9} className="text-[var(--color-radar-cyan)]" />,
  },
  system: {
    dotClass: "bg-[var(--color-radar-text-secondary)]",
    textClass: "text-[var(--color-radar-text-secondary)]",
    icon: <TerminalSquare size={9} className="text-[var(--color-radar-text-secondary)]" />,
  },
  ai: {
    dotClass: "bg-[var(--color-radar-magenta)] shadow-[0_0_4px_var(--color-radar-magenta)]",
    textClass: "text-[var(--color-radar-magenta)]",
    icon: <Cpu size={9} className="text-[var(--color-radar-magenta)]" />,
    prefix: "AI",
  },
};

function EventEntry({
  entry,
  isNewest,
}: {
  entry: LogEntry;
  isNewest: boolean;
}) {
  const config = TYPE_CONFIG[entry.type];

  return (
    <div
      className={clsx(
        "flex gap-2 px-2 py-1.5 rounded transition-colors",
        isNewest && entry.type === "land" && "flash-land",
        isNewest && entry.type === "crash" && "flash-crash",
        "hover:bg-[var(--color-radar-panel-hover)]"
      )}
    >
      {/* Dot indicator */}
      <div className="flex items-start pt-1 shrink-0">
        <div
          className={clsx("w-1.5 h-1.5 rounded-full", config.dotClass)}
        />
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-1.5">
          {/* Timestamp */}
          <span className="text-[9px] font-mono text-[var(--color-radar-text-secondary)] shrink-0 tabular-nums">
            T:{String(entry.time).padStart(3, "0")}
          </span>

          {/* Icon */}
          <span className="shrink-0 flex items-center">{config.icon}</span>

          {/* Prefix for AI entries */}
          {config.prefix && (
            <span className="text-[9px] font-bold tracking-wider text-[var(--color-radar-magenta)] shrink-0">
              {config.prefix}
            </span>
          )}

          {/* Message */}
          <span className={clsx("text-[10px] leading-tight truncate", config.textClass)}>
            {entry.message}
          </span>
        </div>

        {/* Detail line */}
        {entry.detail && (
          <div className="text-[9px] text-[var(--color-radar-text-secondary)] opacity-70 mt-0.5 pl-4 leading-tight truncate">
            {entry.detail}
          </div>
        )}
      </div>
    </div>
  );
}

export function EventLog({ log }: EventLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [prevLength, setPrevLength] = useState(0);

  // Auto-scroll to top when new entries arrive (newest at top)
  useEffect(() => {
    if (log.length > prevLength && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
    setPrevLength(log.length);
  }, [log.length, prevLength]);

  // Show newest first, cap at 50
  const displayEntries = log.slice(-50).reverse();

  return (
    <div className="atc-panel flex flex-col">
      <div className="atc-panel-header">
        <div className="indicator" />
        <span>Event Log</span>
        {log.length > 0 && (
          <span className="ml-auto text-[9px] font-mono text-[var(--color-radar-text-secondary)]">
            {log.length} events
          </span>
        )}
      </div>

      {displayEntries.length === 0 ? (
        <div className="flex items-center justify-center py-8">
          <span className="text-[10px] uppercase tracking-widest text-[var(--color-radar-text-secondary)]">
            No Events
          </span>
        </div>
      ) : (
        <div
          ref={scrollRef}
          className="overflow-y-auto atc-scroll"
          style={{ maxHeight: "200px" }}
        >
          <div className="py-1">
            {displayEntries.map((entry, i) => (
              <EventEntry
                key={`${entry.time}-${entry.type}-${entry.message}-${i}`}
                entry={entry}
                isNewest={i === 0}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
