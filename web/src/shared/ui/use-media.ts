import { useEffect, useState } from "react";

/** Subscribe to a media query; SSR-free app, so window is always present. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };
    setMatches(mql.matches);
    mql.addEventListener("change", onChange);
    return () => {
      mql.removeEventListener("change", onChange);
    };
  }, [query]);
  return matches;
}
