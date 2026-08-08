import { Avatar } from "@/components/ui/avatar";
import { Badge, type badgeVariants } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { VariantProps } from "class-variance-authority";

type DigitalEmployeeStatus = "draft" | "configured" | "active" | "paused" | "retired";

const STATUS_VARIANT: Record<DigitalEmployeeStatus, NonNullable<VariantProps<typeof badgeVariants>["variant"]>> = {
  draft: "neutral",
  configured: "neutral",
  active: "success",
  paused: "info",
  retired: "neutral",
};

/**
 * A roster tile: avatar mark, name, role title, department, a
 * single-word lifecycle status, and one live metric — never both
 * (docs/design/ComponentGuidelines.md §3). Presentation-only: no Digital
 * Employee backend exists in M4. First real consumer: the Digital
 * Employees roster, a future milestone — this component just needs real
 * data passed into these same props then.
 */
function DigitalEmployeeCard({
  name,
  roleTitle,
  department,
  status,
  metric,
  className,
}: {
  name: string;
  roleTitle: string;
  department: string;
  status: DigitalEmployeeStatus;
  metric?: { label: string; value: string };
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-xl border border-border bg-card p-4",
        className
      )}
    >
      <Avatar label={name} tone={status === "active" ? "signal" : "neutral"} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-small font-semibold">{name}</p>
        <p className="truncate text-micro text-muted-foreground">
          {roleTitle} &middot; {department}
        </p>
      </div>
      <div className="flex flex-col items-end gap-1.5">
        <Badge variant={STATUS_VARIANT[status]}>{status}</Badge>
        {metric && (
          <span className="tabular-nums text-micro text-muted-foreground">
            {metric.value} {metric.label}
          </span>
        )}
      </div>
    </div>
  );
}

export { DigitalEmployeeCard };
export type { DigitalEmployeeStatus };
