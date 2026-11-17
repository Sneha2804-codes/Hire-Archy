import type { Metadata } from "next";
import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource-variable/plus-jakarta-sans";
import { AppProvider } from "@/components/app-provider";
import { AppFrame } from "@/components/app-frame";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hire-Archy | A clearer path to your next role",
  description: "Explore relevant jobs and understand the skills shaping the market.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <AppProvider>
            <AppFrame>{children}</AppFrame>
          </AppProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
