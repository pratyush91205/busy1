"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, type ApiError } from "@/lib/api-client";
import type { Page, Vehicle, VehicleInput, VehicleQuery } from "@/types/vehicle";

const VEHICLES = ["vehicles"] as const;

/**
 * Filters go to the server, so they belong in the query key: page 2 of a
 * search is a different cached answer from page 2 of the whole fleet.
 */
export function useVehicles(query: VehicleQuery) {
  return useQuery<Page<Vehicle>, ApiError>({
    queryKey: [...VEHICLES, "list", query],
    queryFn: () => apiFetch<Page<Vehicle>>(`/vehicles${toSearchParams(query)}`),
    // Keeps the previous page on screen while the next one loads, instead of
    // collapsing the table to a spinner on every keystroke.
    placeholderData: (previous) => previous,
  });
}

export function useVehicle(id: number) {
  return useQuery<Vehicle, ApiError>({
    queryKey: [...VEHICLES, id],
    queryFn: () => apiFetch<Vehicle>(`/vehicles/${id}`),
  });
}

export function useCreateVehicle() {
  const invalidate = useInvalidateVehicles();

  return useMutation<Vehicle, ApiError, VehicleInput>({
    mutationFn: (input) =>
      apiFetch<Vehicle>("/vehicles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateVehicle(id: number) {
  const invalidate = useInvalidateVehicles();

  return useMutation<Vehicle, ApiError, Partial<VehicleInput>>({
    mutationFn: (changes) =>
      apiFetch<Vehicle>(`/vehicles/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(changes),
      }),
    onSuccess: invalidate,
  });
}

/** Archive and restore are the same shape; which one is a path, not a flag. */
export function useArchiveVehicle() {
  const invalidate = useInvalidateVehicles();

  return useMutation<Vehicle, ApiError, { id: number; archive: boolean }>({
    mutationFn: ({ id, archive }) =>
      apiFetch<Vehicle>(`/vehicles/${id}/${archive ? "archive" : "restore"}`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

function useInvalidateVehicles() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: VEHICLES });
  };
}

function toSearchParams(query: VehicleQuery): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    // Skip empty search and undefined; sending search= would match nothing
    // useful and makes two identical views cache under different keys.
    if (value === undefined || value === "") continue;
    params.set(key, String(value));
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}
