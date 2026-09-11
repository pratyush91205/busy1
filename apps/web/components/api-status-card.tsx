"use client";

import { useQuery } from "@tanstack/react-query";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiFetch, configuredApiBaseUrl } from "@/lib/api-client";
import type { HealthStatus } from "@/types/health";

/**
 * Smoke check for the API and its database connection.
 *
 * Replaces the walking skeleton's deployment-check card, whose table was
 * dropped by migration 0002. /health needs no table, so this keeps a live
 * end-to-end signal until the real pages arrive with authentication.
 */
export function ApiStatusCard() {
  const { data, error, isPending, isFetching, refetch } = useQuery<
    HealthStatus,
    Error
  >({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthStatus>("/health"),
    retry: false,
  });

  const baseUrl = configuredApiBaseUrl();

  return (
    <Card className="w-full max-w-xl">
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-4 text-sm font-medium">
          <span>API status</span>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="rounded border px-2 py-1 text-xs font-normal text-muted-foreground hover:bg-muted disabled:opacity-50"
          >
            {isFetching ? "Checking…" : "Re-check"}
          </button>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        {isPending ? <LoadingState /> : null}
        {!isPending && error ? <ErrorState error={error} /> : null}
        {!isPending && !error && data ? <SuccessState health={data} /> : null}

        <p className="border-t pt-3 font-mono text-xs text-muted-foreground">
          API: {baseUrl ?? "not configured"}
        </p>
      </CardContent>
    </Card>
  );
}

function LoadingState() {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-4 w-1/3" />
    </div>
  );
}

function ErrorState({ error }: { error: Error }) {
  // A 503 is the API answering honestly that it cannot reach PostgreSQL, which
  // is a different problem from the API not answering at all.
  const unreachableDatabase = error instanceof ApiError && error.status === 503;

  const status =
    error instanceof ApiError && error.status > 0
      ? `HTTP ${error.status}`
      : "no response";

  return (
    <div role="alert" className="space-y-1">
      <p className="font-medium text-destructive">
        {unreachableDatabase ? "Database unreachable" : `Could not load (${status})`}
      </p>
      <p className="text-muted-foreground">{error.message}</p>
    </div>
  );
}

function SuccessState({ health }: { health: HealthStatus }) {
  return (
    <dl className="grid grid-cols-[7rem_1fr] gap-x-4 gap-y-2">
      <dt className="text-muted-foreground">API</dt>
      <dd className="font-medium">{health.status}</dd>

      <dt className="text-muted-foreground">Database</dt>
      <dd className="font-medium">{health.database}</dd>
    </dl>
  );
}
