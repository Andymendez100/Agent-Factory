import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { AgentRun, RunStatus } from "../types";
import { fetchRuns } from "../api/client";

const STATUS_STYLES: Record<
  RunStatus,
  { label: string; color: string; bg: string }
> = {
  pending: { label: "Pending", color: "text-warning", bg: "bg-warning/15" },
  running: {
    label: "Running",
    color: "text-accent-400",
    bg: "bg-accent-500/15",
  },
  completed: { label: "Completed", color: "text-success", bg: "bg-success/15" },
  failed: { label: "Failed", color: "text-danger", bg: "bg-danger/15" },
  cancelled: {
    label: "Cancelled",
    color: "text-text-muted",
    bg: "bg-surface-600/50",
  },
};

export default function RunsPage() {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchRuns();
      setRuns(data);
    } catch {
      setError("Failed to load runs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatDuration(start: string | null, end: string | null): string {
    if (!start) return "--";
    const s = new Date(start).getTime();
    const e = end ? new Date(end).getTime() : Date.now();
    const sec = Math.floor((e - s) / 1000);
    if (sec < 60) return `${sec}s`;
    return `${Math.floor(sec / 60)}m ${sec % 60}s`;
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
          <p className="mt-1 text-text-secondary">
            View past and in-progress agent execution runs.
          </p>
        </div>
        <button
          onClick={load}
          className="rounded-lg border border-surface-600 px-3 py-2 text-sm font-medium text-text-secondary hover:bg-surface-700 hover:text-text-primary transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mt-4 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 underline hover:no-underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Table */}
      <div className="mt-6 overflow-hidden rounded-xl border border-surface-700 bg-surface-800">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-text-muted">
            Loading runs...
          </div>
        ) : runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-text-muted">
            <p className="text-sm">No runs yet.</p>
            <Link
              to="/tasks"
              className="mt-3 text-sm font-medium text-accent-400 hover:text-accent-300"
            >
              Go to Tasks to start a run
            </Link>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-700 text-left">
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-wider text-text-muted">
                  Status
                </th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-wider text-text-muted">
                  Run ID
                </th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-wider text-text-muted">
                  Steps
                </th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-wider text-text-muted">
                  Duration
                </th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-wider text-text-muted">
                  Created
                </th>
                <th className="px-5 py-3 text-right text-xs font-medium uppercase tracking-wider text-text-muted">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700">
              {runs.map((r) => {
                const st =
                  STATUS_STYLES[r.status as RunStatus] ?? STATUS_STYLES.pending;
                return (
                  <tr
                    key={r.id}
                    className="hover:bg-surface-700/40 transition-colors"
                  >
                    <td className="px-5 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-bold ${st.color} ${st.bg}`}
                      >
                        {(r.status === "running" ||
                          r.status === "pending") && (
                          <span className="relative flex h-1.5 w-1.5">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-50" />
                            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
                          </span>
                        )}
                        {st.label}
                      </span>
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-text-secondary">
                      {r.id.slice(0, 8)}
                    </td>
                    <td className="px-5 py-3 text-text-secondary">
                      {r.steps.length} step{r.steps.length !== 1 && "s"}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-text-secondary">
                      {formatDuration(r.started_at, r.finished_at)}
                    </td>
                    <td className="px-5 py-3 text-text-secondary">
                      {formatDate(r.created_at)}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Link
                        to={`/runs/${r.id}`}
                        className="rounded-md px-2.5 py-1 text-xs font-medium text-accent-400 hover:bg-accent-500/10 transition-colors"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
