/** Mirrors app/api/routes/dashboard.py. */

import type { ServiceStatus } from "@/types/service";

export interface DashboardSummary {
  vehicles: {
    total: number;
    due: number;
    in_service: number;
    archived: number;
  };
  services: {
    overdue: number;
    open: number;
    completed_this_week: number;
  };
  /** All four stored statuses, including those at zero. */
  by_status: { status: ServiceStatus; count: number }[];
  by_technician: {
    technician_id: number;
    full_name: string;
    open: number;
    completed: number;
  }[];
  /** Exactly eight ISO weeks, oldest first, zeros included. */
  completed_per_week: { week_start: string; count: number }[];
}
