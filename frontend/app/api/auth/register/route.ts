import { NextRequest, NextResponse } from "next/server";

import { apiFetch } from "@/lib/api-client";
import { apiErrorResponse } from "@/lib/route-handler-utils";

interface UserResponseBody {
  id: string;
  email: string;
  created_at: string;
}

/**
 * Proxies POST /v1/users. Registration issues no tokens (matches the
 * backend's M3 design — register and login are separate concerns), so
 * there's no cookie to set here; the client follows up with a normal
 * login call.
 */
export async function POST(request: NextRequest) {
  const body = await request.json();

  try {
    const user = await apiFetch<UserResponseBody>("/v1/users", {
      method: "POST",
      body,
    });
    return NextResponse.json(user, { status: 201 });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
