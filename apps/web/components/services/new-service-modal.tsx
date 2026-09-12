"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Modal } from "@/components/ui/modal";
import { Textarea } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { VehiclePicker } from "@/components/vehicles/vehicle-picker";
import { useCreateService } from "@/hooks/use-services";

/**
 * Open a service record against a vehicle.
 *
 * Manager-only, and the server agrees: POST /services refuses a technician.
 * The record always starts Due - there is no status to choose here, because
 * choosing one would be skipping the lifecycle.
 */
export function NewServiceModal({
  open,
  onClose,
  vehicleId,
}: {
  open: boolean;
  onClose: () => void;
  /** Fixes the vehicle when opened from that vehicle's own page. */
  vehicleId?: number;
}) {
  const router = useRouter();
  const toast = useToast();
  const create = useCreateService();

  const [vehicle, setVehicle] = useState<number | undefined>(vehicleId);
  const [description, setDescription] = useState("");

  const chosen = vehicleId ?? vehicle;

  function close() {
    create.reset();
    setDescription("");
    setVehicle(vehicleId);
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Open a service record"
      description="It starts Due, and the overdue clock starts now."
    >
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (chosen === undefined) return;

          create.mutate(
            { vehicle_id: chosen, description },
            {
              onSuccess: (service) => {
                toast("Service record opened");
                close();
                router.push(`/services/${service.id}`);
              },
            },
          );
        }}
      >
        {vehicleId === undefined ? (
          <div className="space-y-1.5">
            <Label htmlFor="new-service-vehicle">Vehicle</Label>
            <VehiclePicker
              id="new-service-vehicle"
              value={vehicle}
              onChange={setVehicle}
              placeholder="Search by registration"
            />
            <p className="text-muted-foreground text-xs">
              {/* Archived vehicles are excluded: the API refuses a new record
                  against one, so offering it would be offering a 409. */}
              Archived vehicles cannot take new service records.
            </p>
          </div>
        ) : null}

        <div className="space-y-1.5">
          <Label htmlFor="new-service-description">Description</Label>
          <Textarea
            id="new-service-description"
            required
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Brake inspection"
          />
        </div>

        {create.error ? (
          <p
            role="alert"
            className="border-destructive/40 bg-destructive/10 text-destructive rounded-md border px-3 py-2 text-sm"
          >
            {create.error.message}
          </p>
        ) : null}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={close}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={
              create.isPending || chosen === undefined || description.trim() === ""
            }
          >
            {create.isPending ? "Opening…" : "Open record"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
