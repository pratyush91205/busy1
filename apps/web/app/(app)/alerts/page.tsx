"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAlerts, useDismissAlert } from "@/hooks/use-alerts";
import { useCurrentUser } from "@/hooks/use-auth";
import type { ServiceRecord } from "@/types/service";

export default function AlertsPage() {
  const router = useRouter();
  const { user, isLoading } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";

  const { data, error, isPending } = useAlerts(isManager);
  const dismiss = useDismissAlert();
  const [dismissing, setDismissing] = useState<ServiceRecord | null>(null);

  // A technician has no fleet-wide view; the API answers 403 either way.
  useEffect(() => {
    if (!isLoading && user && !isManager) router.replace("/services");
  }, [isLoading, user, isManager, router]);

  if (!isManager) return null;

  return (
    <main className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">Alerts</h1>
        <p className="text-muted-foreground text-sm">
          Service records still Due after the grace period, and not yet booked.
        </p>
      </header>

      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error.message}
        </p>
      ) : null}

      {isPending ? <Skeleton className="h-24 w-full" /> : null}

      {data && data.items.length === 0 ? (
        <p className="text-muted-foreground rounded-md border border-dashed px-4 py-10 text-center text-sm">
          Nothing overdue. Records that sit Due past the grace period appear
          here.
        </p>
      ) : null}

      {data && data.items.length > 0 ? (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Vehicle</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Overdue since</TableHead>
                <TableHead>Technicians</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((alert) => (
                <TableRow key={alert.id}>
                  <TableCell className="font-medium whitespace-nowrap">
                    <Link
                      href={`/services/${alert.id}`}
                      className="hover:underline"
                    >
                      {alert.vehicle.registration_number}
                    </Link>
                    <span className="text-muted-foreground ml-2 text-xs">
                      cycle {alert.cycle_number}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground max-w-xs truncate">
                    {alert.description}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {alert.overdue_since ? (
                      <>
                        <span className="tabular-nums">
                          {daysAgo(alert.overdue_since)} days
                        </span>
                        <span className="text-muted-foreground ml-2 text-xs">
                          since{" "}
                          {new Date(alert.overdue_since).toLocaleDateString()}
                        </span>
                      </>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs">
                    {alert.technicians.length === 0
                      ? "Unassigned"
                      : alert.technicians.map((t) => t.full_name).join(", ")}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      className="h-7 px-2 text-xs"
                      onClick={() => setDismissing(alert)}
                    >
                      Dismiss
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      <Modal
        open={dismissing !== null}
        onClose={() => {
          setDismissing(null);
          dismiss.reset();
        }}
        title={`Dismiss the alert for ${dismissing?.vehicle.registration_number}?`}
        description="This hides the alert. It does not book or service the vehicle - the record stays Due and stays overdue. When this cycle is completed and the next one runs past the grace period, a new alert will appear."
      >
        {dismiss.error ? (
          <p role="alert" className="text-destructive text-sm">
            {dismiss.error.message}
          </p>
        ) : null}

        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setDismissing(null)}>
            Cancel
          </Button>
          <Button
            disabled={dismiss.isPending}
            onClick={() =>
              dismissing &&
              dismiss.mutate(dismissing.id, {
                onSuccess: () => setDismissing(null),
              })
            }
          >
            {dismiss.isPending ? "Dismissing…" : "Dismiss alert"}
          </Button>
        </div>
      </Modal>
    </main>
  );
}

function daysAgo(iso: string): number {
  const elapsed = Date.now() - new Date(iso).getTime();
  return Math.max(0, Math.floor(elapsed / 86_400_000));
}
