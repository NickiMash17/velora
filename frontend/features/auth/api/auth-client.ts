import { parseJsonResponse } from "@/lib/api-client";

interface SessionTokens {
  access_token: string;
  expires_in: number;
}

interface RegisteredUser {
  id: string;
  email: string;
  created_at: string;
}

export async function login(email: string, password: string): Promise<SessionTokens> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parseJsonResponse<SessionTokens>(response);
}

export async function register(email: string, password: string): Promise<RegisteredUser> {
  const response = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parseJsonResponse<RegisteredUser>(response);
}

export async function refreshSession(): Promise<SessionTokens> {
  const response = await fetch("/api/auth/refresh", { method: "POST" });
  return parseJsonResponse<SessionTokens>(response);
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" });
}
