import { cn } from "@/lib/utils";

interface DecisionTraceEntry {
  time: string;
  text: string;
  flagged?: boolean;
}

/**
 * A vertical, monospace-timestamped sequence of what a Digital Employee
 * considered and why — reads like a flight-recorder transcript, not a
 * chat log (docs/design/ComponentGuidelines.md §3). Presentation-only: no
 * Decision Trace backend exists in M4. First real consumer: a Task's
 * Activity tab, a future milestone.
 */
function DecisionTraceTimeline({
  entries,
  className,
}: {
  entries: DecisionTraceEntry[];
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-2 font-mono text-micro", className)}>
      {entries.map((entry, index) => (
        <div key={index} className="grid grid-cols-[84px_1fr] gap-3">
          <span className="tabular-nums text-muted-foreground">{entry.time}</span>
          <span className={entry.flagged ? "text-signal" : undefined}>{entry.text}</span>
        </div>
      ))}
    </div>
  );
}

export { DecisionTraceTimeline };
export type { DecisionTraceEntry };
