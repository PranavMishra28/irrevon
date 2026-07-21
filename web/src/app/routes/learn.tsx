import { Link, Outlet, createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/learn")({ component: LearnLayout });

const PAGES = [
  { to: "/learn/start", label: "Start here" },
  { to: "/learn/identity", label: "Identity" },
  { to: "/learn/state", label: "State model" },
  { to: "/learn/tiers", label: "Capability tiers" },
] as const;

function LearnLayout() {
  return (
    <div>
      <nav
        aria-label="Learn pages"
        className="flex items-center gap-1 border-b border-border-subtle bg-surface-1 px-6"
      >
        {PAGES.map((page) => (
          <Link
            key={page.to}
            to={page.to}
            className={
              "flex h-9 items-center border-b-2 border-transparent px-2.5 text-sm " +
              "text-text-secondary hover:text-text-primary " +
              "data-[status=active]:border-(--color-accent) data-[status=active]:font-medium " +
              "data-[status=active]:text-text-primary"
            }
          >
            {page.label}
          </Link>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
