import { NextRequest, NextResponse } from "next/server";

import { REFRESH_COOKIE_NAME } from "@/lib/route-handler-utils";

/**
 * Cheap route protection: checks only whether the httpOnly refresh
 * cookie exists, not whether it's actually valid — real verification
 * always happens API-side (the cookie could be stale/revoked, in which
 * case the page's own session-resolution/AuthGuard logic redirects to
 * /login anyway). This just avoids serving an obviously logged-out
 * visitor a protected page's shell.
 */
export function middleware(request: NextRequest) {
  const hasSession = Boolean(request.cookies.get(REFRESH_COOKIE_NAME)?.value);
  const { pathname } = request.nextUrl;

  const isProtectedPath = pathname.startsWith("/dashboard") || pathname.startsWith("/onboarding");
  const isAuthPath = pathname === "/login" || pathname === "/register";

  if (isProtectedPath && !hasSession) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (isAuthPath && hasSession) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/onboarding/:path*", "/login", "/register"],
};
