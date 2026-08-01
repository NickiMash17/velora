"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import { useSessionStore } from "../store/session-store";

interface CurrentUser {
  id: string;
  email: string;
  created_at: string;
}

export function useCurrentUserQuery() {
  const accessToken = useSessionStore((state) => state.accessToken);

  return useQuery({
    queryKey: ["users", "me", accessToken],
    queryFn: () => apiFetch<CurrentUser>("/v1/users/me", { accessToken: accessToken! }),
    enabled: Boolean(accessToken),
  });
}
