import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import type { AgentRun, AgentTask, RunStatus, StepEvent } from "../types";
import { fetchRun, fetchTask, cancelRun } from "../api/client";
import { useWebSocket } from "../hooks/useWebSocket";
import LiveGraph from "../components/LiveGraph/LiveGraph";
import AgentThinking from "../components/AgentThinking/AgentThinking";
import StepLogTable from "../components/StepLogTable/StepLogTable";
import ScreenshotViewer from "../components/ScreenshotViewer/ScreenshotViewer";

/** Map backend step logs to the StepEvent shape used by our components. */
function stepLogToEvent(s: AgentRun["steps"][number]): StepEvent {
  return {
    step_index: s.step_index,
    step_type: s.step_type,
    tool_name: s.tool_name,
    tool_input: s.tool_input,
    tool_output: s.tool_output,
    agent_reasoning: s.agent_reasoning,
    screenshot_path: s.screenshot_path,
    duration_ms: s.duration_ms,
  };
}

const STATUS_CONFIG: Record<
  RunStatus,
  { label: string; color: string; bgColor: string; pulse: boolean }
> = {
  pending: {
    label: "Pending",
    color: "text-warning",
    bgColor: "bg-warning/15",
    pulse: true,
  },
  running: {
    label: "Running",
    color: "text-accent-400",
    bgColor: "bg-accent-500/15",
    pulse: true,
  },
  completed: {
    label: "Completed",
    color: "text-success",
    bgColor: "bg-success/15",
    pulse: false,
  },
  failed: {
    label: "Failed",
    color: "text-danger",
    bgColor: "bg-danger/15",
    pulse: false,
  },
  cancelled: {
    label: "Cancelled",
    color: "text-text-muted",
    bgColor: "bg-surface-600/50",
    pulse: false,
  },
};

