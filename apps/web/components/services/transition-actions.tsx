"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Modal } from "@/components/ui/modal";
import { useTransition } from "@/hooks/use-services";
import { STATUS_LABELS, type ServiceRecord, type ServiceStatus } from "@/types/service";

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

export function TransitionActions({
  service,
  isManager,
}: {
  service: ServiceRecord;
  isManager: boolean;
}) {
  const move = useTransition(service.id);
  const [open, setOpen] = useState(false);
  const [scheduledDate, setScheduledDate] = useState("");
  const [odometer, setOdometer] = useState("");

  const next = NEXT[service.status];

  if (next === null) {
    return (
      <p className="text-muted-foreground rounded-md border border-dashed px-4 py-3 text-sm">
        This cycle is complete. The vehicle&rsquo;s next service interval counts
        from its completion.
      </p>
    );
  }

  const allowed = isManager || !MANAGER_ONLY.includes(next);
  const needsInput = next === "booked" || next === "completed";

  function submit() {
    move.mutate(
      {
        status: next as ServiceStatus,
        ...(next === "booked" ? { scheduled_date: scheduledDate } : {}),
        ...(next === "completed"
          ? { completion_odometer: Number(odometer) }
          : {}),
      },
      { onSuccess: () => setOpen(false) },
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-md border px-4 py-3">
      <span className="text-sm">
        Next step: <strong>{STATUS_LABELS[next]}</strong>
      </span>

      {allowed ? (
        <Button
          disabled={move.isPending}
          onClick={() => (needsInput ? setOpen(true) : submit())}
        >
          {move.isPending ? "Working…" : `Mark ${STATUS_LABELS[next]}`}
        </Button>
      ) : (
        <span className="text-muted-foreground text-sm">
          Booking is a fleet manager&rsquo;s action.
        </span>
      )}

      {move.error && !open ? (
        <p role="alert" className="text-destructive w-full text-sm">
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
            ? "A booked service needs a date."
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
            <div className="space-y-1.5">
              <Label htmlFor="scheduled_date">Scheduled date</Label>
              <Input
                id="scheduled_date"
                type="date"
                required
                value={scheduledDate}
                onChange={(event) => setScheduledDate(event.target.value)}
              />
            </div>
          ) : (
            <div className="space-y-1.5">
              <Label htmlFor="completion_odometer">Completion odometer</Label>
              <Input
                id="completion_odometer"
                type="number"
                min={0}
                required
                value={odometer}
                onChange={(event) => setOdometer(event.target.value)}
              />
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
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={move.isPending}>
              {move.isPending ? "Working…" : `Mark ${STATUS_LABELS[next]}`}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
