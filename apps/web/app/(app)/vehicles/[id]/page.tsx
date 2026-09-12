"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { NewServiceModal } from "@/components/services/new-service-modal";
import { VehicleServiceHistory } from "@/components/vehicles/service-history";
import { VehicleFormModal } from "@/components/vehicles/vehicle-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useCurrentUser } from "@/hooks/use-auth";
import { useUpdateVehicle, useVehicle } from "@/hooks/use-vehicles";
import { formatDate, formatMiles } from "@/lib/format";
import type { Vehicle, VehicleServiceStatus } from "@/types/vehicle";

export default function VehicleDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const { user } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";
  const toast = useToast();

  const { data: vehicle, error, isPending } = useVehicle(id);
  const update = useUpdateVehicle(id);
  const [editing, setEditing] = useState(false);
  const [opening, setOpening] = useState(false);

  if (isPending) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading vehicle">
        <Skeleton className="h-6 w-48" />
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="max-w-lg space-y-2">
        <p className="text-destructive font-medium">
          {error.status === 404
            ? "No such vehicle"
            : "Could not load the vehicle"}
        </p>
        <p className="text-muted-foreground text-sm">{error.message}</p>
        <Link href="/vehicles" className="inline-block text-sm underline">
          Back to vehicles
        </Link>
      </div>
    );
  }

  const status = vehicle.service_status;

  return (
    <div className="space-y-5">
      <nav className="text-muted-foreground text-sm">
        <Link href="/vehicles" className="hover:text-foreground">
          Vehicles
        </Link>
        <span className="px-1.5">/</span>
        <span className="text-foreground">{vehicle.registration_number}</span>
      </nav>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <h1 className="text-base font-semibold">
              {vehicle.registration_number}
            </h1>
            {vehicle.is_archived ? (
              <Badge tone="neutral">Archived</Badge>
            ) : status?.is_due ? (
              <Badge tone="due">Due</Badge>
            ) : null}
          </div>
          <p className="text-muted-foreground text-sm">
            {vehicle.make} {vehicle.model} &middot; added{" "}
            {formatDate(vehicle.created_at)}
          </p>
        </div>

        {/* Hidden for a technician because it would not work, not as the
            authorization itself - PATCH /vehicles/{id} refuses them anyway. */}
        {isManager && !vehicle.is_archived ? (
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setEditing(true)}>
              Edit vehicle
            </Button>
            <Button onClick={() => setOpening(true)}>Open service record</Button>
          </div>
        ) : null}
      </header>

      {vehicle.is_archived ? (
        <p className="text-muted-foreground rounded-md border border-dashed px-4 py-3 text-sm">
          This vehicle is archived. Its history is kept and stays readable; it
          takes no edits and no new service records until it is restored.
        </p>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Current odometer</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold tabular-nums">
              {vehicle.current_odometer.toLocaleString()}
              <span className="text-muted-foreground ml-1 text-sm font-normal">
                miles
              </span>
            </p>
            <p className="text-muted-foreground mt-1 text-xs">
              The latest recorded reading, and the one a bulk upload has to
              beat. It never goes down.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Service interval</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p className="tabular-nums">
              Every{" "}
              <span className="font-medium">
                {vehicle.service_date_interval} days
              </span>
            </p>
            <p className="tabular-nums">
              or every{" "}
              <span className="font-medium">
                {vehicle.service_mileage_interval.toLocaleString()} miles
              </span>
            </p>
            <p className="text-muted-foreground pt-1 text-xs">
              Whichever comes first. Both are reset by a completed service.
            </p>
          </CardContent>
        </Card>

        <NextServiceCard vehicle={vehicle} status={status} />
      </div>

      <VehicleServiceHistory vehicleId={id} />

      <VehicleFormModal
        open={editing}
        onClose={() => {
          setEditing(false);
          update.reset();
        }}
        vehicle={vehicle}
        onSubmit={(values) =>
          update.mutate(values, {
            onSuccess: () => {
              setEditing(false);
              toast("Vehicle updated");
            },
          })
        }
        error={update.error}
        isPending={update.isPending}
      />

      {isManager ? (
        <NewServiceModal
          open={opening}
          onClose={() => setOpening(false)}
          vehicleId={id}
        />
      ) : null}
    </div>
  );
}

function NextServiceCard({
  vehicle,
  status,
}: {
  vehicle: Vehicle;
  status: VehicleServiceStatus | null;
}) {
  return (
    <Card className={status?.is_due && !vehicle.is_archived ? "border-due/40" : ""}>
      <CardHeader>
        <CardTitle>Next service</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {vehicle.is_archived || !status ? (
          <p className="text-muted-foreground">
            Archived vehicles are not in service, so they never become due.
          </p>
        ) : status.is_due ? (
          <p className="text-due font-medium">
            Due now &mdash; {explain(status.reason)}.
          </p>
        ) : (
          <p>On schedule.</p>
        )}

        {status && !vehicle.is_archived ? (
          <dl className="text-muted-foreground grid grid-cols-[7.5rem_1fr] gap-x-3 gap-y-1 text-xs">
            <dt>Due on or after</dt>
            <dd className="tabular-nums">{formatDate(status.next_due_date)}</dd>
            <dt>Or at odometer</dt>
            <dd className="tabular-nums">
              {formatMiles(status.next_due_odometer)}
            </dd>
            <dt>Counting from</dt>
            <dd className="tabular-nums">
              {formatDate(vehicle.service_baseline_date)} &middot;{" "}
              {formatMiles(vehicle.service_baseline_odometer)}
            </dd>
          </dl>
        ) : null}

        {status?.has_open_record ? (
          <p className="text-muted-foreground border-t pt-2 text-xs">
            A service record is already open for this vehicle.
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

/** Either interval makes a vehicle due; they are not required together. */
function explain(reason: VehicleServiceStatus["reason"]): string {
  switch (reason) {
    case "date":
      return "the date interval has been reached";
    case "mileage":
      return "the mileage interval has been reached";
    case "both":
      return "both intervals have been reached";
    default:
      return "";
  }
}
