import { LiveDot, type LiveDotStatus } from "@/components/ui/live-dot";
import { cn } from "@/lib/utils";

interface MeridianEmployeeSignal {
  status: LiveDotStatus;
}

interface MeridianDnaSignal {
  version: string;
  status: "published" | "draft";
}

/**
 * The Meridian Line — a permanent, ~40px strip beneath the header on every
 * authenticated screen (docs/design/ComponentGuidelines.md §3,
 * docs/design/UXPrinciples.md §6). Renders a compressed live read of the
 * organization plus the Company DNA mark.
 *
 * M4 has zero Digital Employees and no Company DNA feature yet — both
 * explicit non-goals. Rather than fabricate activity or a DNA version,
 * this component renders its real, honest dormant state when given no
 * data (the default): a quiet "No Digital Employees yet" caption, no DNA
 * mark. A future milestone passes real `employees`/`dna` props; no change
 * to this component is needed then.
 */
function MeridianLine({
  employees = [],
  dna = null,
  className,
}: {
  employees?: MeridianEmployeeSignal[];
  dna?: MeridianDnaSignal | null;
  className?: string;
}) {
  const activeCount = employees.filter((employee) => employee.status === "live").length;

  return (
    <div
      role="region"
      aria-live="polite"
      aria-label="Organization activity"
      className={cn(
        "flex h-(--meridian-line-height) shrink-0 items-center justify-between gap-4 border-b border-border bg-background/85 px-4 backdrop-blur-sm sm:px-6",
        className
      )}
    >
      {employees.length === 0 ? (
        <span className="text-small text-muted-foreground">No Digital Employees yet</span>
      ) : (
        <div className="flex items-center gap-2">
          {employees.map((employee, index) => (
            <LiveDot key={index} status={employee.status} />
          ))}
          <span className="hidden text-small text-muted-foreground sm:inline">
            {employees.length} employee{employees.length === 1 ? "" : "s"} &middot; {activeCount} active
          </span>
        </div>
      )}

      {dna && (
        <span className="hidden items-center gap-1.5 text-small text-muted-foreground sm:flex">
          <span className="size-1.5 rounded-full bg-signal" aria-hidden />
          DNA {dna.version} &middot; {dna.status}
        </span>
      )}
    </div>
  );
}

export { MeridianLine };
export type { MeridianEmployeeSignal, MeridianDnaSignal };
