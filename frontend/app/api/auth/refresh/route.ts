import { NextRequest, NextResponse } from "next/server";

import { apiFetch } from "@/lib/api-client";
import {
  apiErrorResponse,
  refreshCookieOptions,
  REFRESH_COOKIE_NAME,
  unauthorizedResponse,
} from "@/lib/route-handler-utils";

interface TokenResponseBody {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

/**
 * Proxies POST /v1/auth/refresh using the httpOnly cookie — the client
 * never has to know or handle the refresh token itself, it just calls
 * this endpoint (e.g. on a 401 from a resource call, or on app load) to
 * get a fresh access token.
 */
export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get(REFRESH_COOKIE_NAME)?.value;
  if (!refreshToken) {
    return unauthorizedResponse("No active session.");
  }

  try {
    const tokens = await apiFetch<TokenResponseBody>("/v1/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    });

    const response = NextResponse.json({
      access_token: tokens.access_token,
      expires_in: tokens.expires_in,
    });
    response.cookies.set(REFRESH_COOKIE_NAME, tokens.refresh_token, refreshCookieOptions());
    return response;
  } catch (error) {
    return apiErrorResponse(error);
  }
}
