/**
 * Shared helpers for the Route Handlers under app/api/ that proxy
 * session-mutating backend calls (login, register, refresh, logout,
 * organization creation/selection) and manage the httpOnly refresh
 * cookie — the one thing plain browser-side reads never touch.
 */

import { NextResponse } from "next/server";

import { ApiError } from "@/lib/api-client";

export const REFRESH_COOKIE_NAME = "velora_refresh_token";

// Matches the backend's Settings.refresh_token_ttl_days default
// (Security.md §3.1.2) — the cookie's own expiry is just housekeeping;
// the refresh token's real validity is enforced server-side regardless.
const REFRESH_TOKEN_MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

function baseCookieOptions() {
  return {
    httpOnly: true,
    // Secure is required for SameSite=Lax cookies to survive real HTTPS
    // deployments; disabled only in local dev, where the frontend and
    // backend both run over plain http://localhost.
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
  };
}

export function refreshCookieOptions() {
  return { ...baseCookieOptions(), maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS };
}

export function clearedRefreshCookieOptions() {
  return { ...baseCookieOptions(), maxAge: 0 };
}

export function apiErrorResponse(error: unknown): NextResponse {
  if (error instanceof ApiError) {
    return NextResponse.json(
      {
        error: {
          code: error.code,
          message: error.message,
          details: error.details,
          request_id: error.requestId,
        },
      },
      { status: error.status }
    );
  }
  throw error;
}

export function unauthorizedResponse(message: string): NextResponse {
  return NextResponse.json(
    { error: { code: "unauthorized", message, details: {}, request_id: null } },
    { status: 401 }
  );
}

export function bearerToken(request: Request): string | null {
  const header = request.headers.get("authorization");
  if (!header?.startsWith("Bearer ")) {
    return null;
  }
  return header.slice("Bearer ".length);
}
