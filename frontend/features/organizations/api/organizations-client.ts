import { apiFetch, parseJsonResponse } from "@/lib/api-client";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
  status: string;
  created_at: string;
}

export interface OrganizationMembership {
  organization: Organization;
  role: string;
}

interface OrganizationSessionResult {
  organization: Organization;
  access_token: string;
  expires_in: number;
}

/** Plain read — called directly from the browser with the in-memory
 * bearer token, no Route Handler proxy needed (nothing here touches the
 * refresh cookie). */
export async function listMyOrganizations(accessToken: string): Promise<OrganizationMembership[]> {
  return apiFetch<OrganizationMembership[]>("/v1/organizations", { accessToken });
}

/** Plain read — same reasoning as listMyOrganizations. */
export async function getCurrentOrganization(accessToken: string): Promise<OrganizationMembership> {
  return apiFetch<OrganizationMembership>("/v1/organizations/me", { accessToken });
}

/** Session-mutating (rotates the refresh token) — goes through
 * /api/organizations, which holds the httpOnly cookie server-side. */
export async function createOrganization(
  accessToken: string,
  name: string
): Promise<OrganizationSessionResult> {
  const response = await fetch("/api/organizations", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ name }),
  });
  return parseJsonResponse<OrganizationSessionResult>(response);
}

/** Session-mutating — same reasoning as createOrganization. */
export async function selectOrganization(
  accessToken: string,
  organizationId: string
): Promise<OrganizationSessionResult> {
  const response = await fetch(`/api/organizations/${organizationId}/select`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseJsonResponse<OrganizationSessionResult>(response);
}
