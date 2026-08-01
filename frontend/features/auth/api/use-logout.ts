"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { logout } from "./auth-client";
import { useSessionStore } from "../store/session-store";

export function useLogoutMutation() {
  const clear = useSessionStore((state) => state.clear);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      clear();
      queryClient.clear();
    },
  });
}
