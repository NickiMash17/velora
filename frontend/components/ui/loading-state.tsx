import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * The "waiting on a network request, shape unknown" loading state
 * (docs/design/UXPrinciples.md §2, category 1) — deliberately a neutral,
 * muted indicator, never the Signal-colored pulse reserved for "a Digital
 * Employee is actively reasoning" (category 2, see LiveDot). Replaces the
 * identical `text-sm text-muted-foreground` "Loading…" paragraph previously
 * duplicated across AuthGuard, SessionResolver, and DashboardShell.
 */
function LoadingState({
  label = "Loading…",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-2 text-small text-muted-foreground", className)}>
      <Loader2 className="size-3.5 shrink-0 animate-spin" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export { LoadingState };
