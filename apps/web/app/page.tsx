import { DeploymentCheckCard } from "@/components/deployment-check-card";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">Fleet Maintenance</h1>
        <p className="text-sm text-muted-foreground">
          Walking skeleton. The card below reads one row from PostgreSQL through
          the API, proving the browser → API → database path before any business
          logic exists.
        </p>
      </header>

      <DeploymentCheckCard />
    </main>
  );
}
