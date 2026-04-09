export interface FlightInfo {
  index: number;
  callsign: string;
  aircraft_type: string;
  emergency: "NONE" | "PAN_PAN" | "MAYDAY";
  fuel_minutes: number;
  passengers: number;
  distance_nm: number;
  medical_onboard: boolean;
  min_visibility_nm: number;
  wake_category: "LIGHT" | "MEDIUM" | "HEAVY" | "SUPER";
  can_land_now: boolean;
}

export interface WeatherInfo {
  visibility_nm: number;
  wind_knots: number;
  crosswind_knots: number;
  ceiling_feet: number;
  precipitation: string;
  trend: string;
}

export interface Observation {
  flights: FlightInfo[];
  weather: WeatherInfo;
  runway_free_in_steps: number;
  time_step: number;
  max_time_steps: number;
  landed_safely: number;
  crashed: number;
  total_flights: number;
  task_id: string;
  instructions: string;
  done: boolean;
  reward: number | null;
}

export interface StepResponse {
  observation: Observation;
  reward: number;
  done: boolean;
}

export interface GradeResult {
  task_id: string;
  score: number;
  landing_log: LandingEntry[];
  crash_log: CrashEntry[];
  steps_used: number;
  episode_reward: number;
}

export interface LandingEntry {
  callsign: string;
  step: number;
  fuel_remaining: number;
  emergency: string;
  passengers: number;
  medical: boolean;
}

export interface CrashEntry {
  callsign: string;
  step: number;
  emergency: string;
  passengers: number;
}

export interface LogEntry {
  time: number;
  type: "land" | "crash" | "weather" | "action" | "system" | "ai";
  message: string;
  detail?: string;
}

export type TaskId = "easy" | "medium" | "hard" | "extra_hard";

export interface TaskInfo {
  task_id: string;
  task_name: string;
  description: string;
  num_flights: number;
  max_steps: number;
}

export interface ATCState {
  connected: boolean;
  initialized: boolean;
  loading: boolean;
  taskId: TaskId;
  flights: FlightInfo[];
  weather: WeatherInfo | null;
  selectedIndex: number | null;
  timeStep: number;
  maxTimeSteps: number;
  landedSafely: number;
  crashed: number;
  totalFlights: number;
  reward: number | null;
  cumulativeReward: number;
  score: GradeResult | null;
  done: boolean;
  log: LogEntry[];
  aiPlaying: boolean;
  aiSpeed: number;
}
