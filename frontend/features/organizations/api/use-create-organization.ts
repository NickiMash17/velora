"use client";

import { useMutation } from "@tanstack/react-query";

import { useSessionStore } from "@/features/auth/store/session-store";
import { createOrganization } from "./organizations-client";

export function useCreateOrganizationMutation() {
  const accessToken = useSessionStore((state) => state.accessToken);
  const setAccessToken = useSessionStore((state) => state.setAccessToken);

  return useMutation({
    mutationFn: (name: string) => {
      if (!accessToken) {
        throw new Error("Not authenticated.");
      }
      return createOrganization(accessToken, name);
    },
    onSuccess: (data) => setAccessToken(data.access_token),
  });
}
