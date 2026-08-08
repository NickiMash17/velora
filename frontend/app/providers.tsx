"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

/**
 * All app-wide client providers, composed in one place. Kept as a single
 * "use client" boundary so app/layout.tsx itself can stay a Server
 * Component — only what actually needs client-side hooks (theme, query
 * cache) pays that cost.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  // Created once per component instance (not per render) via useState,
  // so the cache survives re-renders but isn't shared across users/requests
  // on the server — standard pattern for React Query under the App Router.
  const [queryClient] = useState(() => new QueryClient());

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>{children}</TooltipProvider>
        <Toaster />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
