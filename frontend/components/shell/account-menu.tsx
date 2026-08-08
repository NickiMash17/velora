"use client";

import { LogOut } from "lucide-react";

import { Avatar } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/**
 * The real account menu — an avatar (the signed-in user's email initial)
 * opening a dropdown whose one item is the existing, unchanged sign-out
 * action. This relocates that action's trigger from the dashboard card
 * into the shell header — the mutation and redirect it calls are
 * byte-for-byte the same as before; only the UI entry point moved.
 */
function AccountMenu({
  email,
  onSignOut,
  isPending,
}: {
  email: string;
  onSignOut: () => void;
  isPending?: boolean;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account menu"
        className="rounded-full outline-none transition-opacity duration-(--duration-micro) ease-meridian-out focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <Avatar label={email} size="sm" />
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuLabel>Signed in as</DropdownMenuLabel>
        <div className="max-w-56 truncate px-2.5 pb-1.5 text-small text-muted-foreground">{email}</div>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onSignOut} disabled={isPending}>
          <LogOut className="size-3.5" strokeWidth={1.5} aria-hidden />
          {isPending ? "Signing out…" : "Sign out"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export { AccountMenu };
