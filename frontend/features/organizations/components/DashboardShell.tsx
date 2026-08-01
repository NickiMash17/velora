"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";
import { useCurrentUserQuery } from "@/features/auth/api/use-current-user";
import { useLogoutMutation } from "@/features/auth/api/use-logout";
import { useSessionStore } from "@/features/auth/store/session-store";
import { useCurrentOrganizationQuery } from "../api/use-current-organization";

/**
 * Deliberately minimal — organization name/plan/status, the current
 * user's role, and sign out. Not docs/product/WireframeSpec.md §7's full
 * Dashboard: that spec assumes Digital Employees/Goals exist, which this
 * milestone does not build. No hire-CTA, no fake widgets — those would
 * point at features that don't exist yet.
 */
export function DashboardShell() {
  const router = useRouter();
  const accessToken = useSessionStore((state) => state.accessToken);
  const organizationQuery = useCurrentOrganizationQuery(accessToken);
  const userQuery = useCurrentUserQuery();
  const logoutMutation = useLogoutMutation();

  async function handleLogout() {
    await logoutMutation.mutateAsync();
    router.replace("/login");
  }

  if (organizationQuery.isPending || userQuery.isPending) {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }

  if (organizationQuery.isError || !organizationQuery.data) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load your organization.
      </p>
    );
  }

  const { organization, role } = organizationQuery.data;

  return (
    <div className="flex w-full max-w-md flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Velora</h1>
        <ThemeToggle />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>{organization.name}</CardTitle>
          <CardDescription>
            {organization.plan_tier} plan · {organization.status}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            Signed in as {userQuery.data?.email} · {role}
          </p>
          <Button variant="outline" onClick={handleLogout} disabled={logoutMutation.isPending}>
            Sign out
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
