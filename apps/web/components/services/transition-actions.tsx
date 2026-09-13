"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { useTransition } from "@/hooks/use-services";
import { useTechnicians } from "@/hooks/use-technicians";
import { useVehicle } from "@/hooks/use-vehicles";
import { formatMiles } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ServiceRecord, ServiceStatus } from "@/types/service";

/**
 * The one legal next step, if there is one.
 *
 * The lifecycle is linear, so there is never a choice of destination - only
 * whether this user may take it. Booking is a manager's, because it sets the
 * schedule; starting and completing are the work, so an assigned technician
 * may do those.
 *
 * Hiding a button the user may not press is a courtesy. The server refuses it
 * either way, which is what the 403 tests assert.
 */
const NEXT: Record<ServiceStatus, ServiceStatus | null> = {
  due: "booked",
  booked: "in_service",
  in_service: "completed",
  completed: null,
};

const MANAGER_ONLY: ServiceStatus[] = ["booked"];

/** What the button says - the action, not the destination state. */
const ACTION_LABEL: Record<ServiceStatus, string> = {
  due: "Mark due",
  booked: "Book service",
  in_service: "Start work",
  completed: "Complete service",
};

export function nextStatusFor(status: ServiceStatus): ServiceStatus | null {
  return NEXT[status];
}

export function mayTransition(
  status: ServiceStatus,
  isManager: boolean,
): boolean {
  const next = NEXT[status];
  if (next === null) return false;
  return isManager || !MANAGER_ONLY.includes(next);
}

/**
 * The button that moves a record one step, with whatever the step needs.
 *
 * Booking needs a date; completing needs the closing odometer. Both are asked
 * for in a dialog rather than assumed, and both are validated again by the
 * server - the completion reading against the vehicle's current one, the
 * transition against the lifecycle table.
 */
