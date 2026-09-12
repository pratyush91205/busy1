"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { TransitionButton } from "@/components/services/transition-actions";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { useAlerts, useDismissAlert } from "@/hooks/use-alerts";
import { useCurrentUser } from "@/hooks/use-auth";
import { useQueryParams } from "@/hooks/use-query-params";
import { daysSince, formatDate } from "@/lib/format";
import type { ServiceRecord } from "@/types/service";

export default function AlertsPage() {
  return (
    <Suspense fallback={<TableSkeleton label="Loading alerts" columns={5} />}>
      <AlertsView />
    </Suspense>
  );
}

function AlertsView() {
  const router = useRouter();
  const { params, setParams } = useQueryParams("/alerts");
  const { user, isLoading } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";
  const toast = useToast();

  const { data, error, isPending, refetch } = useAlerts(Boolean(isManager), {
    page: Number(params.get("page")) || 1,
    limit: Number(params.get("limit")) || 20,
  });
  const dismiss = useDismissAlert();
  const [dismissing, setDismissing] = useState<ServiceRecord | null>(null);

  // A technician has no fleet-wide view; the API answers 403 either way.
  useEffect(() => {
    if (!isLoading && user && !isManager) router.replace("/my-work");
  }, [isLoading, user, isManager, router]);

  if (!isManager) return null;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-base font-semibold">Overdue alerts</h1>
        <p className="text-muted-foreground mt-0.5 text-sm">
          Records still Due after the grace period, and not yet booked. Booking
          one clears it; dismissing one only hides it for this service cycle.
        </p>
      </header>

      {error ? (
        <ErrorState message={error.message} onRetry={() => void refetch()} />
      ) : null}

      {isPending ? <TableSkeleton label="Loading alerts" columns={5} /> : null}

      {data && data.items.length === 0 ? (
        <EmptyState
          title="Nothing overdue"
          hint="A record that sits Due past the grace period without being booked appears here, and the count beside Alerts in the sidebar matches."
        />
      ) : null}

      {data && data.items.length > 0 ? (
        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Vehicle</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Overdue</TableHead>
                <TableHead>Technicians</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((alert) => (
                <TableRow key={alert.id} className="border-l-overdue border-l-2">
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
                        <span className="text-overdue font-medium tabular-nums">
                          {daysSince(alert.overdue_since)} days
                        </span>
                        <span className="text-muted-foreground ml-2 text-xs">
                          since {formatDate(alert.overdue_since)}
                        </span>
                      </>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground max-w-[12rem] truncate text-xs">
                    {alert.technicians.length === 0
                      ? "Unassigned"
                      : alert.technicians.map((t) => t.full_name).join(", ")}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-2">
                      {/* Booking is the fix; dismissing is the acknowledgement.
                          Both are a manager's, and the API says so. */}
                      <TransitionButton service={alert} isManager size="sm" />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDismissing(alert)}
                      >
                        Dismiss
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      {data && data.total > 0 ? (
        <Pagination
          page={data}
          label="alerts"
          onPage={(page) => setParams({ page })}
        />
      ) : null}

      <Modal
        open={dismissing !== null}
        onClose={() => {
          setDismissing(null);
          dismiss.reset();
        }}
        title={`Dismiss the alert for ${dismissing?.vehicle.registration_number ?? ""}?`}
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
                onSuccess: () => {
                  toast(
                    `Alert dismissed for ${dismissing.vehicle.registration_number}`,
                  );
                  setDismissing(null);
                },
              })
            }
          >
            {dismiss.isPending ? "Dismissing…" : "Dismiss alert"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
