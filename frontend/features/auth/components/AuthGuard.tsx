"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { LoadingState } from "@/components/ui/loading-state";
import { useEnsureSession } from "../api/use-ensure-session";

/** Wraps any protected page's content — see use-ensure-session's
 * docstring for why this can't just check the Zustand store directly. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const status = useEnsureSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status !== "authenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingState />
      </div>
    );
  }

  return <>{children}</>;
}
