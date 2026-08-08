import { cn } from "@/lib/utils";

const MAX_WIDTH_CLASSES = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-3xl",
  xl: "max-w-6xl",
} as const;

/**
 * Centers content and caps its width — DesignSystem.md §6's "generous, not
 * dense" applied at the page level: a 2000px-wide card isn't a better
 * card. Wrap a page's real content in this rather than repeating
 * `mx-auto max-w-*` ad hoc.
 */
function ContentContainer({
  maxWidth = "lg",
  className,
  ...props
}: React.ComponentProps<"div"> & { maxWidth?: keyof typeof MAX_WIDTH_CLASSES }) {
  return (
    <div className={cn("mx-auto w-full", MAX_WIDTH_CLASSES[maxWidth], className)} {...props} />
  );
}

export { ContentContainer };
