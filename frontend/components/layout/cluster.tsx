import { cn } from "@/lib/utils";

const GAP_CLASSES = {
  1: "gap-1",
  2: "gap-2",
  3: "gap-3",
  4: "gap-4",
  6: "gap-6",
} as const;

/**
 * Wrapping horizontal flex + gap — for a row of same-purpose elements
 * (badges, actions, filter chips) that should reflow rather than overflow.
 */
function Cluster({
  gap = 2,
  align = "center",
  className,
  ...props
}: React.ComponentProps<"div"> & {
  gap?: keyof typeof GAP_CLASSES;
  align?: "start" | "center" | "end";
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap",
        align === "start" && "items-start",
        align === "center" && "items-center",
        align === "end" && "items-end",
        GAP_CLASSES[gap],
        className
      )}
      {...props}
    />
  );
}

export { Cluster };
