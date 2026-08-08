import * as React from "react";
import { Avatar as AvatarPrimitive } from "@base-ui/react/avatar";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * A restrained geometric monogram — no illustrated character, no stock
 * photo (docs/design/ComponentGuidelines.md's Digital Employee Card entry,
 * §3, extended here to any identity in the product: a Digital Employee is
 * a colleague with a job, not a mascot, and neither is a human account).
 * M4 has no avatar-upload feature, so this always renders its initials
 * fallback — `AvatarPrimitive.Image` is available for a future milestone
 * that adds real profile pictures, without redesigning this component.
 */
const avatarVariants = cva(
  "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-lg font-semibold",
  {
    variants: {
      size: {
        sm: "size-6 text-micro",
        md: "size-8 text-small",
        lg: "size-10 text-h3",
      },
      tone: {
        neutral: "bg-foreground text-background",
        signal: "bg-signal text-ink",
      },
    },
    defaultVariants: {
      size: "md",
      tone: "neutral",
    },
  }
);

function Avatar({
  label,
  size,
  tone,
  className,
}: {
  /** The name/email this avatar represents — the initial is derived from it. */
  label: string;
  className?: string;
} & VariantProps<typeof avatarVariants>) {
  const initial = label.trim().charAt(0).toUpperCase() || "?";

  return (
    <AvatarPrimitive.Root
      data-slot="avatar"
      className={cn(avatarVariants({ size, tone, className }))}
    >
      <AvatarPrimitive.Fallback aria-hidden className="flex items-center justify-center">
        {initial}
      </AvatarPrimitive.Fallback>
    </AvatarPrimitive.Root>
  );
}

export { Avatar, avatarVariants };
