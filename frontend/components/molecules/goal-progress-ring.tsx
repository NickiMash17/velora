import { cn } from "@/lib/utils";

/**
 * A thin circular progress indicator with a hard tick at the target and
 * the current value in the center — a ring reads as "a target being
 * approached," which is what a Goal is; a bar reads as "a task being
 * finished," which is what a Task is
 * (docs/design/ComponentGuidelines.md §3). Presentation-only: no Goals
 * backend exists in M4. First real consumer: the Goals list, a future
 * milestone.
 */
function GoalProgressRing({
  label,
  percent,
  target,
  size = 72,
  className,
}: {
  label: string;
  percent: number;
  target?: string;
  size?: number;
  className?: string;
}) {
  const radius = size / 2 - 6;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(100, Math.max(0, percent));
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className={cn("flex items-center gap-4", className)}>
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            className="stroke-border"
            strokeWidth={6}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            className="stroke-signal transition-[stroke-dashoffset] duration-(--duration-structural) ease-meridian-out"
            strokeWidth={6}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
          <line
            x1={size / 2}
            y1={6}
            x2={size / 2}
            y2={12}
            className="stroke-foreground"
            strokeWidth={2}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-small font-semibold tabular-nums">
          {Math.round(clamped)}%
        </span>
      </div>
      <div>
        <p className="text-small">{label}</p>
        {target && <p className="text-micro text-muted-foreground">target: {target}</p>}
      </div>
    </div>
  );
}

export { GoalProgressRing };
