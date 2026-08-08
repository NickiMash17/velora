import { cn } from "@/lib/utils";

const COLS_CLASSES = {
  1: "grid-cols-1",
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
  4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
} as const;

const GAP_CLASSES = {
  2: "gap-2",
  4: "gap-4",
  6: "gap-6",
} as const;

/**
 * CSS grid + a responsive column count — for card grids (a future roster,
 * a Goals board) that should collapse to fewer columns on narrower
 * viewports rather than being force-fit (docs/design/Accessibility.md §3).
 */
function Grid({
  cols = 3,
  gap = 4,
  className,
  ...props
}: React.ComponentProps<"div"> & { cols?: keyof typeof COLS_CLASSES; gap?: keyof typeof GAP_CLASSES }) {
  return <div className={cn("grid", COLS_CLASSES[cols], GAP_CLASSES[gap], className)} {...props} />;
}

export { Grid };
