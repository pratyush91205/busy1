"use client";

import Link from "next/link";

import { StatusBadge, accentFor } from "@/components/services/status-badge";
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
import { useServices } from "@/hooks/use-services";
import { formatDate, formatMiles } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Every cycle this vehicle has been through, newest first.
 *
 * Archiving a vehicle keeps this list: it is a soft delete precisely so the
 * history survives. A technician sees only the cycles they were assigned to,
 * because the server scopes the query, not this component.
 */
export function VehicleServiceHistory({ vehicleId }: { vehicleId: number }) {
  const { data, error, isPending, refetch } = useServices({
    vehicle_id: vehicleId,
    sort: "updated_at",
    order: "desc",
    limit: 20,
  });

  const more = data ? data.total > data.items.length : false;

  return (
    <section className="space-y-2">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Service history</h2>
          <p className="text-muted-foreground text-xs">
            {data
              ? `${data.total} ${data.total === 1 ? "cycle" : "cycles"} on record`
              : " "}
          </p>
        </div>

        {more ? (
          <Link
            href={`/services?vehicle_id=${vehicleId}`}
            className="text-muted-foreground hover:text-foreground text-xs"
          >
            View all {data?.total} records
          </Link>
        ) : null}
      </div>

      {isPending ? (
        <TableSkeleton label="Loading service history" rows={3} columns={5} />
      ) : null}

      {error ? (
        <ErrorState message={error.message} onRetry={() => void refetch()} />
      ) : null}

      {data && data.items.length === 0 ? (
        <EmptyState
          title="No service records for this vehicle yet"
          hint="Opening one starts a service cycle; completing it resets both intervals from the completion date and odometer."
        />
      ) : null}

      {data && data.items.length > 0 ? (
        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cycle</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Technicians</TableHead>
                <TableHead>Completed</TableHead>
                <TableHead>Closing odometer</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((service) => (
                <TableRow
                  key={service.id}
                  className={cn(
                    "border-l-2",
                    accentFor(service.status, service.is_overdue),
                  )}
                >
                  <TableCell className="font-medium">
                    <Link
                      href={`/services/${service.id}`}
                      className="hover:underline"
                    >
                      {service.cycle_number}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground max-w-xs truncate">
                    {service.description}
                  </TableCell>
                  <TableCell>
                    <StatusBadge
                      status={service.status}
                      isOverdue={service.is_overdue}
                    />
                  </TableCell>
                  <TableCell className="text-muted-foreground max-w-[12rem] truncate text-xs">
                    {service.technicians.length === 0
                      ? "Unassigned"
                      : service.technicians.map((t) => t.full_name).join(", ")}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {formatDate(service.completed_at)}
                  </TableCell>
                  <TableCell className="text-muted-foreground tabular-nums">
                    {formatMiles(service.completion_odometer)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}
    </section>
  );
}
