"use client";

import { cn } from "@/lib/utils";

type AutonomyLevel = "auto" | "notify" | "approve";

const LEVELS: { value: AutonomyLevel; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "notify", label: "Notify" },
  { value: "approve", label: "Approve" },
];

/**
 * The per-action-type autonomy control, rendered as a three-position
 * dial rather than a dropdown or radio buttons — deliberately weightier
 * to change than a settings toggle, because autonomy level is the single
 * most trust-sensitive control in the product
 * (docs/design/ComponentGuidelines.md §3: "this is a decision, not a
 * preference"). Controlled; presentation-only — no Digital Employee
 * permission system exists in M4. First real consumer: Employee Profile's
 * Permissions & Autonomy tab, a future milestone.
 */
function AutonomyDial({
  actionLabel,
  value,
  onChange,
  className,
}: {
  actionLabel: string;
  value: AutonomyLevel;
  onChange?: (value: AutonomyLevel) => void;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-between gap-4", className)}>
      <span className="text-small">{actionLabel}</span>
      <div
        role="radiogroup"
        aria-label={`Autonomy for ${actionLabel}`}
        className="flex gap-1 rounded-lg border border-border bg-muted p-1"
      >
        {LEVELS.map((level) => (
          <button
            key={level.value}
            type="button"
            role="radio"
            aria-checked={value === level.value}
            onClick={() => onChange?.(level.value)}
            className={cn(
              "rounded-md px-3 py-1 text-micro font-semibold transition-colors duration-(--duration-micro) ease-meridian-out",
              value === level.value
                ? "bg-signal text-ink"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {level.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export { AutonomyDial };
export type { AutonomyLevel };
