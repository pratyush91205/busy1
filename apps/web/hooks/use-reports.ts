"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiBaseUrl, apiFetch } from "@/lib/api-client";
import { readToken } from "@/lib/auth";
import type { ServiceQuery } from "@/types/service";

export interface OdometerRowResult {
  row: number;
  registration_number: string | null;
  status: "success" | "rejected";
  message: string;
  previous_odometer: number | null;
  new_odometer: number | null;
}

export interface OdometerUploadReport {
  total: number;
  succeeded: number;
  failed: number;
  results: OdometerRowResult[];
}

export function useOdometerUpload() {
  const queryClient = useQueryClient();

  return useMutation<OdometerUploadReport, ApiError, File>({
    mutationFn: (file) => {
      const body = new FormData();
      body.append("file", file);
      // No Content-Type header: the browser sets it with the multipart
      // boundary, and overriding it produces an unparseable request.
      return apiFetch<OdometerUploadReport>("/vehicles/odometer-upload", {
        method: "POST",
        body,
      });
    },
    onSuccess: () => {
      // Readings change odometers, which changes which vehicles are due.
      void queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    },
  });
}

/**
 * Download the export.
 *
 * Fetched rather than linked: an `<a download>` cannot carry an Authorization
 * header, and the endpoint is manager-only. So the bytes are fetched with the
 * token, turned into a blob, and handed to a temporary link.
 */
export async function downloadExport(query: ServiceQuery): Promise<void> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === "") continue;
    params.set(key, String(value));
  }

  const token = readToken();
  const response = await fetch(
    `${apiBaseUrl()}/services/export.csv?${params.toString()}`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );

  if (!response.ok) {
    throw new ApiError(response.status, "Could not generate the export.");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filenameFrom(response) ?? "service-history.csv";
  link.click();
  // Or the blob is held for the life of the page.
  URL.revokeObjectURL(url);
}

function filenameFrom(response: Response): string | null {
  const disposition = response.headers.get("content-disposition");
  const match = disposition?.match(/filename="([^"]+)"/);
  return match?.[1] ?? null;
}
