import { ApiStatusCard } from "@/components/api-status-card";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">Fleet Maintenance</h1>
        <p className="text-sm text-muted-foreground">
          The domain schema is in place. Sign-in and the fleet pages arrive with
          Phase 4; until then this card confirms the API can reach PostgreSQL.
        </p>
      </header>

      <ApiStatusCard />
    </main>
  );
}
