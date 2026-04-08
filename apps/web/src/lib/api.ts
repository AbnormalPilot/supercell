import type {
  FlightInfo,
  WeatherInfo,
  Observation,
  StepResponse,
  GradeResult,
  TaskInfo,
} from "./types";

function debugLog(
  runId: string,
  hypothesisId: string,
  location: string,
  message: string,
  data: Record<string, unknown>
): void {
  // #region agent log
  fetch("http://127.0.0.1:7465/ingest/8f201e13-abe3-4cbe-83f6-ddef9ae575d2", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Debug-Session-Id": "502976",
    },
    body: JSON.stringify({
      sessionId: "502976",
      runId,
      hypothesisId,
      location,
      message,
      data,
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion
}

function getBaseUrl(): string {
  // In the browser (including HF Spaces), always call same-origin API.
  if (typeof window !== "undefined") {
    const base = window.location.origin;
    // #region agent log
    debugLog("pre-fix", "H1", "apps/web/src/lib/api.ts:getBaseUrl", "resolved browser base url", {
      base,
      href: window.location.href,
      hostname: window.location.hostname,
      pathname: window.location.pathname,
    });
    // #endregion
    return base;
  }
  // Fallback for non-browser execution paths.
  const fallback = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  // #region agent log
  debugLog("pre-fix", "H2", "apps/web/src/lib/api.ts:getBaseUrl", "resolved non-browser fallback base", {
    fallback,
    hasEnv: Boolean(process.env.NEXT_PUBLIC_API_URL),
  });
  // #endregion
  return fallback;
}

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const base = getBaseUrl();
  const url = `${base}${path}`;
  const method = init?.method ?? "GET";
  // #region agent log
  debugLog("pre-fix", "H3", "apps/web/src/lib/api.ts:fetchJSON", "starting fetch", {
    url,
    path,
    method,
  });
  // #endregion
  try {
    const res = await fetch(url, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
    // #region agent log
    debugLog("pre-fix", "H4", "apps/web/src/lib/api.ts:fetchJSON", "fetch completed", {
      url,
      status: res.status,
      ok: res.ok,
      statusText: res.statusText,
      redirected: res.redirected,
      responseType: res.type,
    });
    // #endregion
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json() as Promise<T>;
  } catch (error) {
    // #region agent log
    debugLog("pre-fix", "H5", "apps/web/src/lib/api.ts:fetchJSON", "fetch threw error", {
      url,
      method,
      error: error instanceof Error ? error.message : String(error),
    });
    // #endregion
    throw error;
  }
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
