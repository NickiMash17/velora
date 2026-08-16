import { Header } from "./header";
import { IconRail } from "./icon-rail";
import { MeridianLine } from "./meridian-line";
import type { MeridianDnaSignal, MeridianEmployeeSignal } from "./meridian-line";

/**
 * The authenticated application shell — icon rail + header + Meridian Line
 * + content (docs/design/Wireframes.md §1). Wraps only the Dashboard for
 * now: it's the one authenticated screen with real navigational context.
 * Login/Register/Onboarding intentionally stay on CenteredScreen instead
 * (see components/layout/centered-screen.tsx) — Journey 1's "momentum
 * matters more than confirmation" argues against wrapping onboarding in
 * full shell chrome.
 */
function AppShell({
  title,
  headerRight,
  employees,
  dna,
  children,
}: {
  title: string;
  headerRight?: React.ReactNode;
  employees?: MeridianEmployeeSignal[];
  dna?: MeridianDnaSignal | null;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <IconRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header title={title} right={headerRight} />
        <MeridianLine employees={employees} dna={dna} />
        <main className="flex-1 p-6 sm:p-8">{children}</main>
      </div>
    </div>
  );
}

export { AppShell };
