import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Not a bare approve/reject button pair — a compact card with the
 * Decision Trace summary inline, so a human can decide without leaving
 * the queue to dig through logs (docs/design/ComponentGuidelines.md §3).
 * The Signal-colored left indicator is the one earned exception to "no
 * decorative accent rails" elsewhere in the system, because this is the
 * single most time-sensitive item type in the product. Presentation-only:
 * no Approval backend exists in M4. First real consumer: the Workforce
 * Command Center's "Needs You" panel, a future milestone.
 */
function ApprovalQueueItem({
  employeeName,
  actionDescription,
  traceSummary,
  onApprove,
  onReject,
  pending,
  className,
}: {
  employeeName: string;
  actionDescription: string;
  traceSummary: string;
  onApprove?: () => void;
  onReject?: () => void;
  pending?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border border-l-[3px] border-l-signal bg-card p-4",
        className
      )}
    >
      <p className="text-small font-semibold">
        {employeeName} <span className="font-normal text-muted-foreground">{actionDescription}</span>
      </p>
      <p className="mt-2 rounded-md border border-border bg-muted px-2.5 py-2 font-mono text-micro text-muted-foreground">
        {traceSummary}
      </p>
      <div className="mt-3 flex gap-2">
        <Button variant="outline" size="sm" onClick={onReject} disabled={pending}>
          Reject
        </Button>
        <Button size="sm" onClick={onApprove} disabled={pending}>
          Approve
        </Button>
      </div>
    </div>
  );
}

export { ApprovalQueueItem };
