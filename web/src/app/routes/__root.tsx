import { Link, Outlet, createRootRoute, useRouter } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { isMockMode } from "@/app/data-mode";
import { Palette } from "@/app/palette";
import { ShortcutHelpDialog, useGlobalShortcuts } from "@/app/shortcuts";
import {
  getDensity,
  getTheme,
  setDensity,
  setTheme,
  type Density,
  type Theme,
} from "@/shared/lib/prefs";
import { AppFrame, DataModeBanner } from "@/shared/ui/layout/app-frame";
import { HelpCircle, Moon, Sun } from "@/shared/ui/icons";
import { IconButton } from "@/shared/ui/primitives/button";

export const Route = createRootRoute({ component: RootLayout });

const NAV_ITEMS: readonly { to: string; label: string }[] = [
  { to: "/effects", label: "Effects" },
  { to: "/findings", label: "Findings" },
  { to: "/attention", label: "Attention" },
  { to: "/adapters", label: "Adapters" },
  { to: "/bench", label: "Benchmark" },
  { to: "/demo", label: "Demo" },
  { to: "/learn/start", label: "Learn" },
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
      activeProps={{ "data-status": "active" }}
      inactiveProps={{}}
    >
      {label}
    </Link>
  );
}

function RootLayout() {
  const router = useRouter();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [theme, setThemeState] = useState<Theme>(() => getTheme());
  const [density, setDensityState] = useState<Density>(() => getDensity());

  useGlobalShortcuts({
    onOpenPalette: () => {
      setPaletteOpen(true);
    },
    onOpenHelp: () => {
      setHelpOpen(true);
    },
  });

  // Full-page navigation moves focus to the route <h1 tabindex="-1">.
  // The initial resolve (including the landing redirect) must not steal
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
      utilities={
        <>
          <button
            type="button"
            onClick={() => {
              setPaletteOpen(true);
            }}
            className={
              "mr-1 flex h-7 items-center gap-2 rounded-(--radius-control) border " +
              "border-border bg-surface-2 px-2.5 text-xs text-text-tertiary " +
              "hover:border-border-strong hover:text-text-secondary"
            }
          >
            <span>Go to…</span>
            <kbd className="font-mono text-2xs">⌘K</kbd>
          </button>
          <IconButton
            label={
              density === "dense" ? "Switch to comfortable density" : "Switch to dense density"
            }
            onClick={toggleDensity}
          >
            <span aria-hidden className="font-mono text-xs font-medium">
              {density === "dense" ? "≡" : "☰"}
            </span>
          </IconButton>
          <IconButton
            label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            onClick={toggleTheme}
          >
            {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
          </IconButton>
          {/* Consistent help: always the last item in the top bar on every view. */}
          <IconButton
            label="Help and keyboard shortcuts"
            onClick={() => {
              setHelpOpen(true);
            }}
          >
            <HelpCircle size={14} />
          </IconButton>
        </>
      }
    >
      <Outlet />
      <Palette open={paletteOpen} onOpenChange={setPaletteOpen} />
      <ShortcutHelpDialog open={helpOpen} onOpenChange={setHelpOpen} />
    </AppFrame>
  );
}
