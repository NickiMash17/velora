"use client";

import { useQuery } from "@tanstack/react-query";

import { getCurrentOrganization } from "./organizations-client";

export function useCurrentOrganizationQuery(accessToken: string | null) {
  return useQuery({
    queryKey: ["organizations", "current", accessToken],
    queryFn: () => getCurrentOrganization(accessToken!),
    enabled: Boolean(accessToken),
    // A 404 (no_organization_context) is an expected, meaningful result
    // here, not a transient failure worth retrying.
    retry: false,
  });
}
