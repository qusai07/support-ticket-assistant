"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AuthProvider } from "@/lib/auth";
import { I18nProvider, type Lang } from "@/lib/i18n";
import { ThemeProvider, type Theme } from "@/lib/theme";

export function Providers({ lang, theme, children }: { lang: Lang; theme: Theme; children: React.ReactNode }) {
  const [qc] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 10_000, refetchOnWindowFocus: true, retry: 1 } },
  }));
  return (
    <QueryClientProvider client={qc}>
      <I18nProvider initialLang={lang}>
        <ThemeProvider initialTheme={theme}>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </I18nProvider>
    </QueryClientProvider>
  );
}
