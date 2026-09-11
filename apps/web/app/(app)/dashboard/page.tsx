"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { CompletionsChart } from "@/components/dashboard/completions-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCurrentUser } from "@/hooks/use-auth";
import { useDashboard } from "@/hooks/use-dashboard";
import { STATUS_LABELS } from "@/types/service";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isLoading } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";

  // A technician's world is their own assignments; the API refuses them too.
  useEffect(() => {
    if (!isLoading && user && !isManager) router.replace("/services");
  }, [isLoading, user, isManager, router]);

  const { data, error, isPending } = useDashboard(isManager);

  if (!isManager) return null;

  return (
    <main className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">Dashboard</h1>
        <p className="text-muted-foreground text-sm">
          {data
            ? `${data.vehicles.total} vehicles in service, ${data.services.open} open records.`
            : "Loading the fleet…"}
        </p>
      </header>

      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error.message}
        </p>
      ) : null}

      {isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((tile) => (
            <Skeleton key={tile} className="h-24 w-full" />
          ))}
        </div>
      ) : null}

      {data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Each tile links to the list behind it: a number a manager
                cannot act on is decoration. */}
            <StatTile
              label="Due for service"
              value={data.vehicles.due}
              href="/vehicles?due=true"
              tone={data.vehicles.due > 0 ? "warning" : "neutral"}
            />
            <StatTile
              label="Overdue"
              value={data.services.overdue}
              href="/alerts"
              tone={data.services.overdue > 0 ? "danger" : "neutral"}
            />
            <StatTile
              label="In service"
              value={data.vehicles.in_service}
              href="/services?status=in_service"
              tone="neutral"
            />
            <StatTile
              label="Completed this week"
              value={data.services.completed_this_week}
              href="/services?status=completed"
              tone="neutral"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">
                  Records by status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {data.by_status.every((row) => row.count === 0) ? (
                  <p className="text-muted-foreground">No service records yet.</p>
                ) : (
                  data.by_status.map((row) => (
                    <StatusBar
                      key={row.status}
                      label={STATUS_LABELS[row.status]}
                      count={row.count}
                      total={data.by_status.reduce((sum, r) => sum + r.count, 0)}
                    />
                  ))
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">
                  Completed per week
                </CardTitle>
              </CardHeader>
              <CardContent>
                <CompletionsChart data={data.completed_per_week} />
                <p className="text-muted-foreground mt-2 text-xs">
                  The last eight ISO weeks, in UTC. Quiet weeks are shown as
                  zero rather than left out.
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Technician workload
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data.by_technician.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No technicians yet.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Technician</TableHead>
                      <TableHead>Open</TableHead>
                      <TableHead>Completed</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.by_technician.map((row) => (
                      <TableRow key={row.technician_id}>
                        <TableCell className="font-medium">
                          {row.full_name}
                        </TableCell>
                        <TableCell className="tabular-nums">
                          <Link
                            href={`/services?technician_id=${row.technician_id}`}
                            className="hover:underline"
                          >
                            {row.open}
                          </Link>
                        </TableCell>
                        <TableCell className="text-muted-foreground tabular-nums">
                          {row.completed}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </main>
  );
}

function StatTile({
  label,
  value,
  href,
  tone,
}: {
  label: string;
  value: number;
  href: string;
  tone: "neutral" | "warning" | "danger";
}) {
  const accent =
    tone === "danger"
      ? "text-red-700 dark:text-red-300"
      : tone === "warning"
        ? "text-amber-700 dark:text-amber-300"
        : "text-foreground";

  return (
    <Link href={href} className="block">
      <Card className="hover:bg-muted/40 h-full transition-colors">
        <CardContent className="space-y-1 px-4">
          <p className="text-muted-foreground text-xs">{label}</p>
          <p className={`text-3xl font-semibold tabular-nums ${accent}`}>
            {value}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}

function StatusBar({
  label,
  count,
  total,
}: {
  label: string;
  count: number;
  total: number;
}) {
  const share = total === 0 ? 0 : Math.round((count / total) * 100);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span>{label}</span>
        <span className="text-muted-foreground tabular-nums">{count}</span>
      </div>
      <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
        <div
          className="bg-foreground/70 h-full rounded-full"
          style={{ width: `${share}%` }}
          // The number is beside it, so the bar is decoration for the eye
          // rather than the only way to read the value.
          aria-hidden
        />
      </div>
    </div>
  );
}
