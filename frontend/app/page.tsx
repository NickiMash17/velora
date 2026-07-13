import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";

/**
 * Milestone 1 foundation-verification surface — NOT the product Landing
 * Page (see docs/product/WireframeSpec.md §3, which is a later milestone).
 * Its only job is to prove the design system foundation actually works:
 * typography/font tokens, the shadcn/ui component pipeline, and the
 * light/dark theme provider. It intentionally has no marketing content.
 */
export default function FoundationCheck() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <div className="flex w-full max-w-md items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Velora</h1>
        <ThemeToggle />
      </div>

      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Milestone 1 — Platform Foundation</CardTitle>
          <CardDescription>
            This page exists only to verify the frontend foundation renders correctly. It is not
            the product Landing Page.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            If this card is legibly styled, the theme toggle above switches between light and
            dark, and the button below responds — Tailwind, shadcn/ui, the font, and the theme
            provider are all wired correctly.
          </p>
          <Button>Foundation looks good</Button>
        </CardContent>
      </Card>
    </main>
  );
}