export default function RunMonitorPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<AgentRun | null>(null);
  const [task, setTask] = useState<AgentTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  // Current effective status (may be overridden by WebSocket completion)
  const [liveStatus, setLiveStatus] = useState<RunStatus | null>(null);
  const [finalAnswer, setFinalAnswer] = useState<string | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);

  // Determine if we should connect the WebSocket
  const runStatus = liveStatus ?? run?.status;
  const shouldStream = runStatus === "pending" || runStatus === "running";

  const {
    steps: wsSteps,
    completion,
    status: wsStatus,
  } = useWebSocket(shouldStream ? runId : undefined);

  // Load initial run + task data
  const loadRun = useCallback(async () => {
    if (!runId) return;
    try {
      setLoading(true);
      setError(null);
      const runData = await fetchRun(runId);
      setRun(runData);
      setLiveStatus(runData.status as RunStatus);
      setFinalAnswer(runData.final_answer);
      setLiveError(runData.error);

      // Fetch associated task
      const taskData = await fetchTask(runData.task_id);
      setTask(taskData);
    } catch {
      setError("Failed to load run.");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    loadRun();
  }, [loadRun]);

  // Handle WebSocket completion event
  useEffect(() => {
    if (completion) {
      setLiveStatus(completion.status as RunStatus);
      setFinalAnswer(completion.final_answer);
      setLiveError(completion.error);
    }
  }, [completion]);

  // Merge historical steps (from initial fetch) with live WS steps
  const allSteps: StepEvent[] = useMemo(() => {
    const historical = run?.steps.map(stepLogToEvent) ?? [];
    if (wsSteps.length === 0) return historical;

    // WS steps arrive after historical load — deduplicate by step_index
    const seen = new Set(historical.map((s) => s.step_index));
    const merged = [...historical];
    for (const ws of wsSteps) {
      if (!seen.has(ws.step_index)) {
        merged.push(ws);
        seen.add(ws.step_index);
      }
    }
    return merged.sort((a, b) => a.step_index - b.step_index);
  }, [run?.steps, wsSteps]);

  // Latest reasoning from most recent agent_thinking step
  const latestReasoning = useMemo(() => {
    for (let i = allSteps.length - 1; i >= 0; i--) {
      if (
        allSteps[i].step_type === "agent_thinking" &&
        allSteps[i].agent_reasoning
      ) {
        return allSteps[i].agent_reasoning;
      }
    }
    return null;
  }, [allSteps]);

  const isRunning = runStatus === "running" || runStatus === "pending";

  async function handleCancel() {
    if (!runId) return;
    setCancelling(true);
    try {
      const updated = await cancelRun(runId);
      setLiveStatus(updated.status as RunStatus);
    } catch {
      setError("Failed to cancel run.");
    } finally {
      setCancelling(false);
    }
  }

  function formatDuration(start: string | null, end: string | null): string {
    if (!start) return "--";
    const s = new Date(start).getTime();
    const e = end ? new Date(end).getTime() : Date.now();
    const sec = Math.floor((e - s) / 1000);
    if (sec < 60) return `${sec}s`;
    return `${Math.floor(sec / 60)}m ${sec % 60}s`;
  }

  const statusCfg = STATUS_CONFIG[runStatus ?? "pending"];

  // ---------- Loading / Error states ----------

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32 text-text-muted">
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-accent-500 mr-3" />
        Loading run...
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="py-16 text-center">
        <p className="text-danger">{error ?? "Run not found."}</p>
        <Link
          to="/runs"
          className="mt-3 inline-block text-sm text-accent-400 hover:text-accent-300"
        >
          Back to Runs
        </Link>
      </div>
    );
  }

  // ---------- Main layout ----------

  return (
    <div className="-mx-6 -my-8">
      {/* ── Status Bar ─────────────────────────────────────── */}
      <div className="border-b border-surface-700 bg-surface-800/60 px-6 py-3">
        <div className="mx-auto flex max-w-7xl items-center gap-4">
          {/* Back link */}
          <Link
            to="/runs"
            className="mr-1 rounded-md p-1 text-text-muted hover:text-text-primary hover:bg-surface-700 transition-colors"
            title="Back to Runs"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </Link>

          {/* Status badge */}
          <span
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${statusCfg.color} ${statusCfg.bgColor}`}
          >
            {statusCfg.pulse && (
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-50" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-current" />
              </span>
            )}
            {statusCfg.label}
          </span>

          {/* Run ID */}
          <span className="font-mono text-xs text-text-muted truncate max-w-[160px]">
            {run.id.slice(0, 8)}
          </span>

          {/* Duration */}
          <span className="text-xs text-text-secondary">
            {formatDuration(run.started_at, run.finished_at)}
          </span>

          {/* Steps count */}
          <span className="text-xs text-text-muted">
            {allSteps.length} step{allSteps.length !== 1 && "s"}
          </span>

          {/* WS indicator */}
          {shouldStream && (
            <span className="flex items-center gap-1 text-[10px] text-text-muted">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  wsStatus === "connected"
                    ? "bg-success"
                    : wsStatus === "connecting"
                      ? "bg-warning animate-pulse"
                      : "bg-surface-500"
                }`}
              />
              WS
            </span>
          )}

          {/* Spacer */}
          <div className="flex-1" />

          {/* Cancel button */}
          {isRunning && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="rounded-lg border border-danger/40 px-3 py-1.5 text-xs font-medium text-danger hover:bg-danger/10 disabled:opacity-50 transition-colors"
            >
              {cancelling ? "Cancelling..." : "Cancel Run"}
            </button>
          )}
        </div>
      </div>

      {/* ── Split Layout ────────────────────────────────────── */}
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-5 px-6 py-6 lg:grid-cols-[320px_1fr]">
        {/* ── Left Panel: Task Info ───────────────────────── */}
        <div className="space-y-4">
          {/* Task Card */}
          <div className="rounded-xl border border-surface-700 bg-surface-800 p-5">
            <h2 className="text-xs font-medium uppercase tracking-wider text-text-muted mb-3">
              Task
            </h2>
            <p className="text-sm font-semibold leading-snug">
              {task?.name ?? "Loading..."}
            </p>
            {task?.goal && (
              <p className="mt-2 text-xs leading-relaxed text-text-secondary">
                {task.goal}
              </p>
            )}

            {/* Platforms */}
            {task && task.platforms.length > 0 && (
              <div className="mt-4">
                <span className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
                  Platforms
                </span>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {task.platforms.map((p) => (
                    <span
                      key={p.id}
                      className="rounded-full bg-surface-700 px-2 py-0.5 text-[11px] font-medium text-text-secondary"
                    >
                      {p.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Constraints */}
            {task?.constraints &&
              Object.keys(task.constraints).length > 0 && (
                <div className="mt-4">
                  <span className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
                    Constraints
                  </span>
                  <div className="mt-1.5 space-y-1">
                    {Object.entries(task.constraints).map(([k, v]) => (
                      <div
                        key={k}
                        className="flex items-baseline gap-2 text-[11px]"
                      >
                        <span className="font-mono text-text-muted">{k}</span>
                        <span className="text-text-secondary">
                          {String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
          </div>

          {/* Agent Reasoning */}
          <AgentThinking text={latestReasoning} isLive={isRunning} />

          {/* Screenshot Viewer */}
          <ScreenshotViewer steps={allSteps} isRunning={isRunning} />

          {/* Final Answer / Error */}
          {(finalAnswer || liveError) && (
            <div
              className={`rounded-xl border p-5 ${
                liveError
                  ? "border-danger/30 bg-danger/5"
                  : "border-success/30 bg-success/5"
              }`}
            >
              <h2
                className={`text-xs font-medium uppercase tracking-wider mb-2 ${
                  liveError ? "text-danger" : "text-success"
                }`}
              >
                {liveError ? "Error" : "Final Answer"}
              </h2>
              <p className="text-xs leading-relaxed text-text-secondary whitespace-pre-wrap">
                {liveError ?? finalAnswer}
              </p>
            </div>
          )}
        </div>

        {/* ── Right Panel: Live Graph + Step Log ─────────── */}
        <div className="flex flex-col gap-5">
          {/* Graph Container */}
          <div
            className="relative overflow-hidden rounded-xl border border-surface-700 bg-surface-900"
            style={{ height: "520px" }}
          >
            {/* Graph title overlay */}
            <div className="absolute top-3 left-4 z-10 flex items-center gap-2">
              <span className="rounded-md bg-surface-800/80 px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest text-text-muted backdrop-blur-sm">
                Execution Trace
              </span>
            </div>
            <LiveGraph steps={allSteps} isRunning={isRunning} />
          </div>

          {/* Step Log Table */}
          <StepLogTable steps={allSteps} isRunning={isRunning} />
        </div>
      </div>
    </div>
  );
}
