import { toast } from "sonner";

/**
 * Typed helper over the already-mounted `sonner` Toaster
 * (components/ui/sonner.tsx, providers.tsx) — quiet confirmation by
 * default, never a modal requiring dismissal (docs/design/UXPrinciples.md
 * §4). Icons and Meridian theming are configured once on the `<Toaster />`
 * mount; these calls just supply the message. Not wired into the current
 * login/register/logout flows — those redirect immediately, and a toast
 * the user navigates past before reading isn't a genuine improvement. The
 * first real, un-redirected success/error moment is this helper's first
 * consumer.
 */
const showToast = {
  success: (message: string) => toast.success(message),
  error: (message: string) => toast.error(message),
  info: (message: string) => toast(message),
};

export { showToast };
