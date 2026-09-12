"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, type ApiError } from "@/lib/api-client";
import { toSearchParams } from "@/lib/query-string";
import type { Page } from "@/types/vehicle";
import type {
  AuditEvent,
  ServiceNote,
  ServiceQuery,
  ServiceRecord,
  TransitionInput,
} from "@/types/service";

const SERVICES = ["services"] as const;

export function useServices(query: ServiceQuery) {
  return useQuery<Page<ServiceRecord>, ApiError>({
    queryKey: [...SERVICES, "list", query],
    queryFn: () =>
      apiFetch<Page<ServiceRecord>>(`/services${toSearchParams(query)}`),
    placeholderData: (previous) => previous,
  });
}

export function useService(id: number) {
  return useQuery<ServiceRecord, ApiError>({
    queryKey: [...SERVICES, id],
    queryFn: () => apiFetch<ServiceRecord>(`/services/${id}`),
  });
}

export function useNotes(id: number) {
  return useQuery<ServiceNote[], ApiError>({
    queryKey: [...SERVICES, id, "notes"],
    queryFn: () => apiFetch<ServiceNote[]>(`/services/${id}/notes`),
  });
}

export function useTimeline(id: number) {
  return useQuery<AuditEvent[], ApiError>({
    queryKey: [...SERVICES, id, "timeline"],
    queryFn: () => apiFetch<AuditEvent[]>(`/services/${id}/timeline`),
  });
}

export function useCreateService() {
  const refresh = useRefreshServices();

  return useMutation<
    ServiceRecord,
    ApiError,
    { vehicle_id: number; description: string }
  >({
    mutationFn: (input) => post("/services", input),
    onSuccess: () => refresh(),
  });
}

export function useUpdateDescription(id: number) {
  const refresh = useRefreshServices();

  return useMutation<ServiceRecord, ApiError, string>({
    mutationFn: (description) =>
      apiFetch<ServiceRecord>(`/services/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description }),
      }),
    onSuccess: () => refresh(id),
  });
}

/**
 * One mutation for the whole lifecycle, matching the single transition
 * endpoint. Whether a move is legal, and whether this user may make it, are
 * both the server's answers - this only carries the request.
 */
export function useTransition(id: number) {
  const queryClient = useQueryClient();
  const refresh = useRefreshServices();

  return useMutation<ServiceRecord, ApiError, TransitionInput>({
    mutationFn: (input) => post(`/services/${id}/transition`, input),
    onSuccess: () => {
      refresh(id);
      // Completing raises the vehicle's odometer, so the fleet is stale too.
      void queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    },
  });
}

export function useAssignTechnician(id: number) {
  const refresh = useRefreshServices();

  return useMutation<ServiceRecord, ApiError, number>({
    mutationFn: (technician_id) =>
      post(`/services/${id}/technicians`, { technician_id }),
    onSuccess: () => refresh(id),
  });
}

export function useUnassignTechnician(id: number) {
  const refresh = useRefreshServices();

  return useMutation<void, ApiError, number>({
    mutationFn: async (technician_id) => {
      await apiFetch<void>(`/services/${id}/technicians/${technician_id}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => refresh(id),
  });
}

export function useAddNote(id: number) {
  const refresh = useRefreshServices();

  return useMutation<ServiceNote, ApiError, string>({
    mutationFn: (content) => post(`/services/${id}/notes`, { content }),
    onSuccess: () => refresh(id),
  });
}

function useRefreshServices() {
  const queryClient = useQueryClient();

  return (id?: number) => {
    void queryClient.invalidateQueries({ queryKey: SERVICES });
    if (id !== undefined) {
      void queryClient.invalidateQueries({ queryKey: [...SERVICES, id] });
    }
  };
}

function post<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

