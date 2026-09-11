import { QueryClient } from "@tanstack/react-query";

/**
 * One query client per browser session. Created behind a function so the
 * provider can hold it in state rather than sharing a module-level client
 * between server renders.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
      },
    },
  });
}
