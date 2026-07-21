import {
  Link,
  Outlet,
  createRootRoute,
  useRouter,
  useRouterState,
} from "@tanstack/react-router";
import { Suspense, lazy, useEffect, useState } from "react";
import { isMockMode } from "@/app/data-mode";
import { useGlobalShortcuts } from "@/app/shortcuts";
import {
  getDensity,
  getTheme,
  setDensity,
  setTheme,
  type Density,
  type Theme,
} from "@/shared/lib/prefs";
import { AppFrame, DataModeBanner } from "@/shared/ui/layout/app-frame";
import { HelpCircle, Menu, Moon, Search, Sun } from "@/shared/ui/icons";
import { IconButton } from "@/shared/ui/primitives/button";

export const Route = createRootRoute({ component: RootLayout });

// Overlay surfaces are dynamic chunks: nothing dialog-shaped rides in the
// initial route JS (REDESIGN-BRIEF A3). They are idle-preloaded after mount
// so the first open is warm.
const Palette = lazy(() => import("@/app/palette").then((m) => ({ default: m.Palette })));
const ShortcutHelpDialog = lazy(() =>
  import("@/app/shortcut-help").then((m) => ({ default: m.ShortcutHelpDialog })),
);
const MobileNavDialog = lazy(() =>
  import("@/shared/ui/primitives/mobile-nav").then((m) => ({ default: m.MobileNavDialog })),
);

const NAV_ITEMS: readonly { to: string; label: string; matchPrefix?: string }[] = [
  { to: "/effects", label: "Effects" },
  { to: "/findings", label: "Findings" },
  { to: "/attention", label: "Attention" },
  { to: "/adapters", label: "Adapters" },
  { to: "/demo", label: "Demo" },
  { to: "/bench", label: "Benchmark" },
  { to: "/learn/start", label: "Learn", matchPrefix: "/learn" },
  { to: "/health", label: "Health" },
];

function NavLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      activeOptions={{ includeSearch: false }}
      className={
        "relative flex items-center border-b-2 border-transparent px-2.5 text-sm " +
        "text-text-secondary hover:text-text-primary " +
        "data-[status=active]:border-(--color-accent) data-[status=active]:font-medium " +
        "data-[status=active]:text-text-primary"
      }
      // /learn/start should stay active across all /learn/* pages
      activeProps={{ "data-status": "active", "aria-current": "page" }}
      inactiveProps={{}}
    >
      {label}
    </Link>
  );
}

/** 44px-minimum drawer row shared by nav links and utility controls. */
const DRAWER_ROW =
  "flex min-h-11 w-full items-center gap-3 px-4 text-left text-sm " +
  "text-text-secondary hover:bg-(--sys-state-hover) hover:text-text-primary";

