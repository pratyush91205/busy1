"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch, type ApiError } from "@/lib/api-client";
import type { DashboardSummary } from "@/types/dashboard";

/**
 * The whole summary in one request.
 *
 * One call rather than six: the dashboard is one screen, so six round trips
 * would be six chances for a half-drawn answer.
 */
export function useDashboard(enabled: boolean) {
  return useQuery<DashboardSummary, ApiError>({
    queryKey: ["dashboard"],
    queryFn: () => apiFetch<DashboardSummary>("/dashboard"),
    enabled,
    staleTime: 30_000,
  });
}
