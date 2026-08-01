import { AuthGuard } from "@/features/auth/components/AuthGuard";
import { DashboardShell } from "@/features/organizations/components/DashboardShell";

export default function DashboardPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <AuthGuard>
        <DashboardShell />
      </AuthGuard>
    </main>
  );
}
