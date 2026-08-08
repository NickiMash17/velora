"use client";

import { useState } from "react";
import { Bell, Inbox, LogOut, Settings } from "lucide-react";

import { AppShell } from "@/components/shell/app-shell";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/ui/empty-state";
import { FormError } from "@/components/ui/form-error";
import { LiveDot } from "@/components/ui/live-dot";
import { LoadingState } from "@/components/ui/loading-state";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { showToast } from "@/components/ui/toast";
import { Cluster } from "@/components/layout/cluster";
import { Grid } from "@/components/layout/grid";
import { PageHeader } from "@/components/layout/page-header";
import { Section } from "@/components/layout/section";
import { SplitPanel } from "@/components/layout/split-panel";
import { Stack } from "@/components/layout/stack";
import { ApprovalQueueItem } from "@/components/molecules/approval-queue-item";
import { AutonomyDial, type AutonomyLevel } from "@/components/molecules/autonomy-dial";
import { DecisionTraceTimeline } from "@/components/molecules/decision-trace-timeline";
import { DigitalEmployeeCard } from "@/components/molecules/digital-employee-card";
import { GoalProgressRing } from "@/components/molecules/goal-progress-ring";
import { OrgPulse } from "@/components/molecules/org-pulse";

/**
 * Internal design-review tooling — NOT a product page. Not linked from
 * the icon rail, not part of the product nav. Every value below is
 * clearly-labeled mock data for demonstrating what these components look
 * like; none of it is wired to a real backend, because the underlying
 * features (Digital Employees, Goals, Approvals, Departments, Company
 * DNA) don't exist in M4. See docs/design/Stage0-Migration.md §11.
 *
 * This is a stand-in for a proper Storybook setup — flagged as known
 * technical debt, not a permanent fixture.
 */
