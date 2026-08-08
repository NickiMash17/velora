import { CenteredScreen } from "@/components/layout/centered-screen";
import { SessionResolver } from "@/features/organizations/components/SessionResolver";

/**
 * The root route is now the session-resolution entry point, not a
 * marketing landing page (docs/product/WireframeSpec.md §3's Landing
 * Page is out of scope until real marketing content exists) —
 * unauthenticated visitors go to /login, authenticated ones are routed
 * to onboarding, the dashboard, or an organization choice, per
 * SessionResolver.
 */
export default function RootPage() {
  return (
    <CenteredScreen>
      <SessionResolver />
    </CenteredScreen>
  );
}
