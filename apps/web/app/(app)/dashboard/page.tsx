"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CompletionsChart } from "@/components/dashboard/completions-chart";
import { NewServiceModal } from "@/components/services/new-service-modal";
import { TransitionButton } from "@/components/services/transition-actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAlerts } from "@/hooks/use-alerts";
import { useCurrentUser } from "@/hooks/use-auth";
import { useDashboard } from "@/hooks/use-dashboard";
import { useVehicles } from "@/hooks/use-vehicles";
import { daysSince, formatMiles } from "@/lib/format";
import { cn } from "@/lib/utils";
import { STATUS_LABELS } from "@/types/service";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isLoading } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";

  // A technician's world is their own assignments; the API refuses them too.
  useEffect(() => {
    if (!isLoading && user && !isManager) router.replace("/my-work");
  }, [isLoading, user, isManager, router]);

  const { data, error, isPending, refetch } = useDashboard(Boolean(isManager));

  if (!isManager) return null;

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-base font-semibold">Fleet overview</h1>
        <p className="text-muted-foreground mt-0.5 text-sm">
          {data
            ? `${data.vehicles.total} active vehicles · ${data.services.open} open service records${
                data.vehicles.archived > 0
                  ? ` · ${data.vehicles.archived} archived`
                  : ""
              }`
            : " "}
        </p>
      </header>

      {error ? (
        <ErrorState message={error.message} onRetry={() => void refetch()} />
      ) : null}

      {isPending ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((tile) => (
            <Skeleton key={tile} className="h-[4.5rem] w-full" />
          ))}
        </div>
      ) : null}

      {data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {/* Each tile links to the list behind it: a number a manager
                cannot act on is decoration. */}
            <StatTile
              label="Due for service"
              value={data.vehicles.due}
              href="/vehicles?due=true"
              tone={data.vehicles.due > 0 ? "due" : "neutral"}
            />
            <StatTile
              label="Overdue"
              value={data.services.overdue}
              href="/alerts"
              tone={data.services.overdue > 0 ? "overdue" : "neutral"}
            />
            <StatTile
              label="In service"
              value={data.vehicles.in_service}
              href="/services?status=in_service"
              tone={data.vehicles.in_service > 0 ? "in_service" : "neutral"}
            />
            <StatTile
              label="Completed this week"
              value={data.services.completed_this_week}
              href="/services?status=completed"
              tone="neutral"
            />
          </div>

          <NeedsAttention />

          <div className="grid gap-4 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Records by status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2.5 text-sm">
                {data.by_status.every((row) => row.count === 0) ? (
                  <p className="text-muted-foreground">
                    No service records yet.
                  </p>
                ) : (
                  data.by_status.map((row) => (
                    <StatusBar
                      key={row.status}
                      status={row.status}
                      count={row.count}
                      total={data.by_status.reduce(
                        (sum, item) => sum + item.count,
                        0,
                      )}
                    />
                  ))
                )}
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Completed per week</CardTitle>
                <span className="text-muted-foreground text-xs">
                  Last eight ISO weeks, UTC
                </span>
              </CardHeader>
              <CardContent>
                <CompletionsChart data={data.completed_per_week} />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Technician workload</CardTitle>
              <span className="text-muted-foreground text-xs">
                Open records count against a technician until completed
              </span>
            </CardHeader>
            <CardContent className="p-0">
              {data.by_technician.length === 0 ? (
                <p className="text-muted-foreground p-4 text-sm">
                  No technicians yet.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Technician</TableHead>
                      <TableHead className="text-right">Open</TableHead>
                      <TableHead className="text-right">Completed</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.by_technician.map((row) => (
                      <TableRow key={row.technician_id}>
                        <TableCell className="font-medium">
                          {row.full_name}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {row.open}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-right tabular-nums">
                          {row.completed}
                        </TableCell>
                        <TableCell className="text-right">
                          <Link
                            href={`/services?technician_id=${row.technician_id}`}
                            className="text-muted-foreground hover:text-foreground text-xs"
                          >
                            View records
                          </Link>
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
    </div>
  );
}

/**
 * What a manager should do something about, with the action attached.
 *
 * Both halves are their own server queries - the five longest-overdue records
 * and the five vehicles the API says are due - rather than anything counted or
 * sliced here.
 */
function NeedsAttention() {
  const alerts = useAlerts(true, { limit: 5 });
  const due = useVehicles({ due: true, limit: 5 });
  const [openingFor, setOpeningFor] = useState<number | null>(null);

  const nothing =
    alerts.data?.items.length === 0 && due.data?.items.length === 0;

  if (nothing) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Needs attention</CardTitle>
        </CardHeader>
        <CardContent className="text-muted-foreground text-sm">
          Nothing overdue, and nothing due for service. The fleet is on
          schedule.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="border-overdue/30">
        <CardHeader>
          <CardTitle>Overdue records</CardTitle>
          <Link
            href="/alerts"
            className="text-muted-foreground hover:text-foreground text-xs"
          >
            All alerts
            {alerts.data && alerts.data.total > 5
              ? ` (${alerts.data.total})`
              : ""}
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          {alerts.isPending ? (
            <div className="p-4">
              <Skeleton className="h-16 w-full" />
            </div>
          ) : null}

          {alerts.data?.items.length === 0 ? (
            <p className="text-muted-foreground p-4 text-sm">
              Nothing has passed the grace period.
            </p>
          ) : null}

          <ul className="divide-y">
            {alerts.data?.items.map((service) => (
              <li
                key={service.id}
                className="flex items-center justify-between gap-3 px-4 py-2.5"
              >
                <div className="min-w-0">
                  <Link
                    href={`/services/${service.id}`}
                    className="text-sm font-medium hover:underline"
                  >
                    {service.vehicle.registration_number}
                  </Link>
                  <p className="text-muted-foreground truncate text-xs">
                    {service.description}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-overdue text-xs font-medium tabular-nums">
                    {service.overdue_since
                      ? `${daysSince(service.overdue_since)}d overdue`
                      : "Overdue"}
                  </span>
                  {/* Booking is the action that clears it - and the one the
                      API allows only a manager. */}
                  <TransitionButton
                    service={service}
                    isManager
                    size="sm"
                  />
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card className="border-due/30">
        <CardHeader>
          <CardTitle>Vehicles due for service</CardTitle>
          <Link
            href="/vehicles?due=true"
            className="text-muted-foreground hover:text-foreground text-xs"
          >
            All due
            {due.data && due.data.total > 5 ? ` (${due.data.total})` : ""}
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          {due.isPending ? (
            <div className="p-4">
              <Skeleton className="h-16 w-full" />
            </div>
          ) : null}

          {due.data?.items.length === 0 ? (
            <p className="text-muted-foreground p-4 text-sm">
              Nothing has reached its date or mileage interval.
            </p>
          ) : null}

          <ul className="divide-y">
            {due.data?.items.map((vehicle) => (
              <li
                key={vehicle.id}
                className="flex items-center justify-between gap-3 px-4 py-2.5"
              >
                <div className="min-w-0">
                  <Link
                    href={`/vehicles/${vehicle.id}`}
                    className="text-sm font-medium hover:underline"
                  >
                    {vehicle.registration_number}
                  </Link>
                  <p className="text-muted-foreground truncate text-xs">
                    {formatMiles(vehicle.current_odometer)} &middot; due on{" "}
                    {vehicle.service_status?.reason === "mileage"
                      ? "mileage"
                      : vehicle.service_status?.reason === "both"
                        ? "date and mileage"
                        : "date"}
                  </p>
                </div>

                {vehicle.service_status?.has_open_record ? (
                  <Link
                    href={`/services?vehicle_id=${vehicle.id}`}
                    className="text-muted-foreground hover:text-foreground shrink-0 text-xs"
                  >
                    Record open
                  </Link>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    className="shrink-0"
                    onClick={() => setOpeningFor(vehicle.id)}
                  >
                    Open record
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {openingFor !== null ? (
        <NewServiceModal
          open
          onClose={() => setOpeningFor(null)}
          vehicleId={openingFor}
        />
      ) : null}
    </div>
  );
}

const TILE_TONE = {
  neutral: "",
  due: "border-due/40 [&_p:last-child]:text-due",
  overdue: "border-overdue/40 [&_p:last-child]:text-overdue",
  in_service: "border-in-service/40 [&_p:last-child]:text-in-service",
} as const;

function StatTile({
  label,
  value,
  href,
  tone,
}: {
  label: string;
  value: number;
  href: string;
  tone: keyof typeof TILE_TONE;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "hover:bg-muted/40 block rounded-md border px-4 py-3 transition-colors duration-120",
        TILE_TONE[tone],
      )}
    >
      <p className="text-muted-foreground text-xs">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
    </Link>
  );
}

const BAR_COLOUR = {
  due: "bg-due",
  booked: "bg-booked",
  in_service: "bg-in-service",
  completed: "bg-completed",
} as const;

function StatusBar({
  status,
  count,
  total,
}: {
  status: keyof typeof BAR_COLOUR;
  count: number;
  total: number;
}) {
  const share = total === 0 ? 0 : Math.round((count / total) * 100);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <Link
          href={`/services?status=${status}`}
          className="hover:text-foreground flex items-center gap-2"
        >
          <Badge tone={status}>{STATUS_LABELS[status]}</Badge>
        </Link>
        <span className="text-muted-foreground text-xs tabular-nums">
          {count}
          <span className="ml-1 opacity-70">({share}%)</span>
        </span>
      </div>
      <div className="bg-muted h-1.5 w-full overflow-hidden rounded-full">
        <div
          className={cn("h-full rounded-full", BAR_COLOUR[status])}
          style={{ width: `${share}%` }}
          // The number is beside it, so the bar is for the eye rather than the
          // only way to read the value.
          aria-hidden
        />
      </div>
    </div>
  );
}
