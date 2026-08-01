"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api-client";
import { useLoginMutation } from "../api/use-login";
import { useRegisterMutation } from "../api/use-register";

export function RegisterForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();
  const registerMutation = useRegisterMutation();
  const loginMutation = useLoginMutation();

  const isPending = registerMutation.isPending || loginMutation.isPending;
  const error = registerMutation.error ?? loginMutation.error;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await registerMutation.mutateAsync({ email, password });
      // Registration issues no tokens (a separate concern from auth) —
      // immediately logging in with the same credentials is what gets
      // the user an actual session, matching "momentum matters more
      // than confirmation" (docs/product/WireframeSpec.md §5).
      await loginMutation.mutateAsync({ email, password });
      router.push("/");
    } catch {
      // Surfaced via `error` below.
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={isPending}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={isPending}
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error instanceof ApiError ? error.message : "Something went wrong. Please try again."}
        </p>
      )}
      <Button type="submit" disabled={isPending}>
        {isPending ? "Creating account…" : "Create account"}
      </Button>
    </form>
  );
}
