"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { VehicleFormModal } from "@/components/vehicles/vehicle-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUser } from "@/hooks/use-auth";
import { useUpdateVehicle, useVehicle } from "@/hooks/use-vehicles";

export default function VehicleDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const { user } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";

  const { data: vehicle, error, isPending } = useVehicle(id);
  const update = useUpdateVehicle(id);
  const [editing, setEditing] = useState(false);

  if (isPending) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading vehicle">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="space-y-2">
        <p className="text-destructive font-medium">
          {error.status === 404 ? "No such vehicle" : "Could not load the vehicle"}
        </p>
        <p className="text-muted-foreground text-sm">{error.message}</p>
        <Link href="/vehicles" className="text-sm underline">
          Back to vehicles
        </Link>
      </div>
    );
  }

  return (
    <main className="space-y-6">
      <nav className="text-muted-foreground text-sm">
        <Link href="/vehicles" className="hover:underline">
          Vehicles
        </Link>
        <span className="px-2">/</span>
        <span>{vehicle.registration_number}</span>
      </nav>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold">
              {vehicle.registration_number}
            </h1>
            {vehicle.is_archived ? <Badge tone="neutral">ARCHIVED</Badge> : null}
          </div>
          <p className="text-muted-foreground text-sm">
            {vehicle.make} {vehicle.model}
          </p>
        </div>

        {/* Hidden for a technician because it would not work, not as the
            authorization itself - PATCH /vehicles/{id} refuses them anyway. */}
        {isManager && !vehicle.is_archived ? (
          <Button variant="ghost" onClick={() => setEditing(true)}>
            Edit
          </Button>
        ) : null}
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Odometer</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold tabular-nums">
              {vehicle.current_odometer.toLocaleString()}
              <span className="text-muted-foreground ml-1 text-sm font-normal">
                miles
              </span>
            </p>
            <p className="text-muted-foreground mt-1 text-xs">
              The latest recorded reading. It never goes down.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Service interval</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p className="tabular-nums">
              Every {vehicle.service_date_interval} days
            </p>
            <p className="tabular-nums">
              or {vehicle.service_mileage_interval.toLocaleString()} miles
            </p>
            <p className="text-muted-foreground text-xs">
              Whichever comes first, counted from the last completed service.
            </p>
          </CardContent>
        </Card>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Service history</h2>
        <p className="text-muted-foreground rounded-md border border-dashed px-4 py-8 text-center text-sm">
          Service records arrive with the next phase. Archiving a vehicle keeps
          its history, so nothing shown here is ever deleted.
        </p>
      </section>

      <VehicleFormModal
        open={editing}
        onClose={() => {
          setEditing(false);
          update.reset();
        }}
        vehicle={vehicle}
        onSubmit={(values) =>
          update.mutate(values, { onSuccess: () => setEditing(false) })
        }
        error={update.error}
        isPending={update.isPending}
      />
    </main>
  );
}
