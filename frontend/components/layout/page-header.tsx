import { cn } from "@/lib/utils";

/**
 * An in-content page header — title, optional description, optional
 * actions on the right (docs/design/Wireframes.md §6's "Goals ·
 * [+ New Goal]" pattern). Distinct from the shell's own `Header`
 * (components/shell/header.tsx), which is persistent chrome around the
 * whole authenticated app, not a per-page title.
 */
function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-4", className)}>
      <div className="flex flex-col gap-1">
        <h2 className="text-h2 font-semibold tracking-tight">{title}</h2>
        {description && <p className="text-small text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export { PageHeader };
