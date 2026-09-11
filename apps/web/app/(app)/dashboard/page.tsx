"use client";

import { ApiStatusCard } from "@/components/api-status-card";
import { useCurrentUser } from "@/hooks/use-auth";
import { ROLE_LABELS } from "@/types/auth";

/**
 * A placeholder until Phase 15 builds the real dashboard. It shows the one
 * thing Phase 4 can honestly show: who the server says you are.
 */
export default function DashboardPage() {
  const { user } = useCurrentUser();

  return (
    <main className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">Dashboard</h1>
        <p className="text-muted-foreground text-sm">
          {user
            ? `Signed in as ${user.email} (${ROLE_LABELS[user.role]}).`
            : null}{" "}
          Fleet metrics arrive with the dashboard phase; vehicles and service
          records come first.
        </p>
      </header>

      <ApiStatusCard />
    </main>
  );
}
