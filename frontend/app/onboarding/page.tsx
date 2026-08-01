import { AuthGuard } from "@/features/auth/components/AuthGuard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CreateOrganizationForm } from "@/features/organizations/components/CreateOrganizationForm";

export default function OnboardingPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Velora</h1>
      <AuthGuard>
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>Create your organization</CardTitle>
            <CardDescription>
              This is the workspace your Digital Employees will belong to.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CreateOrganizationForm />
          </CardContent>
        </Card>
      </AuthGuard>
    </main>
  );
}
