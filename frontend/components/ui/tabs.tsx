import * as React from "react";
import { Tabs as TabsPrimitive } from "@base-ui/react/tabs";

import { cn } from "@/lib/utils";

/**
 * Lateral navigation within one screen, not a sequence — cross-fades, no
 * slide (docs/design/ComponentGuidelines.md's Employee Profile entry).
 * No real tabbed screen exists in M4 yet (Employee Profile's Overview/
 * Permissions/DNA/Activity/Chat tabs are a future milestone) — built fully
 * for that first real consumer.
 */
function Tabs({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return (
    <TabsPrimitive.Root data-slot="tabs" className={cn("flex flex-col gap-4", className)} {...props} />
  );
}

function TabsList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-list"
      className={cn("inline-flex items-center gap-1 border-b border-border", className)}
      {...props}
    />
  );
}

function TabsTrigger({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Tab>) {
  return (
    <TabsPrimitive.Tab
      data-slot="tabs-trigger"
      className={cn(
        "relative px-1 py-2 text-small font-medium text-muted-foreground outline-none transition-colors duration-(--duration-micro) ease-meridian-out after:absolute after:inset-x-0 after:-bottom-px after:h-px after:bg-transparent after:transition-colors after:duration-(--duration-micro) after:ease-meridian-out hover:text-foreground data-active:text-foreground data-active:after:bg-signal",
        className
      )}
      {...props}
    />
  );
}

function TabsContent({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Panel>) {
  return (
    <TabsPrimitive.Panel
      data-slot="tabs-content"
      className={cn(
        "outline-none transition-opacity duration-(--duration-component) ease-meridian-out",
        className
      )}
      {...props}
    />
  );
}

export { Tabs, TabsList, TabsTrigger, TabsContent };
