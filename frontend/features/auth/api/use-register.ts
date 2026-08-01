"use client";

import { useMutation } from "@tanstack/react-query";

import { register } from "./auth-client";

export function useRegisterMutation() {
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      register(email, password),
  });
}
