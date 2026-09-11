/** Mirrors the response of GET /health in apps/api/app/api/routes/health.py. */
export interface HealthStatus {
  status: "ok" | "degraded";
  database: "ok" | "unreachable";
}
