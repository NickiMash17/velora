"use client";

import { useMutation } from "@tanstack/react-query";

import { login } from "./auth-client";
import { useSessionStore } from "../store/session-store";

export function useLoginMutation() {
  const setAccessToken = useSessionStore((state) => state.setAccessToken);

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => login(email, password),
    onSuccess: (data) => setAccessToken(data.access_token),
  });
}