export default function DesignPreviewPage() {
  const [autonomy, setAutonomy] = useState<AutonomyLevel>("notify");

  return (
    <AppShell title="Design Preview">
      <Stack gap={2} className="mb-8 rounded-lg border border-dashed border-border bg-muted/40 p-4">
        <p className="text-small font-semibold">Internal design-review page — not a product screen</p>
        <p className="text-small text-muted-foreground">
          Every value on this page is mock data, clearly labeled as such. Nothing here is wired to a
          real backend — see docs/design/Stage0-Migration.md §11.
        </p>
      </Stack>

      <Section className="pt-0">
        <PageHeader title="Core primitives" description="Badge, Avatar, Tooltip, Dialog, Tabs, Separator, Empty/Loading/Error state, Toast." />
        <Stack gap={8} className="mt-6">
          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">Badge</p>
            <Cluster gap={2}>
              <Badge>neutral</Badge>
              <Badge variant="success">success</Badge>
              <Badge variant="warning">warning</Badge>
              <Badge variant="critical">critical</Badge>
              <Badge variant="info">info</Badge>
            </Cluster>
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">Avatar</p>
            <Cluster gap={3}>
              <Avatar label="Maya" size="sm" />
              <Avatar label="Riley" size="md" tone="signal" />
              <Avatar label="Jordan" size="lg" />
            </Cluster>
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">
              Loading / Error / Empty state
            </p>
            <Stack gap={3} className="max-w-md">
              <LoadingState />
              <Skeleton className="h-8 w-full" />
              <FormError>Something went wrong. Please try again.</FormError>
              <EmptyState
                icon={<Inbox className="size-6" strokeWidth={1.5} />}
                title="Nothing here yet"
                description="This is the generic fallback — a specific molecule's dormant state is preferred where one exists."
              />
            </Stack>
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">
              Dropdown menu
            </p>
            <Cluster gap={2}>
              <DropdownMenu>
                <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
                  <Settings className="size-3.5" strokeWidth={1.5} aria-hidden />
                  Options
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuLabel>Account</DropdownMenuLabel>
                  <DropdownMenuItem>
                    <Bell className="size-3.5" strokeWidth={1.5} aria-hidden />
                    Notification settings
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => showToast.info("This is a mock action.")}>
                    <LogOut className="size-3.5" strokeWidth={1.5} aria-hidden />
                    Sign out (mock)
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </Cluster>
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">Dialog</p>
            <Cluster gap={2}>
              <Dialog>
                <DialogTrigger render={<Button variant="outline" size="sm" />}>Open dialog</DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Confirm action</DialogTitle>
                    <DialogDescription>
                      This is a presentation-only demo — no real destructive action is wired up.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
                    <DialogClose render={<Button />}>Confirm</DialogClose>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </Cluster>
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">Tabs</p>
            <Tabs defaultValue="overview" className="max-w-md">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="permissions">Permissions</TabsTrigger>
                <TabsTrigger value="activity">Activity</TabsTrigger>
              </TabsList>
              <TabsContent value="overview">
                <p className="text-small text-muted-foreground">Overview panel content (mock).</p>
              </TabsContent>
              <TabsContent value="permissions">
                <p className="text-small text-muted-foreground">Permissions panel content (mock).</p>
              </TabsContent>
              <TabsContent value="activity">
                <p className="text-small text-muted-foreground">Activity panel content (mock).</p>
              </TabsContent>
            </Tabs>
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">Toast</p>
            <Cluster gap={2}>
              <Button variant="outline" size="sm" onClick={() => showToast.success("Saved successfully.")}>
                Trigger success
              </Button>
              <Button variant="outline" size="sm" onClick={() => showToast.error("Couldn't save.")}>
                Trigger error
              </Button>
              <Button variant="outline" size="sm" onClick={() => showToast.info("For your information.")}>
                Trigger info
              </Button>
            </Cluster>
          </Stack>
        </Stack>
      </Section>

      <Separator className="my-4" />

      <Section>
        <PageHeader
          title="Layout primitives"
          description="Stack, Cluster, Grid, Section, ContentContainer, SplitPanel, PageHeader (this section uses all of them)."
        />
        <Stack gap={6} className="mt-6">
          <Grid cols={3} gap={4}>
            <Card>
              <CardHeader>
                <CardTitle className="text-small">Grid item 1</CardTitle>
              </CardHeader>
              <CardContent className="text-small text-muted-foreground">Mock card content.</CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-small">Grid item 2</CardTitle>
              </CardHeader>
              <CardContent className="text-small text-muted-foreground">Mock card content.</CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-small">Grid item 3</CardTitle>
              </CardHeader>
              <CardContent className="text-small text-muted-foreground">Mock card content.</CardContent>
            </Card>
          </Grid>

          <div>
            <p className="mb-2 text-micro font-semibold tracking-wide text-muted-foreground uppercase">
              SplitPanel (the shape a future Workforce Command Center composes from)
            </p>
            <SplitPanel
              main={
                <div className="flex h-32 items-center justify-center rounded-xl border border-dashed border-border text-small text-muted-foreground">
                  Dominant main pane (mock)
                </div>
              }
              side={
                <div className="flex h-32 items-center justify-center rounded-xl border border-dashed border-border text-small text-muted-foreground">
                  Docked side pane (mock)
                </div>
              }
            />
          </div>
        </Stack>
      </Section>

      <Separator className="my-4" />

      <Section>
        <PageHeader
          title="Signature molecules"
          description="Presentation-only, typed props, mock data — no Digital Employee/Goals/Approval/Org Pulse backend exists in M4."
        />
        <Stack gap={8} className="mt-6">
          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">
              Digital Employee Card
            </p>
            <Grid cols={2} gap={4}>
              <DigitalEmployeeCard
                name="Riley"
                roleTitle="Support Agent"
                department="Support"
                status="active"
                metric={{ label: "tasks this week", value: "12" }}
              />
              <DigitalEmployeeCard
                name="Maya"
                roleTitle="Sales Assistant"
                department="Sales"
                status="draft"
              />
            </Grid>
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">
              Autonomy Dial
            </p>
            <Card>
              <CardContent className="divide-y divide-border py-2">
                <AutonomyDial
                  actionLabel="Send email to customer"
                  value="auto"
                  onChange={() => {}}
                  className="py-3"
                />
                <AutonomyDial
                  actionLabel="Issue refund ≤ $50"
                  value={autonomy}
                  onChange={setAutonomy}
                  className="py-3"
                />
                <AutonomyDial
                  actionLabel="Issue refund > $50"
                  value="approve"
                  onChange={() => {}}
                  className="py-3"
                />
              </CardContent>
            </Card>
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">
              Goal Progress Ring
            </p>
            <Card>
              <CardContent className="flex flex-wrap gap-8 py-4">
                <GoalProgressRing label="Qualified leads +20%" percent={62} target="Sep 30" />
                <GoalProgressRing label="Response time -30%" percent={88} target="Oct 15" />
                <GoalProgressRing label="Referral program" percent={0} />
              </CardContent>
            </Card>
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">
              Approval Queue Item
            </p>
            <ApprovalQueueItem
              employeeName="Riley"
              actionDescription="wants to issue a refund"
              traceSummary="Requested amount $120 exceeds the $50 no-approval limit."
              onApprove={() => showToast.success("Approved (mock).")}
              onReject={() => showToast.info("Rejected (mock).")}
            />
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">
              Decision Trace Timeline
            </p>
            <Card>
              <CardContent className="py-4">
                <DecisionTraceTimeline
                  entries={[
                    { time: "10:42:03", text: "Task received: refund request from customer #4821" },
                    { time: "10:42:04", text: "Checked refund policy — limit $50 without approval" },
                    { time: "10:42:05", text: "▍ Routed to approval queue", flagged: true },
                    { time: "10:44:52", text: "✓ Approved — refund issued, confirmation RF-88213" },
                  ]}
                />
              </CardContent>
            </Card>
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">
              Org Pulse
            </p>
            <OrgPulse
              departments={[
                {
                  name: "Sales",
                  employees: [
                    { name: "Maya", status: "idle" },
                    { name: "Riley", status: "live" },
                  ],
                },
                {
                  name: "Support",
                  employees: [{ name: "Jordan", status: "drift" }],
                },
              ]}
            />
          </Stack>

          <Stack gap={2}>
            <p className="text-micro font-semibold tracking-wide text-muted-foreground uppercase">
              LiveDot (the primitive Org Pulse and the Meridian Line share)
            </p>
            <Cluster gap={4}>
              <span className="flex items-center gap-2 text-small">
                <LiveDot status="idle" /> idle
              </span>
              <span className="flex items-center gap-2 text-small">
                <LiveDot status="live" /> live
              </span>
              <span className="flex items-center gap-2 text-small">
                <LiveDot status="drift" /> drift
              </span>
            </Cluster>
          </Stack>
        </Stack>
      </Section>
    </AppShell>
  );
}
