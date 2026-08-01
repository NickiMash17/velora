import { NextResponse } from "next/server";

import { clearedRefreshCookieOptions, REFRESH_COOKIE_NAME } from "@/lib/route-handler-utils";

/**
 * Clears the refresh cookie. No backend call — M3/M4's API has no
 * revoke-on-logout endpoint (the refresh token simply expires on its
 * own schedule, or is invalidated the next time it's presented after
 * this point since the client no longer holds it); adding one is out of
 * this milestone's scope.
 */
export async function POST() {
  const response = NextResponse.json({ success: true });
  response.cookies.set(REFRESH_COOKIE_NAME, "", clearedRefreshCookieOptions());
  return response;
}
