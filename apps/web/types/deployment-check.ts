/** Mirrors DeploymentCheckRead in apps/api/app/schemas/deployment_check.py. */
export interface DeploymentCheck {
  id: number;
  label: string;
  /** ISO-8601, UTC. */
  checked_at: string;
}
