"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { CompletionsChart } from "@/components/dashboard/completions-chart";
import { TransitionButton } from "@/components/services/transition-actions";
import { Badge } from "@/components/ui/badge";
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
import { useServices } from "@/hooks/use-services";
import { daysSince } from "@/lib/format";
import { cn } from "@/lib/utils";
import { STATUS_LABELS, type ServiceRecord } from "@/types/service";

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
              href="/services?status=due"
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
 * Two server queries: the five longest-overdue records, and Due records still
 * inside their grace period. A vehicle that falls due opens its own cycle, so
 * both halves are records - and each row carries the booking that clears it.
 */
function NeedsAttention() {
  const alerts = useAlerts(true, { limit: 5 });
  const awaiting = useServices({
    status: "due",
    overdue: false,
    sort: "updated_at",
    order: "desc",
    limit: 5,
  });

  const nothing =
    alerts.data?.items.length === 0 && awaiting.data?.items.length === 0;

  if (nothing) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Needs attention</CardTitle>
        </CardHeader>
        <CardContent className="text-muted-foreground text-sm">
          Nothing overdue, and nothing waiting to be booked. The fleet is on
          schedule.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <AttentionList
        title="Overdue records"
        allHref="/alerts"
        allLabel="All alerts"
        tone="overdue"
        pending={alerts.isPending}
        total={alerts.data?.total}
        items={alerts.data?.items}
        empty="Nothing has passed the grace period."
        age={(service) =>
          service.overdue_since
            ? `${daysSince(service.overdue_since)}d overdue`
            : "Overdue"
        }
      />
      <AttentionList
        title="Awaiting booking"
        allHref="/services?status=due"
        allLabel="All due"
        tone="due"
        pending={awaiting.isPending}
        total={awaiting.data?.total}
        items={awaiting.data?.items}
        empty="Nothing is due and still inside its grace period."
        age={(service) =>
          service.due_since ? `due ${daysSince(service.due_since)}d` : "Due"
        }
      />
    </div>
  );
}

function AttentionList({
  title,
  allHref,
  allLabel,
  tone,
  pending,
  total,
  items,
  empty,
  age,
}: {
  title: string;
  allHref: string;
  allLabel: string;
  tone: "overdue" | "due";
  pending: boolean;
  total: number | undefined;
  items: ServiceRecord[] | undefined;
  empty: string;
  age: (service: ServiceRecord) => string;
}) {
  return (
    <Card className={tone === "overdue" ? "border-overdue/30" : "border-due/30"}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <Link
          href={allHref}
          className="text-muted-foreground hover:text-foreground text-xs"
        >
          {allLabel}
          {total !== undefined && total > 5 ? ` (${total})` : ""}
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        {pending ? (
          <div className="p-4">
            <Skeleton className="h-16 w-full" />
          </div>
        ) : null}

        {items?.length === 0 ? (
          <p className="text-muted-foreground p-4 text-sm">{empty}</p>
        ) : null}

        <ul className="divide-y">
          {items?.map((service) => (
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
                <span
                  className={cn(
                    "text-xs font-medium tabular-nums",
                    tone === "overdue" ? "text-overdue" : "text-due",
                  )}
                >
                  {age(service)}
                </span>
                {/* Booking is the action that clears either list - and the
                    one the API allows only a manager. */}
                <TransitionButton service={service} isManager size="sm" />
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
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
