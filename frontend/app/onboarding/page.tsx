import { AuthGuard } from "@/features/auth/components/AuthGuard";
import { CenteredScreen } from "@/components/layout/centered-screen";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CreateOrganizationForm } from "@/features/organizations/components/CreateOrganizationForm";

export default function OnboardingPage() {
  return (
    <CenteredScreen>
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
    </CenteredScreen>
  );
}
