import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * Status label — docs/design/ComponentGuidelines.md §2 ("Tag / Badge").
 * Uses the semantic ramp (success/warning/critical/info), never Signal —
 * Signal is reserved for the one accent that means "the thing that matters
 * right now" (DesignSystem.md §4.1), and a status pill isn't that.
 */
const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center gap-1 rounded-md border px-2 py-0.5 text-micro font-medium tracking-wide uppercase whitespace-nowrap",
  {
    variants: {
      variant: {
        neutral: "border-border bg-muted text-muted-foreground",
        success: "border-sage/30 bg-sage/10 text-sage",
        warning: "border-ochre/30 bg-ochre/10 text-ochre",
        critical: "border-clay/30 bg-clay/10 text-clay",
        info: "border-dusk/30 bg-dusk/10 text-dusk",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  }
);

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ variant, className }))}
      {...props}
    />
  );
}

export { Badge, badgeVariants };
