import type {
  FlightInfo,
  WeatherInfo,
  Observation,
  StepResponse,
  GradeResult,
  TaskInfo,
} from "./types";

const BASE =
  typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? ""
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetchJSON<{ status: string }>("/health"),

  metadata: () =>
    fetchJSON<{ name: string; description: string; version: string }>("/metadata"),

  tasks: () => fetchJSON<TaskInfo[]>("/tasks"),

  reset: (taskId: string) =>
    fetchJSON<{ observation: Observation; reward: number | null; done: boolean }>(
      "/reset",
      {
        method: "POST",
        body: JSON.stringify({ episode_id: taskId }),
      }
    ),

  step: (flightIndex: number) =>
    fetchJSON<StepResponse>("/step", {
      method: "POST",
      body: JSON.stringify({ action: { flight_index: flightIndex } }),
    }),

  state: () => fetchJSON<Record<string, unknown>>("/state"),

  grade: () => fetchJSON<GradeResult>("/grade", { method: "POST" }),
};

export type { FlightInfo, WeatherInfo, Observation, StepResponse, GradeResult, TaskInfo };
