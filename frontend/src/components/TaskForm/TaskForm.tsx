import { useEffect, useState } from "react";
import type { AgentTask, Platform } from "../../types";
import type { TaskCreatePayload } from "../../api/client";
import { fetchPlatforms } from "../../api/client";

interface Props {
  /** Task to edit, or null for create mode. */
  task: AgentTask | null;
  onSubmit: (data: TaskCreatePayload) => void;
  onClose: () => void;
  isSubmitting: boolean;
}

interface ConstraintRow {
  key: string;
  value: string;
}

const EMPTY_FORM: TaskCreatePayload = {
  name: "",
  goal: "",
  platform_ids: [],
  constraints: null,
};

export default function TaskForm({
  task,
  onSubmit,
  onClose,
  isSubmitting,
}: Props) {
  const [form, setForm] = useState<TaskCreatePayload>(EMPTY_FORM);
  const [constraints, setConstraints] = useState<ConstraintRow[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [loadingPlatforms, setLoadingPlatforms] = useState(true);
  const isEdit = task !== null;

  // Load available platforms for multi-select
  useEffect(() => {
    fetchPlatforms()
      .then(setPlatforms)
      .catch(() => setPlatforms([]))
      .finally(() => setLoadingPlatforms(false));
  }, []);

  // Populate form when editing
  useEffect(() => {
    if (task) {
      setForm({
        name: task.name,
        goal: task.goal,
        platform_ids: task.platforms.map((p) => p.id),
        constraints: task.constraints,
      });
      // Convert constraints object to key-value rows
      if (task.constraints && Object.keys(task.constraints).length > 0) {
        setConstraints(
          Object.entries(task.constraints).map(([key, value]) => ({
            key,
            value: String(value),
          })),
        );
      } else {
        setConstraints([]);
      }
    } else {
      setForm(EMPTY_FORM);
      setConstraints([]);
    }
  }, [task]);

  function handleChange(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function togglePlatform(platformId: string) {
    setForm((prev) => {
      const ids = prev.platform_ids.includes(platformId)
        ? prev.platform_ids.filter((id) => id !== platformId)
        : [...prev.platform_ids, platformId];
      return { ...prev, platform_ids: ids };
    });
  }

  function addConstraint() {
    setConstraints((prev) => [...prev, { key: "", value: "" }]);
  }

  function updateConstraint(
    index: number,
    field: "key" | "value",
    value: string,
  ) {
    setConstraints((prev) =>
      prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)),
    );
  }

  function removeConstraint(index: number) {
    setConstraints((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // Build constraints object from key-value rows
    const constraintsObj: Record<string, unknown> = {};
    for (const row of constraints) {
      if (row.key.trim()) {
        // Try to parse numeric values
        const num = Number(row.value);
        constraintsObj[row.key.trim()] = isNaN(num) ? row.value : num;
      }
    }
    onSubmit({
      ...form,
      constraints:
        Object.keys(constraintsObj).length > 0 ? constraintsObj : null,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-surface-600 bg-surface-800 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-700 px-6 py-4">
          <h2 className="text-lg font-semibold">
            {isEdit ? "Edit Task" : "Create Task"}
          </h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-text-muted hover:bg-surface-700 hover:text-text-primary transition-colors"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          {/* Name */}
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-text-secondary">
              Name
            </label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => handleChange("name", e.target.value)}
              placeholder="e.g. Check Active Time — Maria Santos"
              className="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
            />
          </div>

          {/* Goal */}
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-text-secondary">
              Goal
            </label>
            <textarea
              required
              rows={3}
              value={form.goal}
              onChange={(e) => handleChange("goal", e.target.value)}
              placeholder="Describe what the agent should accomplish..."
              className="w-full resize-y rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
            />
          </div>

          {/* Platform Multi-select */}
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-text-secondary">
              Platforms
            </label>
            {loadingPlatforms ? (
              <p className="text-xs text-text-muted">Loading platforms...</p>
            ) : platforms.length === 0 ? (
              <p className="text-xs text-text-muted">
                No platforms available. Create one first.
              </p>
            ) : (
              <div className="space-y-1.5">
                {platforms.map((p) => {
                  const selected = form.platform_ids.includes(p.id);
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => togglePlatform(p.id)}
                      className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                        selected
                          ? "border-accent-500 bg-accent-500/10 text-text-primary"
                          : "border-surface-600 bg-surface-700 text-text-secondary hover:border-surface-500 hover:text-text-primary"
                      }`}
                    >
                      <span
                        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                          selected
                            ? "border-accent-500 bg-accent-500"
                            : "border-surface-500"
                        }`}
                      >
                        {selected && (
                          <svg
                            className="h-3 w-3 text-white"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={3}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        )}
                      </span>
                      <span className="font-medium">{p.name}</span>
                      <span className="ml-auto font-mono text-xs text-text-muted">
                        {p.base_url}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Constraints (dynamic key-value) */}
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label className="block text-xs font-medium uppercase tracking-wider text-text-secondary">
                Constraints
              </label>
              <button
                type="button"
                onClick={addConstraint}
                className="text-xs font-medium text-accent-400 hover:text-accent-300 transition-colors"
              >
                + Add
              </button>
            </div>
            {constraints.length === 0 ? (
              <p className="text-xs text-text-muted">
                No constraints. Click "+ Add" to define key-value pairs.
              </p>
            ) : (
              <div className="space-y-2">
                {constraints.map((row, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={row.key}
                      onChange={(e) =>
                        updateConstraint(i, "key", e.target.value)
                      }
                      placeholder="Key"
                      className="w-2/5 rounded-lg border border-surface-600 bg-surface-700 px-3 py-1.5 text-xs font-mono text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
                    />
                    <input
                      type="text"
                      value={row.value}
                      onChange={(e) =>
                        updateConstraint(i, "value", e.target.value)
                      }
                      placeholder="Value"
                      className="flex-1 rounded-lg border border-surface-600 bg-surface-700 px-3 py-1.5 text-xs font-mono text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
                    />
                    <button
                      type="button"
                      onClick={() => removeConstraint(i)}
                      className="rounded-md p-1 text-text-muted hover:text-danger transition-colors"
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
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 border-t border-surface-700 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-surface-600 px-4 py-2 text-sm font-medium text-text-secondary hover:bg-surface-700 hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || form.platform_ids.length === 0}
              className="rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50 transition-colors"
            >
              {isSubmitting
                ? "Saving..."
                : isEdit
                  ? "Update Task"
                  : "Create Task"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
