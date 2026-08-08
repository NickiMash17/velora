import { cn } from "@/lib/utils";

/**
 * Generic empty-state scaffold — docs/design/UXPrinciples.md §1: "an empty
 * state is a promise, not an apology." Where a specific signature molecule
 * has its own dormant treatment (a Digital Employee Card silhouette, a
 * Goal Progress Ring at 0%), prefer that over this generic primitive —
 * this exists for the cases that don't have one yet. No decorative
 * illustration; an optional icon slot, plain language, an optional action.
 */
function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl border border-dashed border-border px-6 py-12 text-center",
        className
      )}
    >
      {icon && <div className="text-muted-foreground">{icon}</div>}
      <div className="flex flex-col gap-1">
        <p className="text-h3 font-semibold tracking-tight">{title}</p>
        {description && <p className="text-small text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export { EmptyState };
