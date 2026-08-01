import { NextRequest, NextResponse } from "next/server";

import { apiFetch } from "@/lib/api-client";
import {
  apiErrorResponse,
  bearerToken,
  refreshCookieOptions,
  REFRESH_COOKIE_NAME,
  unauthorizedResponse,
} from "@/lib/route-handler-utils";

interface OrganizationResponseBody {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
  status: string;
  created_at: string;
}

interface OrganizationSessionResponseBody {
  organization: OrganizationResponseBody;
  tokens: { access_token: string; refresh_token: string; expires_in: number };
}

/**
 * Proxies POST /v1/organizations. Organization creation scopes the
 * session (Security.md §3.2), which means rotating the caller's current
 * refresh token — so, like /api/auth/refresh, this needs the httpOnly
 * cookie server-side and can't be called directly from browser JS.
 */
export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get(REFRESH_COOKIE_NAME)?.value;
  const accessToken = bearerToken(request);
  if (!refreshToken || !accessToken) {
    return unauthorizedResponse("No active session.");
  }

  const body = await request.json();

  try {
    const result = await apiFetch<OrganizationSessionResponseBody>("/v1/organizations", {
      method: "POST",
      accessToken,
      body: { name: body.name, refresh_token: refreshToken },
    });

    const response = NextResponse.json(
      {
        organization: result.organization,
        access_token: result.tokens.access_token,
        expires_in: result.tokens.expires_in,
      },
      { status: 201 }
    );
    response.cookies.set(REFRESH_COOKIE_NAME, result.tokens.refresh_token, refreshCookieOptions());
    return response;
  } catch (error) {
    return apiErrorResponse(error);
  }
}