export function TransitionButton({
  service,
  isManager,
  size = "md",
  className,
}: {
  service: ServiceRecord;
  isManager: boolean;
  size?: "sm" | "md";
  className?: string;
}) {
  const move = useTransition(service.id);
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [scheduledDate, setScheduledDate] = useState("");
  const [odometer, setOdometer] = useState("");
  const [technicianId, setTechnicianId] = useState("");

  const next = NEXT[service.status];
  // Only loaded when it is about to be needed: the completion dialog shows the
  // reading the new one has to beat.
  const vehicle = useVehicle(service.vehicle.id, open && next === "completed");
  // Booking assigns a technician as well as a date. Only a manager books, and
  // only a manager may read the roster.
  const roster = useTechnicians(isManager && open && next === "booked");
  const assignedNames = service.technicians.map((t) => t.full_name).join(", ");

  if (next === null || !mayTransition(service.status, isManager)) return null;

  const needsInput = next === "booked" || next === "completed";

  function submit() {
    if (next === null) return;

    move.mutate(
      {
        status: next,
        ...(next === "booked"
          ? {
              scheduled_date: scheduledDate,
              ...(technicianId ? { technician_id: Number(technicianId) } : {}),
            }
          : {}),
        ...(next === "completed"
          ? { completion_odometer: Number(odometer) }
          : {}),
      },
      {
        onSuccess: (updated) => {
          setOpen(false);
          setScheduledDate("");
          setOdometer("");
          setTechnicianId("");
          toast(
            updated.status === "completed"
              ? "Service completed - the next cycle counts from here"
              : `Moved to ${updated.status === "in_service" ? "In Service" : "Booked"}`,
          );
        },
      },
    );
  }

  return (
    <>
      <Button
        size={size}
        className={className}
        disabled={move.isPending}
        onClick={() => (needsInput ? setOpen(true) : submit())}
      >
        {move.isPending ? "Working…" : ACTION_LABEL[next]}
      </Button>

      {/* A failure outside the dialog still has to be visible, and the
          server's own wording is the useful part of it. */}
      {move.error && !open ? (
        <p role="alert" className="text-destructive mt-2 w-full text-sm">
          {move.error.message}
        </p>
      ) : null}

      <Modal
        open={open}
        onClose={() => {
          setOpen(false);
          move.reset();
        }}
        title={next === "booked" ? "Book this service" : "Complete this service"}
        description={
          next === "booked"
            ? "Booking sets the date and who does the work. It also stops the overdue clock for this cycle."
            : "The completion reading becomes the vehicle's odometer and starts the next mileage interval. It cannot be lower than the vehicle's current reading."
        }
      >
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          {next === "booked" ? (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="scheduled_date">Scheduled date</Label>
                <Input
                  id="scheduled_date"
                  type="date"
                  required
                  className="h-9"
                  value={scheduledDate}
                  onChange={(event) => setScheduledDate(event.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="booking_technician">Technician</Label>
                <Select
                  id="booking_technician"
                  // Required only when nobody is assigned yet - the server
                  // refuses a booking with no technician on the record.
                  required={service.technicians.length === 0}
                  value={technicianId}
                  onChange={(event) => setTechnicianId(event.target.value)}
                  className="h-9 w-full"
                >
                  <option value="">
                    {service.technicians.length > 0
                      ? `Keep ${assignedNames}`
                      : roster.isPending
                        ? "Loading technicians…"
                        : "Choose a technician"}
                  </option>
                  {roster.data?.map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.full_name}
                    </option>
                  ))}
                </Select>
              </div>
            </>
          ) : (
            <div className="space-y-1.5">
              <Label htmlFor="completion_odometer">Completion odometer</Label>
              <Input
                id="completion_odometer"
                type="number"
                min={vehicle.data?.current_odometer ?? 0}
                required
                className="h-9"
                value={odometer}
                onChange={(event) => setOdometer(event.target.value)}
              />
              {vehicle.data ? (
                <p className="text-muted-foreground text-xs">
                  Current reading: {formatMiles(vehicle.data.current_odometer)}
                </p>
              ) : null}
            </div>
          )}

          {move.error ? (
            <p
              role="alert"
              className="border-destructive/40 bg-destructive/10 text-destructive rounded-md border px-3 py-2 text-sm"
            >
              {move.error.message}
            </p>
          ) : null}

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setOpen(false);
                move.reset();
              }}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={move.isPending}>
              {move.isPending ? "Working…" : ACTION_LABEL[next]}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}

/**
 * The next step, as a strip across the service detail page: what happens next,
 * who may do it, and the button if that is this user.
 */
export function TransitionPanel({
  service,
  isManager,
  className,
}: {
  service: ServiceRecord;
  isManager: boolean;
  className?: string;
}) {
  const next = NEXT[service.status];

  if (next === null) {
    return (
      <div
        className={cn(
          "border-completed/30 bg-completed-soft rounded-md border px-4 py-3",
          className,
        )}
      >
        <p className="text-completed text-sm font-medium">
          This cycle is complete.
        </p>
        <p className="text-completed/90 mt-0.5 text-sm">
          The vehicle&rsquo;s next service interval counts from its completion
          date and odometer, not from when the vehicle was added.
        </p>
      </div>
    );
  }

  const allowed = mayTransition(service.status, isManager);

  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 rounded-md border px-4 py-3",
        className,
      )}
    >
      <div>
        <p className="text-sm font-medium">Next step: {ACTION_LABEL[next]}</p>
        <p className="text-muted-foreground mt-0.5 text-sm">
          {allowed
            ? next === "booked"
              ? "Booking sets the date this service is scheduled for."
              : next === "in_service"
                ? "Start work when the vehicle is in the bay."
                : "Completing records the closing odometer and resets both counters."
            : "Booking is a fleet manager's action - it sets the schedule."}
        </p>
      </div>

      <TransitionButton service={service} isManager={isManager} />
    </div>
  );
}
