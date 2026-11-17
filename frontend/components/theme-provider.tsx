"use client";

import { ThemeProvider as NextThemeProvider } from "next-themes";
import type { ReactNode } from "react";

export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <NextThemeProvider
      attribute="data-theme"
      themes={["midnight", "light", "urban"]}
      defaultTheme="urban"
      enableSystem={false}
      storageKey="hire-archy-theme"
      disableTransitionOnChange
    >
      {children}
    </NextThemeProvider>
  );
}
