/** TypeScript types matching backend Pydantic schemas. */

export interface Platform {
  id: string;
  name: string;
  base_url: string;
  login_url: string;
  login_selectors: Record<string, string>;
  extra_config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface AgentTask {
  id: string;
  name: string;
  goal: string;
  constraints: Record<string, unknown> | null;
  platforms: Platform[];
  created_at: string;
  updated_at: string;
}

export type RunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface StepLog {
  id: string;
  run_id: string;
  step_index: number;
  step_type: "agent_thinking" | "tool_call";
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  tool_output: Record<string, unknown> | null;
  agent_reasoning: string | null;
  screenshot_path: string | null;
  duration_ms: number;
  created_at: string;
}

export interface AgentRun {
  id: string;
  task_id: string;
  status: RunStatus;
  started_at: string | null;
  finished_at: string | null;
  final_answer: string | null;
  error: string | null;
  steps: StepLog[];
  created_at: string;
}

/** WebSocket step event pushed from Redis pub/sub. */
export interface StepEvent {
  step_index: number;
  step_type: "agent_thinking" | "tool_call";
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  tool_output: Record<string, unknown> | null;
  agent_reasoning: string | null;
  screenshot_path: string | null;
  duration_ms: number;
}

/** Terminal WebSocket event. */
export interface RunCompleteEvent {
  type: "run_complete";
  status: string;
  final_answer: string | null;
  error: string | null;
}
