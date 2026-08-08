"use client";

import { useEffect, useState } from "react";

/**
 * JS-level `prefers-reduced-motion` read, for components that can't rely on
 * the global CSS override alone (e.g. canvas-based drawing, animation logic
 * gated in JS rather than a CSS transition/animation) — see
 * docs/design/Accessibility.md §1.
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);

    const listener = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener("change", listener);
    return () => query.removeEventListener("change", listener);
  }, []);

  return reduced;
}
