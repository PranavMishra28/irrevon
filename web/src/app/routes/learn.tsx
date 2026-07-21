import {
  Link,
  Outlet,
  createFileRoute,
  useNavigate,
  useRouterState,
} from "@tanstack/react-router";

export const Route = createFileRoute("/learn")({ component: LearnLayout });

const PAGES = [
  { to: "/learn/start", label: "Start here" },
  { to: "/learn/identity", label: "Identity" },
  { to: "/learn/state", label: "State model" },
  { to: "/learn/tiers", label: "Capability tiers" },
] as const;

function LearnLayout() {
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const active = PAGES.find((page) => pathname.startsWith(page.to))?.to ?? PAGES[0].to;

  return (
    <div>
      {/* ≥768: tab strip. <768: a labeled native menu — no mid-label wrapping. */}
      <nav
        aria-label="Learn pages"
        className="hidden items-center gap-1 border-b border-border-subtle bg-layer-nav px-6 min-[768px]:flex"
      >
        {PAGES.map((page) => (
          <Link
            key={page.to}
            to={page.to}
            className={
              "flex h-9 items-center border-b-2 border-transparent px-2.5 text-sm " +
              "whitespace-nowrap text-text-secondary hover:text-text-primary " +
              "data-[status=active]:border-(--color-accent) data-[status=active]:font-medium " +
              "data-[status=active]:text-text-primary"
            }
          >
            {page.label}
          </Link>
        ))}
      </nav>
      <div className="border-b border-border-subtle bg-layer-nav px-4 py-2 min-[768px]:hidden">
        <label className="flex items-center gap-2 text-sm text-text-secondary">
          <span className="font-mono text-2xs font-medium tracking-wide uppercase">
            Learn page
          </span>
          <select
            value={active}
            onChange={(event) => {
              void navigate({ to: event.target.value });
            }}
            className={
              "min-h-11 min-w-0 flex-1 rounded-(--radius-control) border border-border " +
              "bg-layer-panel px-2 text-sm text-text-primary"
            }
          >
            {PAGES.map((page) => (
              <option key={page.to} value={page.to}>
                {page.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Outlet />
    </div>
  );
}
