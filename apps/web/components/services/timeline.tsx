"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { useTimeline } from "@/hooks/use-services";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  STATUS_LABELS,
  type AuditEvent,
  type ServiceStatus,
} from "@/types/service";

/**
 * The immutable audit trail, oldest first.
 *
 * Read-only by construction: there is no edit or delete here because there is
 * no endpoint for either, and the table itself has triggers refusing UPDATE
 * and DELETE. Nothing on this screen could remove an entry even if it tried.
 */
export function ServiceTimeline({ id }: { id: number }) {
  const { data: events, error, isPending, refetch } = useTimeline(id);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit timeline</CardTitle>
        <span className="text-muted-foreground text-xs">
          Append-only · {events?.length ?? 0} events
        </span>
      </CardHeader>

      <CardContent className="text-sm">
        {isPending ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-3/5" />
          </div>
        ) : null}

        {error ? (
          <ErrorState
            title="Could not load the timeline"
            message={error.message}
            onRetry={() => void refetch()}
          />
        ) : null}

        {events && events.length === 0 ? (
          <p className="text-muted-foreground">Nothing recorded yet.</p>
        ) : null}

        {events && events.length > 0 ? (
          <ol className="relative space-y-4 pl-5">
            {/* One rule down the left, so a long history reads as a sequence
                rather than a list of sentences. */}
            <span
              aria-hidden
              className="bg-border absolute top-1.5 bottom-1.5 left-[3px] w-px"
            />

            {events.map((event) => (
              <li key={event.id} className="relative">
                <span
                  aria-hidden
                  className={cn(
                    "absolute top-1.5 -left-5 size-[7px] rounded-full ring-2",
                    "ring-background",
                    dotFor(event),
                  )}
                />
                <p>{describe(event)}</p>
                <p className="text-muted-foreground mt-0.5 text-xs">
                  {/* Null actor means the system acted rather than a person. */}
                  {event.actor?.full_name ?? "System"} &middot;{" "}
                  {formatDateTime(event.created_at)}
                </p>
              </li>
            ))}
          </ol>
        ) : null}
      </CardContent>
    </Card>
  );
}

/** Status changes take the colour of the state they arrived at. */
function dotFor(event: AuditEvent): string {
  if (event.event_type !== "status_changed") return "bg-muted-foreground/40";

  switch (event.new_value as ServiceStatus) {
    case "booked":
      return "bg-booked";
    case "in_service":
      return "bg-in-service";
    case "completed":
      return "bg-completed";
    default:
      return "bg-due";
  }
}

function describe(event: AuditEvent): string {
  const name = String(event.event_metadata?.technician_name ?? "a technician");

  switch (event.event_type) {
    case "service_created":
      return `Opened this service record as ${label(event.new_value)}`;
    case "status_changed":
      return `Moved from ${label(event.old_value)} to ${label(event.new_value)}`;
    case "technician_assigned":
      return `Assigned ${name}`;
    case "technician_unassigned":
      return `Removed ${name}`;
    case "note_added":
      return "Added a note";
    default:
      return event.event_type;
  }
}

function label(status: string | null): string {
  if (!status) return "—";
  return STATUS_LABELS[status as ServiceStatus] ?? status;
}