function RootLayout() {
  const router = useRouter();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [overlaysRequested, setOverlaysRequested] = useState({
    palette: false,
    help: false,
    drawer: false,
  });
  const [theme, setThemeState] = useState<Theme>(() => getTheme());
  const [density, setDensityState] = useState<Density>(() => getDensity());

  const openPalette = () => {
    setOverlaysRequested((s) => (s.palette ? s : { ...s, palette: true }));
    setPaletteOpen(true);
  };
  const openHelp = () => {
    setOverlaysRequested((s) => (s.help ? s : { ...s, help: true }));
    setHelpOpen(true);
  };
  const openDrawer = () => {
    setOverlaysRequested((s) => (s.drawer ? s : { ...s, drawer: true }));
    setDrawerOpen(true);
  };

  useGlobalShortcuts({ onOpenPalette: openPalette, onOpenHelp: openHelp });

  // Warm the overlay chunks after first paint so the palette opens <50ms.
  useEffect(() => {
    const id = window.setTimeout(() => {
      void import("@/app/palette");
      void import("@/app/shortcut-help");
      void import("@/shared/ui/primitives/mobile-nav");
    }, 1200);
    return () => {
      clearTimeout(id);
    };
  }, []);

  // Full-page navigation moves focus to the route <h1 tabindex="-1">.
  // The initial resolve (including any landing redirect) must not steal
  // focus, so the skip link stays the first tab stop on load.
  useEffect(() => {
    let initialResolveSeen = false;
    return router.subscribe("onResolved", (event) => {
      if (!initialResolveSeen) {
        initialResolveSeen = true;
        return;
      }
      if (event.pathChanged) {
        requestAnimationFrame(() => {
          const heading = document.querySelector<HTMLElement>("[data-route-heading]");
          heading?.focus({ preventScroll: false });
        });
      }
    });
  }, [router]);

  const toggleTheme = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  };

  const toggleDensity = () => {
    const next: Density = density === "dense" ? "comfortable" : "dense";
    setDensity(next);
    setDensityState(next);
  };

  const activeItem = NAV_ITEMS.find((item) =>
    item.matchPrefix
      ? pathname.startsWith(item.matchPrefix)
      : pathname === item.to || pathname.startsWith(`${item.to}/`),
  );
  const viewLabel = activeItem?.label ?? (pathname === "/" ? "Overview" : "Detent");

  const themeLabel = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
  const densityLabel =
    density === "dense" ? "Switch to comfortable density" : "Switch to dense density";

  return (
    <AppFrame
      banner={
        isMockMode ? (
          <DataModeBanner>Synthetic fixture — not live or measured</DataModeBanner>
        ) : undefined
      }
      nav={NAV_ITEMS.map((item) => (
        <NavLink key={item.to} to={item.to} label={item.label} />
      ))}
      viewLabel={viewLabel}
      utilities={
        <>
          {/* Command trigger: labeled button ≥768, icon-only below. */}
          <button
            type="button"
            onClick={openPalette}
            className={
              "mr-1 hidden h-7 items-center gap-2 rounded-(--radius-control) border " +
              "border-border bg-layer-workspace px-2.5 text-xs text-text-tertiary " +
              "hover:border-border-strong hover:text-text-secondary min-[768px]:flex"
            }
          >
            <span>Go to…</span>
            <kbd className="font-mono text-2xs">⌘K</kbd>
          </button>
          <span className="min-[768px]:hidden">
            <IconButton label="Go to…" onClick={openPalette} className="size-11">
              <Search size={16} />
            </IconButton>
          </span>
          <span className="hidden items-center gap-1 min-[1120px]:flex">
            <IconButton label={densityLabel} onClick={toggleDensity}>
              <span aria-hidden className="font-mono text-xs font-medium">
                {density === "dense" ? "≡" : "☰"}
              </span>
            </IconButton>
            <IconButton label={themeLabel} onClick={toggleTheme}>
              {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
            </IconButton>
            {/* Consistent help: always the last item in the top bar on every view. */}
            <IconButton label="Help and keyboard shortcuts" onClick={openHelp}>
              <HelpCircle size={14} />
            </IconButton>
          </span>
          <span className="min-[1120px]:hidden">
            <IconButton
              label="Menu"
              onClick={openDrawer}
              aria-haspopup="dialog"
              aria-expanded={drawerOpen}
              className="size-11 min-[768px]:size-8"
            >
              <Menu size={16} />
            </IconButton>
          </span>
        </>
      }
    >
      <Outlet />
      {overlaysRequested.palette ? (
        <Suspense fallback={null}>
          <Palette open={paletteOpen} onOpenChange={setPaletteOpen} />
        </Suspense>
      ) : null}
      {overlaysRequested.help ? (
        <Suspense fallback={null}>
          <ShortcutHelpDialog open={helpOpen} onOpenChange={setHelpOpen} />
        </Suspense>
      ) : null}
      {overlaysRequested.drawer ? (
        <Suspense fallback={null}>
          <MobileNavDialog open={drawerOpen} onOpenChange={setDrawerOpen}>
            <nav aria-label="Views">
              <ul>
                {NAV_ITEMS.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      activeOptions={{ includeSearch: false }}
                      onClick={() => {
                        setDrawerOpen(false);
                      }}
                      className={
                        DRAWER_ROW +
                        " data-[status=active]:border-l-2 data-[status=active]:border-(--color-accent)" +
                        " data-[status=active]:font-medium data-[status=active]:text-text-primary"
                      }
                      activeProps={{ "data-status": "active", "aria-current": "page" }}
                      inactiveProps={{}}
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
            <div className="mt-2 flex flex-col border-t border-border-subtle pt-2">
              <button type="button" onClick={toggleDensity} className={DRAWER_ROW}>
                <span aria-hidden className="w-4 text-center font-mono text-xs font-medium">
                  {density === "dense" ? "≡" : "☰"}
                </span>
                {densityLabel}
              </button>
              <button type="button" onClick={toggleTheme} className={DRAWER_ROW}>
                <span aria-hidden className="flex w-4 justify-center">
                  {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
                </span>
                {themeLabel}
              </button>
              <button
                type="button"
                onClick={() => {
                  setDrawerOpen(false);
                  openHelp();
                }}
                className={DRAWER_ROW}
              >
                <span aria-hidden className="flex w-4 justify-center">
                  <HelpCircle size={14} />
                </span>
                Help and keyboard shortcuts
              </button>
            </div>
          </MobileNavDialog>
        </Suspense>
      ) : null}
    </AppFrame>
  );
}
