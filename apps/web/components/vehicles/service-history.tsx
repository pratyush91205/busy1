"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/services/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useServices } from "@/hooks/use-services";

/**
 * Every cycle this vehicle has been through, newest first.
 *
 * Archiving a vehicle keeps this list: it is a soft delete precisely so the
 * history survives. A technician sees only the cycles they were assigned to,
 * because the server scopes the query, not this component.
 */
export function VehicleServiceHistory({ vehicleId }: { vehicleId: number }) {
  const { data, error, isPending } = useServices({
    vehicle_id: vehicleId,
    sort: "updated_at",
    order: "desc",
  });

  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold">Service history</h2>

      {isPending ? <Skeleton className="h-24 w-full" /> : null}

      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error.message}
        </p>
      ) : null}

      {data && data.items.length === 0 ? (
        <p className="text-muted-foreground rounded-md border border-dashed px-4 py-8 text-center text-sm">
          No service records for this vehicle yet.
        </p>
      ) : null}

      {data && data.items.length > 0 ? (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cycle</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Completed</TableHead>
                <TableHead>Odometer</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((service) => (
                <TableRow key={service.id}>
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
                    <StatusBadge status={service.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {service.completed_at
                      ? new Date(service.completed_at).toLocaleDateString()
                      : "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground tabular-nums">
                    {service.completion_odometer?.toLocaleString() ?? "—"}
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
