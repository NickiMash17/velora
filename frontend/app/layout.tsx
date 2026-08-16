import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Velora",
  description: "The Digital Workforce Platform",
};

/**
 * Meridian deliberately uses each OS's own native system-font stack rather
 * than an embedded custom typeface (docs/design/DesignSystem.md §5.1) — no
 * `next/font` loading here, `--font-sans`/`--font-mono` in globals.css are
 * literal font stacks.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
