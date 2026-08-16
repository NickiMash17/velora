import { cn } from "@/lib/utils";

/**
 * Inline error message — docs/design/UXPrinciples.md §3: plain language,
 * calm (Clay applied narrowly to text only, never a filled red banner),
 * `role="alert"` so screen readers announce it. Replaces the identical
 * `role="alert" text-sm text-destructive` paragraph previously duplicated
 * across LoginForm, RegisterForm, CreateOrganizationForm, and
 * SessionResolver.
 */
function FormError({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p role="alert" className={cn("text-small text-destructive", className)}>
      {children}
    </p>
  );
}

export { FormError };
