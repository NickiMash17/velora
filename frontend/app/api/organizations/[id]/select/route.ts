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

/** Proxies POST /v1/organizations/{id}/select — see app/api/organizations/route.ts's
 * module docstring for why this needs the httpOnly cookie server-side. */
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const refreshToken = request.cookies.get(REFRESH_COOKIE_NAME)?.value;
  const accessToken = bearerToken(request);
  if (!refreshToken || !accessToken) {
    return unauthorizedResponse("No active session.");
  }

  try {
    const result = await apiFetch<OrganizationSessionResponseBody>(
      `/v1/organizations/${id}/select`,
      {
        method: "POST",
        accessToken,
        body: { refresh_token: refreshToken },
      }
    );

    const response = NextResponse.json({
      organization: result.organization,
      access_token: result.tokens.access_token,
      expires_in: result.tokens.expires_in,
    });
    response.cookies.set(REFRESH_COOKIE_NAME, result.tokens.refresh_token, refreshCookieOptions());
    return response;
  } catch (error) {
    return apiErrorResponse(error);
  }
}
