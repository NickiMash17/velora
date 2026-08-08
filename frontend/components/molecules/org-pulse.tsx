import { LiveDot, type LiveDotStatus } from "@/components/ui/live-dot";
import { cn } from "@/lib/utils";

interface OrgPulseEmployee {
  name: string;
  status: LiveDotStatus;
}

interface OrgPulseDepartment {
  name: string;
  employees: OrgPulseEmployee[];
}

/**
 * The living organization map — departments as fixed nodes, Digital
 * Employees as smaller nodes within them
 * (docs/design/ComponentGuidelines.md §3, docs/design/UXPrinciples.md §6).
 * A DOM/SVG foundation, not the full canvas-based version with animated
 * task edges (that one lives in the approved meridian.html artifact and
 * is Stage 2 work, once real Digital Employees and Departments exist to
 * animate) — this is the typed, reusable shape a future milestone plugs
 * real data into. Presentation-only: no Digital Employee/Department
 * backend exists in M4. First real consumer: the Workforce Command
 * Center, a future milestone.
 */
function OrgPulse({
  departments,
  className,
}: {
  departments: OrgPulseDepartment[];
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap gap-4", className)}>
      {departments.map((department) => (
        <div
          key={department.name}
          className="min-w-48 flex-1 rounded-xl border border-dashed border-border p-4"
        >
          <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">
            {department.name}
          </p>
          <div className="mt-3 flex flex-col gap-2">
            {department.employees.map((employee) => (
              <div key={employee.name} className="flex items-center gap-2 text-small">
                <LiveDot status={employee.status} />
                <span className={employee.status === "live" ? "font-medium" : "text-muted-foreground"}>
                  {employee.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export { OrgPulse };
export type { OrgPulseDepartment, OrgPulseEmployee };
