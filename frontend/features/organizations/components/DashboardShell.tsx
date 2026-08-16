"use client";

import { useRouter } from "next/navigation";

import { AppShell } from "@/components/shell/app-shell";
import { AccountMenu } from "@/components/shell/account-menu";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FormError } from "@/components/ui/form-error";
import { Skeleton } from "@/components/ui/skeleton";
import { ContentContainer } from "@/components/layout/content-container";
import { Stack } from "@/components/layout/stack";
import { useCurrentUserQuery } from "@/features/auth/api/use-current-user";
import { useLogoutMutation } from "@/features/auth/api/use-logout";
import { useSessionStore } from "@/features/auth/store/session-store";
import { useCurrentOrganizationQuery } from "../api/use-current-organization";

const dateFormatter = new Intl.DateTimeFormat("en-US", { dateStyle: "medium" });

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
 *
 * Sign-out lives in the header's AccountMenu (Avatar + DropdownMenu) rather
 * than a button in this card — same mutation, same redirect, only the
 * trigger's location moved (docs/design/Stage0-Migration.md §11).
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
        <ContentContainer maxWidth="md">
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-40" />
              <Skeleton className="mt-1.5 h-4 w-28" />
            </CardHeader>
            <CardContent>
              <Stack gap={2}>
                <Skeleton className="h-4 w-36" />
                <Skeleton className="h-4 w-44" />
              </Stack>
            </CardContent>
          </Card>
        </ContentContainer>
      </AppShell>
    );
  }

  if (organizationQuery.isError || !organizationQuery.data) {
    return (
      <AppShell title="Dashboard">
        <ContentContainer maxWidth="md">
          <FormError>Couldn&apos;t load your organization.</FormError>
        </ContentContainer>
      </AppShell>
    );
  }

  const { organization, role } = organizationQuery.data;
  const email = userQuery.data?.email ?? "";

  return (
    <AppShell
      title="Dashboard"
      headerRight={
        <>
          <Badge>{role.replace(/_/g, " ")}</Badge>
          <AccountMenu email={email} onSignOut={handleLogout} isPending={logoutMutation.isPending} />
        </>
      }
    >
      <ContentContainer maxWidth="md">
        <Card>
          <CardHeader>
            <CardTitle>{organization.name}</CardTitle>
            <CardDescription>
              {organization.plan_tier} plan &middot; {organization.status}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Stack gap={2}>
              <p className="text-small text-muted-foreground">/{organization.slug}</p>
              <p className="text-small text-muted-foreground">
                Created {dateFormatter.format(new Date(organization.created_at))}
              </p>
            </Stack>
          </CardContent>
        </Card>
      </ContentContainer>
    </AppShell>
  );
}
