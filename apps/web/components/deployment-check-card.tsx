"use client";

import { useQuery } from "@tanstack/react-query";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiFetch, configuredApiBaseUrl } from "@/lib/api-client";
import type { DeploymentCheck } from "@/types/deployment-check";

/**
 * Proves the full path: browser -> API -> Postgres -> back.
 *
 * All four states are rendered explicitly. The error state is the one most
 * likely to be seen first in production, so it shows the status code and the
 * API's own message instead of a blank screen.
 */
export function DeploymentCheckCard() {
  const {
    data,
    error,
    isPending,
    isFetching,
    refetch,
  } = useQuery<DeploymentCheck, Error>({
    queryKey: ["deployment-check"],
    queryFn: () => apiFetch<DeploymentCheck>("/api/deployment-check"),
    retry: false,
  });

  const baseUrl = configuredApiBaseUrl();

  return (
    <Card className="w-full max-w-xl">
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-4 text-sm font-medium">
          <span>Deployment check</span>
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

        {!isPending && !error && data ? <SuccessState row={data} /> : null}

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
  // 404 is not a failure: the request reached the database and the seeded row
  // is genuinely absent, which is a different problem with a different fix.
  if (error instanceof ApiError && error.status === 404) {
    return (
      <div role="status" className="space-y-1">
        <p className="font-medium">No deployment check row</p>
        <p className="text-muted-foreground">{error.message}</p>
      </div>
    );
  }

  const status =
    error instanceof ApiError && error.status > 0
      ? `HTTP ${error.status}`
      : "no response";

  return (
    <div role="alert" className="space-y-1">
      <p className="font-medium text-destructive">Could not load ({status})</p>
      <p className="text-muted-foreground">{error.message}</p>
    </div>
  );
}

function SuccessState({ row }: { row: DeploymentCheck }) {
  return (
    <dl className="grid grid-cols-[7rem_1fr] gap-x-4 gap-y-2">
      <dt className="text-muted-foreground">Label</dt>
      <dd className="font-medium">{row.label}</dd>

      <dt className="text-muted-foreground">Row id</dt>
      <dd className="font-mono">{row.id}</dd>

      <dt className="text-muted-foreground">Checked at</dt>
      <dd className="font-mono">{formatUtc(row.checked_at)}</dd>
    </dl>
  );
}

/** Timestamps are stored and displayed in UTC, as the whole system will be. */
function formatUtc(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return `${parsed.toISOString().replace("T", " ").slice(0, 19)} UTC`;
}
