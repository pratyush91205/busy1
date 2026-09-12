import type { User } from "@/types/auth";

/**
 * Where a role starts.
 *
 * A manager opens onto the fleet; a technician opens onto their own queue. One
 * function so that login, the root redirect and every manager-only page that
 * turns a technician away all agree on the destination.
 */
export function landingRouteFor(user: Pick<User, "role">): string {
  return user.role === "fleet_manager" ? "/dashboard" : "/my-work";
}
