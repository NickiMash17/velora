/**
 * Shared fetch wrapper for calling the FastAPI backend — framework-
 * agnostic (no Next.js/React imports), usable from both browser-side
 * React Query hooks (plain reads, bearer-token auth) and server-side
 * Route Handlers (session-mutating calls that also touch the httpOnly
 * refresh cookie — see app/api/*\/route.ts).
 *
 * Every non-2xx response is expected to follow the backend's error
 * envelope (docs/architecture/API.md §7):
 *   { "error": { "code", "message", "details", "request_id" } }
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown>,
    requestId: string | null
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

interface ApiFetchOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  accessToken?: string;
}

/**
 * Parses a fetch Response per the shared error envelope — used both for
 * calls to the FastAPI backend (apiFetch, below) and, in feature api/
 * modules, for calls the browser makes to this app's own Route Handlers
 * (app/api/*\/route.ts), which mirror the same envelope shape on error.
 */
export async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const error = payload?.error as
      | { code?: string; message?: string; details?: Record<string, unknown>; request_id?: string }
      | undefined;
    throw new ApiError(
      response.status,
      error?.code ?? "unknown_error",
      error?.message ?? "An unexpected error occurred.",
      error?.details ?? {},
      error?.request_id ?? null
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { method = "GET", body, accessToken } = options;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  return parseJsonResponse<T>(response);
}
