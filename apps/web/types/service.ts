/** Mirrors app/schemas/service.py. */

import type { Vehicle } from "@/types/vehicle";

/**
 * The four stored statuses. Overdue is not one of them - it is derived from
 * `due` plus `due_since` plus the grace period, and is rendered as a badge
 * only. Any filter or transition still names one of these four.
 */
export type ServiceStatus = "due" | "booked" | "in_service" | "completed";

export const STATUS_LABELS: Record<ServiceStatus, string> = {
  due: "DUE",
  booked: "BOOKED",
  in_service: "IN SERVICE",
  completed: "COMPLETED",
};

/** The lifecycle, in order, for the progress display. */
export const LIFECYCLE: ServiceStatus[] = [
  "due",
  "booked",
  "in_service",
  "completed",
];

export interface UserSummary {
  id: number;
  full_name: string;
  email: string;
}

export interface ServiceRecord {
  id: number;
  vehicle: Pick<Vehicle, "id" | "registration_number" | "make" | "model">;
  cycle_number: number;
  description: string;
  status: ServiceStatus;
  scheduled_date: string | null;
  due_since: string | null;
  completed_at: string | null;
  completion_odometer: number | null;
  technicians: UserSummary[];
  created_at: string;
  updated_at: string;

  /** Derived server-side: status `due` plus an elapsed grace period. */
  is_overdue: boolean;
  overdue_since: string | null;
}

export interface ServiceNote {
  id: number;
  content: string;
  author: UserSummary;
  created_at: string;
}

export interface AuditEvent {
  id: number;
  event_type:
    | "service_created"
    | "status_changed"
    | "technician_assigned"
    | "technician_unassigned"
    | "note_added";
  old_value: string | null;
  new_value: string | null;
  event_metadata: Record<string, unknown> | null;
  /** Null means the system acted rather than a person. */
  actor: UserSummary | null;
  created_at: string;
}

export type ServiceSort = "scheduled_date" | "status" | "updated_at";

export interface ServiceQuery {
  search?: string;
  overdue?: boolean;
  vehicle_id?: number;
  status?: ServiceStatus;
  technician_id?: number;
  sort?: ServiceSort;
  order?: "asc" | "desc";
  page?: number;
}

export interface TransitionInput {
  status: ServiceStatus;
  scheduled_date?: string;
  completion_odometer?: number;
}
