import { AuthGuard } from "@/features/auth/components/AuthGuard";
import { DashboardShell } from "@/features/organizations/components/DashboardShell";

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardShell />
    </AuthGuard>
  );
}
