import { cn } from "@/lib/utils";

/**
 * The shared wrapper for focused, single-purpose screens (session
 * resolution, login, register, onboarding) — no rail, no header chrome,
 * per Journey 1's "momentum matters more than confirmation"
 * (docs/design/UserJourneys.md). Replaces four previously-duplicated
 * `<main className="flex min-h-screen flex-col items-center
 * justify-center gap-8 p-8">` + literal `<h1>Velora</h1>` blocks.
 */
function CenteredScreen({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <main className={cn("flex min-h-screen flex-col items-center justify-center gap-8 p-8", className)}>
      <h1 className="text-h1 font-semibold tracking-tight">Velora</h1>
      {children}
    </main>
  );
}

export { CenteredScreen };
