import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ProductIcon, type ProductIconName } from "./ProductIcons";
import { ParseLogo } from "./UI";

const links: ReadonlyArray<[string, string, ProductIconName]> = [
  ["/", "Overview", "overview"],
  ["/documents", "Documents", "documents"],
  ["/processors", "Processors", "processors"],
  ["/workflows", "Workflows", "workflows"],
  ["/developer", "API", "api"],
  ["/settings", "Settings", "settings"],
];

export function AppShell() {
  const { user, workspaceId, switchWorkspace, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-paper pb-16 md:pb-0">
      <header className="sticky top-0 z-30 border-b border-line bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1480px] items-center px-4 md:px-7">
          <div className="flex w-28 shrink-0 items-center md:w-40">
            <ParseLogo />
          </div>

          <nav
            className="hidden h-full flex-1 items-center gap-7 md:flex"
            aria-label="Primary navigation"
          >
            {links.map(([to, label, icon]) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `group relative flex h-full items-center gap-2 text-[13px] font-medium transition-colors ${isActive ? "text-ink" : "text-ink-soft hover:text-ink"}`
                }
              >
                {({ isActive }) => (
                  <>
                    <ProductIcon
                      name={icon}
                      size={16}
                      className={isActive ? "text-brand" : ""}
                    />
                    <span>{label}</span>
                    {isActive && (
                      <span className="motion-underline absolute inset-x-0 bottom-0 h-[2px] bg-brand" />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2.5">
            <div className="relative hidden lg:block">
              <select
                aria-label="Workspace"
                value={workspaceId || ""}
                onChange={(e) => switchWorkspace(e.target.value)}
                className="max-w-44 appearance-none border-0 bg-transparent py-2 pl-2 pr-7 text-[12px] font-medium text-ink focus:ring-0"
              >
                {user?.workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </option>
                ))}
              </select>
              <ProductIcon
                name="chevron"
                size={14}
                className="pointer-events-none absolute right-1.5 top-2.5 text-ink-soft"
              />
            </div>
            <span className="hidden h-5 w-px bg-line lg:block" />
            <button
              className="btn-primary min-h-9 px-3.5 py-1.5"
              onClick={() => navigate("/documents/new")}
            >
              <ProductIcon name="upload" size={15} />
              <span className="hidden sm:inline">Upload</span>
            </button>
            <div className="hidden max-w-32 xl:block">
              <div className="truncate text-[12px] font-medium text-ink">
                {user?.display_name}
              </div>
              <div className="truncate text-[10px] text-ink-soft">
                {user?.email}
              </div>
            </div>
            <button
              aria-label="Log out"
              title="Log out"
              className="btn-icon"
              onClick={() => void logout()}
            >
              <ProductIcon name="logout" size={17} />
            </button>
          </div>
        </div>
      </header>

      <main className="px-4 py-7 md:px-8 md:py-10">
        <Outlet />
      </main>

      <nav
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-6 border-t border-line bg-white/95 px-1 pb-[max(.35rem,env(safe-area-inset-bottom))] pt-1.5 backdrop-blur-xl md:hidden"
        aria-label="Mobile navigation"
      >
        {links.map(([to, label, icon]) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex min-w-0 flex-col items-center gap-1 rounded-sm py-1 text-[9px] ${isActive ? "text-brand-strong" : "text-ink-soft"}`
            }
          >
            <ProductIcon name={icon} size={17} />
            <span className="max-w-full truncate">{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
