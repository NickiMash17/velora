import { cn } from "@/lib/utils";

const GAP_CLASSES = {
  1: "gap-1",
  2: "gap-2",
  3: "gap-3",
  4: "gap-4",
  6: "gap-6",
  8: "gap-8",
} as const;

/**
 * Vertical flex + gap — the default way to stack related elements
 * (docs/design/DesignSystem.md §6's spacing scale). Thin on purpose; see
 * docs/design/Stage0-Migration.md §11 for the layout-primitives rationale.
 */
function Stack({
  gap = 4,
  className,
  ...props
}: React.ComponentProps<"div"> & { gap?: keyof typeof GAP_CLASSES }) {
  return <div className={cn("flex flex-col", GAP_CLASSES[gap], className)} {...props} />;
}

export { Stack };
