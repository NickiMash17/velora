"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/**
 * The left icon rail (docs/design/ComponentGuidelines.md §4) — command-first
 * navigation's persistent chrome. Ships with exactly one real item:
 * Employees/Goals/Knowledge/Settings don't exist yet in M4, and rendering
 * icons for them would be chrome pointing at features that don't exist
 * (the M4 plan's own "no fake widgets" rule). Add entries here as each
 * milestone ships its real destination.
 */
const NAV_ITEMS = [{ href: "/dashboard", label: "Dashboard", icon: LayoutDashboard }] as const;

function IconRail() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Primary"
      className="flex w-16 shrink-0 flex-col items-center gap-1 border-r border-border py-4"
    >
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href;
        const Icon = item.icon;
        return (
          <Tooltip key={item.href}>
            <TooltipTrigger
              render={
                <Link
                  href={item.href}
                  aria-label={item.label}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex size-10 items-center justify-center rounded-lg text-muted-foreground transition-colors duration-(--duration-micro) ease-meridian-out hover:bg-muted hover:text-foreground",
                    isActive && "bg-muted text-foreground"
                  )}
                />
              }
            >
              <Icon className="size-4" strokeWidth={1.5} aria-hidden />
            </TooltipTrigger>
            <TooltipContent>{item.label}</TooltipContent>
          </Tooltip>
        );
      })}
    </nav>
  );
}

export { IconRail };
