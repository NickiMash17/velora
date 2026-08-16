import { cn } from "@/lib/utils";

type LiveDotStatus = "idle" | "live" | "drift";

const STATUS_LABEL: Record<LiveDotStatus, string> = {
  idle: "idle",
  live: "actively working",
  drift: "idle, Company DNA behind current",
};

/**
 * The instrumentation-not-illustration status dot (docs/design/
 * DesignSystem.md §3.1) — idle (solid, neutral), live (Signal, pulsing —
 * the one deliberate ambient-motion exception, §9), or drift (muted,
 * dashed ring — Company DNA behind the org's published version,
 * docs/design/UXPrinciples.md §7). Color is reinforced by the accessible
 * label text, never the only signal (docs/design/Accessibility.md §2).
 * First real consumer: the Meridian Line (shell/meridian-line.tsx).
 */
function LiveDot({
  status,
  label,
  className,
}: {
  status: LiveDotStatus;
  label?: string;
  className?: string;
}) {
  return (
    <span
      role="img"
      aria-label={label ?? STATUS_LABEL[status]}
      className={cn(
        "inline-block size-1.5 shrink-0 rounded-full",
        status === "idle" && "bg-sage",
        status === "live" && "animate-meridian-pulse bg-signal",
        status === "drift" && "border border-dashed border-muted-foreground bg-transparent",
        className
      )}
    />
  );
}

export { LiveDot };
export type { LiveDotStatus };
