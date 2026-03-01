import { useEffect, useState } from "react";
import type { Platform } from "../../types";
import type { PlatformCreatePayload } from "../../api/client";

interface Props {
  /** Platform to edit, or null for create mode. */
  platform: Platform | null;
  onSubmit: (data: PlatformCreatePayload) => void;
  onClose: () => void;
  isSubmitting: boolean;
}

const EMPTY_FORM: PlatformCreatePayload = {
  name: "",
  base_url: "",
  login_url: "",
  credentials: { username: "", password: "" },
  login_selectors: {
    username_field: "",
    password_field: "",
    submit_button: "",
  },
};

export default function PlatformForm({
  platform,
  onSubmit,
  onClose,
  isSubmitting,
}: Props) {
  const [form, setForm] = useState<PlatformCreatePayload>(EMPTY_FORM);
  const isEdit = platform !== null;

  useEffect(() => {
    if (platform) {
      setForm({
        name: platform.name,
        base_url: platform.base_url,
        login_url: platform.login_url,
        credentials: { username: "", password: "" },
        login_selectors: {
          username_field: platform.login_selectors.username_field ?? "",
          password_field: platform.login_selectors.password_field ?? "",
          submit_button: platform.login_selectors.submit_button ?? "",
        },
      });
    } else {
      setForm(EMPTY_FORM);
    }
  }, [platform]);

  function handleChange(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleCredentialChange(field: string, value: string) {
    setForm((prev) => ({
      ...prev,
      credentials: { ...prev.credentials, [field]: value },
    }));
  }

  function handleSelectorChange(field: string, value: string) {
    setForm((prev) => ({
      ...prev,
      login_selectors: { ...prev.login_selectors, [field]: value },
    }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(form);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-surface-600 bg-surface-800 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-700 px-6 py-4">
          <h2 className="text-lg font-semibold">
            {isEdit ? "Edit Platform" : "Add Platform"}
          </h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-text-muted hover:bg-surface-700 hover:text-text-primary transition-colors"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
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
              placeholder="e.g. BPO Employee Portal"
              className="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
            />
          </div>

          {/* URLs */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-text-secondary">
                Base URL
              </label>
              <input
                type="url"
                required
                value={form.base_url}
                onChange={(e) => handleChange("base_url", e.target.value)}
                placeholder="https://portal.example.com"
                className="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-text-secondary">
                Login URL
              </label>
              <input
                type="url"
                required
                value={form.login_url}
                onChange={(e) => handleChange("login_url", e.target.value)}
                placeholder="https://portal.example.com/login"
                className="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
              />
            </div>
          </div>

          {/* Credentials */}
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-text-secondary">
              Credentials {isEdit && "(leave blank to keep existing)"}
            </label>
            <div className="grid grid-cols-2 gap-3">
              <input
                type="text"
                required={!isEdit}
                value={form.credentials.username}
                onChange={(e) =>
                  handleCredentialChange("username", e.target.value)
                }
                placeholder="Username"
                className="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
              />
              <input
                type="password"
                required={!isEdit}
                value={form.credentials.password}
                onChange={(e) =>
                  handleCredentialChange("password", e.target.value)
                }
                placeholder="Password"
                className="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
              />
            </div>
          </div>

          {/* Login Selectors */}
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-text-secondary">
              Login CSS Selectors
            </label>
            <div className="grid grid-cols-3 gap-3">
              <input
                type="text"
                value={form.login_selectors.username_field ?? ""}
                onChange={(e) =>
                  handleSelectorChange("username_field", e.target.value)
                }
                placeholder="#username"
                className="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-xs font-mono text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
              />
              <input
                type="text"
                value={form.login_selectors.password_field ?? ""}
                onChange={(e) =>
                  handleSelectorChange("password_field", e.target.value)
                }
                placeholder="#password"
                className="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-xs font-mono text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
              />
              <input
                type="text"
                value={form.login_selectors.submit_button ?? ""}
                onChange={(e) =>
                  handleSelectorChange("submit_button", e.target.value)
                }
                placeholder="button[type='submit']"
                className="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-xs font-mono text-text-primary placeholder:text-text-muted focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
              />
            </div>
            <p className="mt-1 text-xs text-text-muted">
              CSS selectors for the username field, password field, and submit
              button on the login page.
            </p>
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
              disabled={isSubmitting}
              className="rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50 transition-colors"
            >
              {isSubmitting
                ? "Saving..."
                : isEdit
                  ? "Update Platform"
                  : "Create Platform"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
