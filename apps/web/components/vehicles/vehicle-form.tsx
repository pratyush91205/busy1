"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Modal } from "@/components/ui/modal";
import type { ApiError } from "@/lib/api-client";
import type { Vehicle, VehicleInput } from "@/types/vehicle";

/**
 * Mirrors the bounds in app/schemas/vehicle.py. This is UX - it saves a round
 * trip on an obviously bad value. The server still rejects everything it
 * should, and a duplicate registration or a backwards odometer can only be
 * answered there, so those come back as 409s and are shown below.
 */
const vehicleSchema = z.object({
  registration_number: z.string().trim().min(1, "Required").max(32),
  make: z.string().trim().min(1, "Required").max(64),
  model: z.string().trim().min(1, "Required").max(64),
  current_odometer: z.coerce
    .number<number>()
    .int("Whole miles")
    .min(0, "Cannot be negative"),
  service_date_interval: z.coerce
    .number<number>()
    .int()
    .positive("Must be at least 1 day"),
  service_mileage_interval: z.coerce
    .number<number>()
    .int()
    .positive("Must be at least 1 mile"),
});

type VehicleValues = z.infer<typeof vehicleSchema>;

const BLANK: VehicleValues = {
  registration_number: "",
  make: "",
  model: "",
  current_odometer: 0,
  service_date_interval: 180,
  service_mileage_interval: 10000,
};

export function VehicleFormModal({
  open,
  onClose,
  vehicle,
  onSubmit,
  error,
  isPending,
}: {
  open: boolean;
  onClose: () => void;
  vehicle?: Vehicle;
  onSubmit: (values: VehicleInput) => void;
  error: ApiError | null;
  isPending: boolean;
}) {
  const editing = vehicle !== undefined;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<VehicleValues>({
    resolver: zodResolver(vehicleSchema),
    values: vehicle ? toValues(vehicle) : BLANK,
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editing ? `Edit ${vehicle.registration_number}` : "Add vehicle"}
      description={
        editing
          ? "The odometer can only go up. Intervals apply from the last completed service."
          : "Service intervals decide when this vehicle next becomes due."
      }
    >
      <form
        onSubmit={handleSubmit((values) => onSubmit(values))}
        noValidate
        className="space-y-4"
      >
        <Field
          id="registration_number"
          label="Registration"
          error={errors.registration_number?.message}
          {...register("registration_number")}
        />

        <div className="grid grid-cols-2 gap-3">
          <Field id="make" label="Make" error={errors.make?.message} {...register("make")} />
          <Field
            id="model"
            label="Model"
            error={errors.model?.message}
            {...register("model")}
          />
        </div>

        <Field
          id="current_odometer"
          label="Odometer (miles)"
          type="number"
          error={errors.current_odometer?.message}
          {...register("current_odometer")}
        />

        <div className="grid grid-cols-2 gap-3">
          <Field
            id="service_date_interval"
            label="Service every (days)"
            type="number"
            error={errors.service_date_interval?.message}
            {...register("service_date_interval")}
          />
          <Field
            id="service_mileage_interval"
            label="Service every (miles)"
            type="number"
            error={errors.service_mileage_interval?.message}
            {...register("service_mileage_interval")}
          />
        </div>

        {error ? (
          <p
            role="alert"
            className="border-destructive/40 bg-destructive/10 text-destructive rounded-md border px-3 py-2 text-sm"
          >
            {error.message}
          </p>
        ) : null}

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending ? "Saving…" : editing ? "Save changes" : "Add vehicle"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function Field({
  id,
  label,
  error,
  ...props
}: React.ComponentProps<"input"> & { id: string; label: string; error?: string }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        {...props}
      />
      {error ? (
        <p id={`${id}-error`} className="text-destructive text-xs">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function toValues(vehicle: Vehicle): VehicleValues {
  return {
    registration_number: vehicle.registration_number,
    make: vehicle.make,
    model: vehicle.model,
    current_odometer: vehicle.current_odometer,
    service_date_interval: vehicle.service_date_interval,
    service_mileage_interval: vehicle.service_mileage_interval,
  };
}
