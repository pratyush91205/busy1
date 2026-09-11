"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch, type ApiError } from "@/lib/api-client";
import type { UserSummary } from "@/types/service";

/**
 * The technician roster, for the assignment picker.
 *
 * `enabled` because only a fleet manager may read it - asking as a technician
 * would be a guaranteed 403, and a 403 on a request that carried a token is
 * indistinguishable from nothing useful.
 */
export function useTechnicians(enabled: boolean) {
  return useQuery<UserSummary[], ApiError>({
    queryKey: ["technicians"],
    queryFn: () => apiFetch<UserSummary[]>("/technicians"),
    enabled,
    staleTime: 5 * 60_000,
  });
}
