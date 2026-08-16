"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/form-error";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api-client";
import { useLoginMutation } from "../api/use-login";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();
  const loginMutation = useLoginMutation();

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await loginMutation.mutateAsync({ email, password });
      // Session-resolution at the root route decides onboarding vs.
      // dashboard from here — see app/page.tsx.
      router.push("/");
    } catch {
      // Surfaced via loginMutation.error below.
    }
  }

  const error = loginMutation.error;

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
          disabled={loginMutation.isPending}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={loginMutation.isPending}
        />
      </div>
      {error && (
        <FormError>
          {error instanceof ApiError ? error.message : "Something went wrong. Please try again."}
          {error instanceof ApiError &&
            error.code === "rate_limited" &&
            typeof error.details.retry_after_seconds === "number" && (
              <> Try again in {error.details.retry_after_seconds}s.</>
            )}
        </FormError>
      )}
      <Button type="submit" disabled={loginMutation.isPending}>
        {loginMutation.isPending ? "Logging in…" : "Log in"}
      </Button>
    </form>
  );
}
