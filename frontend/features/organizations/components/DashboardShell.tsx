"use client";

import { useRouter } from "next/navigation";

import { AppShell } from "@/components/shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FormError } from "@/components/ui/form-error";
import { Skeleton } from "@/components/ui/skeleton";
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
 *
 * The Meridian Line renders here with no data (its real, honest dormant
 * state — components/shell/meridian-line.tsx) since this organization has
 * zero Digital Employees and no Company DNA feature exists yet.
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
    return (
      <AppShell title="Dashboard">
        <Card className="w-full max-w-md">
          <CardHeader>
            <Skeleton className="h-5 w-40" />
            <Skeleton className="mt-1.5 h-4 w-28" />
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Skeleton className="h-4 w-52" />
            <Skeleton className="h-8 w-24" />
          </CardContent>
        </Card>
      </AppShell>
    );
  }

  if (organizationQuery.isError || !organizationQuery.data) {
    return (
      <AppShell title="Dashboard">
        <FormError>Couldn&apos;t load your organization.</FormError>
      </AppShell>
    );
  }

  const { organization, role } = organizationQuery.data;

  return (
    <AppShell title="Dashboard" headerRight={<Badge>{role.replace(/_/g, " ")}</Badge>}>
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{organization.name}</CardTitle>
          <CardDescription>
            {organization.plan_tier} plan &middot; {organization.status}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-small text-muted-foreground">Signed in as {userQuery.data?.email}</p>
          <Button variant="outline" onClick={handleLogout} disabled={logoutMutation.isPending}>
            Sign out
          </Button>
        </CardContent>
      </Card>
    </AppShell>
  );
}
