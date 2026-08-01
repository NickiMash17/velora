"use client";

import { useMutation } from "@tanstack/react-query";

import { useSessionStore } from "@/features/auth/store/session-store";
import { selectOrganization } from "./organizations-client";

export function useSelectOrganizationMutation() {
  const accessToken = useSessionStore((state) => state.accessToken);
  const setAccessToken = useSessionStore((state) => state.setAccessToken);

  return useMutation({
    mutationFn: (organizationId: string) => {
      if (!accessToken) {
        throw new Error("Not authenticated.");
      }
      return selectOrganization(accessToken, organizationId);
    },
    onSuccess: (data) => setAccessToken(data.access_token),
  });
}
