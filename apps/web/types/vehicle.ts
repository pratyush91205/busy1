/** Mirrors app/schemas/vehicle.py and app/schemas/pagination.py. */

export interface Vehicle {
  id: number;
  registration_number: string;
  make: string;
  model: string;
  current_odometer: number;
  service_date_interval: number;
  service_mileage_interval: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export type VehicleSort =
  | "registration_number"
  | "current_odometer"
  | "created_at"
  | "updated_at";

export type SortOrder = "asc" | "desc";

export interface VehicleQuery {
  search?: string;
  include_archived?: boolean;
  sort?: VehicleSort;
  order?: SortOrder;
  page?: number;
  limit?: number;
}

/** The body of POST /vehicles, and of PATCH with every field optional. */
export interface VehicleInput {
  registration_number: string;
  make: string;
  model: string;
  current_odometer: number;
  service_date_interval: number;
  service_mileage_interval: number;
}
