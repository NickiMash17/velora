"use client";

import { create } from "zustand";

/**
 * The access token lives here — in memory only, never persisted to
 * localStorage/sessionStorage/a readable cookie. The refresh token never
 * reaches this store at all; it stays server-side in an httpOnly cookie
 * (see lib/route-handler-utils.ts). A hard page reload always loses this
 * state, which is the intended tradeoff — see this milestone's
 * completion report for the token-storage decision.
 */
interface SessionState {
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
  clear: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  accessToken: null,
  setAccessToken: (token) => set({ accessToken: token }),
  clear: () => set({ accessToken: null }),
}));
