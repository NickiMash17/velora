import { cn } from "@/lib/utils";

/**
 * A loading placeholder matching the *shape* of the real content it stands
 * in for — never a generic spinner for anything with a known shape
 * (docs/design/UXPrinciples.md §2). `animate-pulse` is neutralized globally
 * under `prefers-reduced-motion` (globals.css).
 */
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  );
}

export { Skeleton };
