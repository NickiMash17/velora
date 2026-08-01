import { NextRequest, NextResponse } from "next/server";

import { apiFetch } from "@/lib/api-client";
import { apiErrorResponse, refreshCookieOptions, REFRESH_COOKIE_NAME } from "@/lib/route-handler-utils";

interface TokenResponseBody {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

/**
 * Proxies POST /v1/auth/login. The refresh token never reaches the
 * browser as JS-readable state — it's set here as an httpOnly cookie;
 * only the access token (short-lived, held in memory client-side) is
 * returned in the JSON body.
 */
export async function POST(request: NextRequest) {
  const body = await request.json();

  try {
    const tokens = await apiFetch<TokenResponseBody>("/v1/auth/login", {
      method: "POST",
      body,
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
