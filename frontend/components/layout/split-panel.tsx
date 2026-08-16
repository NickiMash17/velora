import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

/**
 * A dominant main pane beside a narrower, docked side pane — the generic
 * shape docs/design/UXPrinciples.md §5's Workforce Command Center will
 * compose from once the Org Pulse has real content (the main pane) and
 * "Needs You" has real approvals (the docked pane). No Command Center-
 * specific component exists yet — that's still Stage 2/3, per
 * docs/design/Roadmap.md — this is just the reusable two-pane shape.
 */
function SplitPanel({
  main,
  side,
  sideWidth = "20rem",
  className,
}: {
  main: React.ReactNode;
  side: React.ReactNode;
  sideWidth?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-6 lg:flex-row", className)}>
      <div className="min-w-0 flex-1">{main}</div>
      <Separator orientation="vertical" className="hidden lg:block" />
      <div className="w-full shrink-0 lg:w-(--split-panel-side-width)" style={{ "--split-panel-side-width": sideWidth } as React.CSSProperties}>
        {side}
      </div>
    </div>
  );
}

export { SplitPanel };
