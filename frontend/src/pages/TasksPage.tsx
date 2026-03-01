import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { AgentTask } from "../types";
import type { TaskCreatePayload } from "../api/client";
import {
  fetchTasks,
  createTask,
  updateTask,
  deleteTask,
  triggerRun,
} from "../api/client";
import TaskForm from "../components/TaskForm/TaskForm";

export default function TasksPage() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form modal state
  const [showForm, setShowForm] = useState(false);
  const [editTarget, setEditTarget] = useState<AgentTask | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<AgentTask | null>(null);

  // Run-in-progress tracker (task id)
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchTasks();
      setTasks(data);
    } catch {
      setError("Failed to load tasks.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Create / Update
  async function handleSubmit(data: TaskCreatePayload) {
    setSubmitting(true);
    try {
      if (editTarget) {
        await updateTask(editTarget.id, data);
      } else {
        await createTask(data);
      }
      setShowForm(false);
      setEditTarget(null);
      await load();
    } catch {
      setError("Failed to save task.");
    } finally {
      setSubmitting(false);
    }
  }

  // Delete
  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteTask(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch {
      setError("Failed to delete task.");
    }
  }

  // Run
  async function handleRun(taskId: string) {
    setRunningTaskId(taskId);
    try {
      const run = await triggerRun(taskId);
      navigate(`/runs/${run.id}`);
    } catch {
      setError("Failed to start run.");
      setRunningTaskId(null);
    }
  }

  function openCreate() {
    setEditTarget(null);
    setShowForm(true);
  }

  function openEdit(t: AgentTask) {
    setEditTarget(t);
    setShowForm(true);
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function truncate(text: string, max: number) {
    return text.length > max ? text.slice(0, max) + "..." : text;
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tasks</h1>
          <p className="mt-1 text-text-secondary">
            Define agent goals and select which platforms to use.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400 transition-colors"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 4v16m8-8H4"
            />
          </svg>
          Create Task
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
            Loading tasks...
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-text-muted">
            <p className="text-sm">No tasks defined yet.</p>
            <button
              onClick={openCreate}
              className="mt-3 text-sm font-medium text-accent-400 hover:text-accent-300"
            >
              Create your first task
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-700 text-left">
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-wider text-text-muted">
                  Name
                </th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-wider text-text-muted">
                  Goal
                </th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-wider text-text-muted">
                  Platforms
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
              {tasks.map((t) => (
                <tr
                  key={t.id}
                  className="hover:bg-surface-700/40 transition-colors"
                >
                  <td className="px-5 py-3 font-medium">{t.name}</td>
                  <td className="px-5 py-3 text-text-secondary">
                    {truncate(t.goal, 60)}
                  </td>
                  <td className="px-5 py-3">
                    {t.platforms.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {t.platforms.map((p) => (
                          <span
                            key={p.id}
                            className="inline-block rounded-full bg-surface-600 px-2 py-0.5 text-xs font-medium text-text-secondary"
                          >
                            {p.name}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-text-muted">None</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-text-secondary">
                    {formatDate(t.created_at)}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => handleRun(t.id)}
                      disabled={runningTaskId === t.id}
                      className="mr-2 rounded-md bg-success/15 px-2.5 py-1 text-xs font-medium text-success hover:bg-success/25 disabled:opacity-50 transition-colors"
                    >
                      {runningTaskId === t.id ? "Starting..." : "Run"}
                    </button>
                    <button
                      onClick={() => openEdit(t)}
                      className="mr-2 rounded-md px-2.5 py-1 text-xs font-medium text-text-secondary hover:bg-surface-600 hover:text-text-primary transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => setDeleteTarget(t)}
                      className="rounded-md px-2.5 py-1 text-xs font-medium text-danger/80 hover:bg-danger/10 hover:text-danger transition-colors"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Form Modal */}
      {showForm && (
        <TaskForm
          task={editTarget}
          onSubmit={handleSubmit}
          onClose={() => {
            setShowForm(false);
            setEditTarget(null);
          }}
          isSubmitting={submitting}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-xl border border-surface-600 bg-surface-800 p-6 shadow-2xl">
            <h3 className="text-lg font-semibold">Delete Task</h3>
            <p className="mt-2 text-sm text-text-secondary">
              Are you sure you want to delete{" "}
              <span className="font-medium text-text-primary">
                {deleteTarget.name}
              </span>
              ? This action cannot be undone.
            </p>
            <div className="mt-5 flex justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="rounded-lg border border-surface-600 px-4 py-2 text-sm font-medium text-text-secondary hover:bg-surface-700 hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="rounded-lg bg-danger px-4 py-2 text-sm font-medium text-white hover:bg-danger/80 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
