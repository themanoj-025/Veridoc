"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

/**
 * F14: React Query provider that wraps the app so child components can
 * use ``useQuery`` / ``useMutation`` hooks.
 *
 * We lazy-create the ``QueryClient`` inside component state so that
 * each request in SSR/SSG gets its own instance (avoids stale state
 * leaking across renders).
 */
export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000, // 30s — refetch after this duration
            gcTime: 5 * 60_000, // 5 min — keep unused data in cache
            retry: 1,
            refetchOnWindowFocus: true,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
