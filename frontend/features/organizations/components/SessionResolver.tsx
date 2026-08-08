"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useEnsureSession } from "@/features/auth/api/use-ensure-session";
import { useSessionStore } from "@/features/auth/store/session-store";
import { FormError } from "@/components/ui/form-error";
import { LoadingState } from "@/components/ui/loading-state";
import { apiFetch, ApiError } from "@/lib/api-client";
import { listMyOrganizations, selectOrganization } from "../api/organizations-client";
import type { OrganizationMembership } from "../api/organizations-client";
import { OrganizationChoiceList } from "./OrganizationChoiceList";

/**
 * The root route's job: given an authenticated session, decide where to
 * actually send the user — WireframeSpec.md §4's exact navigation rule:
 * no organization → onboarding; exactly one → dashboard (auto-selected,
 * no visible switcher step); more than one → a choice list.
 */
export function SessionResolver() {
  const status = useEnsureSession();
  const router = useRouter();
  const accessToken = useSessionStore((state) => state.accessToken);
  const setAccessToken = useSessionStore((state) => state.setAccessToken);
  const [choices, setChoices] = useState<OrganizationMembership[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status !== "authenticated" || !accessToken) {
      return;
    }

    let cancelled = false;

    async function resolveOrganization(token: string) {
      try {
        await apiFetch("/v1/organizations/me", { accessToken: token });
        if (!cancelled) router.replace("/dashboard");
        return;
      } catch (err) {
        if (!(err instanceof ApiError) || err.code !== "no_organization_context") {
          if (!cancelled) setError("Something went wrong. Please try again.");
          return;
        }
      }

      try {
        const memberships = await listMyOrganizations(token);
        if (cancelled) return;

        if (memberships.length === 0) {
          router.replace("/onboarding");
        } else if (memberships.length === 1) {
          const result = await selectOrganization(token, memberships[0].organization.id);
          if (!cancelled) {
            setAccessToken(result.access_token);
            router.replace("/dashboard");
          }
        } else {
          setChoices(memberships);
        }
      } catch {
        if (!cancelled) setError("Something went wrong. Please try again.");
      }
    }

    resolveOrganization(accessToken);
    return () => {
      cancelled = true;
    };
  }, [status, accessToken, router, setAccessToken]);

  if (error) {
    return <FormError>{error}</FormError>;
  }

  if (choices) {
    return <OrganizationChoiceList memberships={choices} />;
  }

  return <LoadingState />;
}
