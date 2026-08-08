import { ThemeToggle } from "@/components/theme-toggle";

/**
 * The shell's top header — breadcrumb/page title on the left, real
 * contextual chrome on the right (docs/design/Wireframes.md §1). No
 * notification bell, no ⌘K palette, no org-switcher widget: none of those
 * features exist yet in M4, and rendering them would be chrome pointing
 * at nothing (the M4 plan's "no fake widgets" rule). `right` is a slot for
 * whatever real, working chrome a given screen actually has today.
 */
function Header({ title, right }: { title: string; right?: React.ReactNode }) {
  return (
    <header className="flex h-(--shell-header-height) shrink-0 items-center justify-between gap-4 border-b border-border px-4 sm:px-6">
      <h2 className="text-h3 font-semibold tracking-tight">{title}</h2>
      <div className="flex items-center gap-3">
        {right}
        <ThemeToggle />
      </div>
    </header>
  );
}

export { Header };
