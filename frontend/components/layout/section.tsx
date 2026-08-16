import { cn } from "@/lib/utils";

/**
 * A vertical block of page content with generous, consistent breathing
 * room (docs/design/DesignSystem.md §6: "generous, not dense") — the
 * building block a page stacks to form its sections.
 */
function Section({ className, ...props }: React.ComponentProps<"section">) {
  return <section className={cn("py-8 sm:py-12", className)} {...props} />;
}

export { Section };
