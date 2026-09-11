/** Mirrors app/schemas/auth.py. */

export type UserRole = "fleet_manager" | "technician";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  fleet_manager: "Fleet Manager",
  technician: "Technician",
};
