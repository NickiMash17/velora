"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/form-error";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api-client";
import { useCreateOrganizationMutation } from "../api/use-create-organization";

export function CreateOrganizationForm() {
  const [name, setName] = useState("");
  const router = useRouter();
  const createMutation = useCreateOrganizationMutation();

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await createMutation.mutateAsync(name);
      router.replace("/dashboard");
    } catch {
      // Surfaced via createMutation.error below.
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="organization-name">Organization name</Label>
        <Input
          id="organization-name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          disabled={createMutation.isPending}
        />
      </div>
      {createMutation.isError && (
        <FormError>
          {createMutation.error instanceof ApiError
            ? createMutation.error.message
            : "Something went wrong. Please try again."}
        </FormError>
      )}
      <Button type="submit" disabled={createMutation.isPending}>
        {createMutation.isPending ? "Creating…" : "Create organization"}
      </Button>
    </form>
  );
}
