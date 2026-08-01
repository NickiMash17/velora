"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSelectOrganizationMutation } from "../api/use-select-organization";
import type { OrganizationMembership } from "../api/organizations-client";

/**
 * A minimal, honest "pick one" list — not a full organization switcher.
 * Unreachable in practice this milestone (no invite flow exists to ever
 * put a user in more than one organization), but a user backfilled with
 * multiple memberships outside the app must still see something correct
 * rather than a silently-wrong auto-pick.
 */
export function OrganizationChoiceList({ memberships }: { memberships: OrganizationMembership[] }) {
  const router = useRouter();
  const selectMutation = useSelectOrganizationMutation();

  async function handleSelect(organizationId: string) {
    await selectMutation.mutateAsync(organizationId);
    router.replace("/dashboard");
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Choose an organization</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {memberships.map((membership) => (
          <Button
            key={membership.organization.id}
            variant="outline"
            className="justify-start"
            disabled={selectMutation.isPending}
            onClick={() => handleSelect(membership.organization.id)}
          >
            {membership.organization.name}
          </Button>
        ))}
      </CardContent>
    </Card>
  );
}
