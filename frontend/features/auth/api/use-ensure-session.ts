"use client";

import { useEffect, useState } from "react";

import { refreshSession } from "./auth-client";
import { useSessionStore } from "../store/session-store";

export type SessionStatus = "checking" | "authenticated" | "unauthenticated";

/**
 * The in-memory access token is lost on every hard reload (by design —
 * see session-store.ts). This hook is what makes that survivable: if no
 * access token is held yet, it silently attempts a refresh using the
 * httpOnly cookie before declaring the session missing. Any
 * page/component that needs an authenticated session renders through
 * this (directly, or via AuthGuard) rather than assuming the store is
 * already populated.
 */
export function useEnsureSession(): SessionStatus {
  const accessToken = useSessionStore((state) => state.accessToken);
  const setAccessToken = useSessionStore((state) => state.setAccessToken);
  const [status, setStatus] = useState<SessionStatus>(accessToken ? "authenticated" : "checking");

  useEffect(() => {
    if (accessToken) {
      setStatus("authenticated");
      return;
    }

    let cancelled = false;
    refreshSession()
      .then((tokens) => {
        if (cancelled) return;
        setAccessToken(tokens.access_token);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!cancelled) setStatus("unauthenticated");
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken, setAccessToken]);

  return status;
}
