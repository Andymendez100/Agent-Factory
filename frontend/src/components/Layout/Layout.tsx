import { NavLink, Outlet } from "react-router-dom";

const navLinks = [
  { to: "/platforms", label: "Platforms" },
  { to: "/tasks", label: "Tasks" },
  { to: "/runs", label: "Runs" },
];

export default function Layout() {
  return (
    <>
      <header className="border-b border-surface-700 bg-surface-800/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <NavLink
            to="/"
            className="flex items-center gap-2 text-lg font-semibold tracking-tight text-text-primary"
          >
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-accent-500 text-xs font-bold text-white">
              AF
            </span>
            Agent Factory
          </NavLink>

          <nav className="flex items-center gap-1">
            {navLinks.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-surface-700 text-text-primary"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-700/50"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <div className="mx-auto max-w-7xl px-6 py-8">
          <Outlet />
        </div>
      </main>
    </>
  );
}
