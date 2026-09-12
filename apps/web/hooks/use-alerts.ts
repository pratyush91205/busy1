"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, type ApiError } from "@/lib/api-client";
import { toSearchParams } from "@/lib/query-string";
import type { ServiceRecord } from "@/types/service";
import type { Page } from "@/types/vehicle";

const ALERTS = ["alerts"] as const;

export interface AlertQuery {
  page?: number;
  limit?: number;
}

/** Undismissed overdue records, longest overdue first, one page at a time. */
export function useAlerts(enabled: boolean, query: AlertQuery = {}) {
  return useQuery<Page<ServiceRecord>, ApiError>({
    queryKey: [...ALERTS, "list", query],
    queryFn: () =>
      apiFetch<Page<ServiceRecord>>(`/alerts${toSearchParams(query)}`),
    enabled,
    placeholderData: (previous) => previous,
  });
}

/**
 * The count behind the nav badge.
 *
 * Polled rather than pushed. A count that is up to a minute stale is not a
 * correctness problem, because nothing acts on it - the alerts page re-reads
 * when opened, and dismissal is checked server-side.
 *
 * Manager-only, so `enabled` keeps a technician from asking for a guaranteed
 * 403 on a timer.
 */
export function useAlertCount(enabled: boolean) {
  return useQuery<{ count: number }, ApiError>({
    queryKey: [...ALERTS, "count"],
    queryFn: () => apiFetch<{ count: number }>("/alerts/count"),
    enabled,
    refetchInterval: 60_000,
  });
}

export function useDismissAlert() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, number>({
    mutationFn: async (serviceId) => {
      await apiFetch<void>(`/alerts/${serviceId}/dismiss`, { method: "POST" });
    },
    onSuccess: () => {
      // The list and the badge both come back from the server; neither is
      // decremented locally.
      void queryClient.invalidateQueries({ queryKey: ALERTS });
      // The record is unchanged - still due, still overdue - but any list
      // showing it should re-read so nothing looks fixed that is not.
      void queryClient.invalidateQueries({ queryKey: ["services"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
