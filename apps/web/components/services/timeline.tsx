"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useTimeline } from "@/hooks/use-services";
import { STATUS_LABELS, type AuditEvent, type ServiceStatus } from "@/types/service";

/**
 * The immutable audit trail, oldest first.
 *
 * Read-only by construction: there is no edit or delete here because there is
 * no endpoint for either, and the table itself has triggers refusing UPDATE
 * and DELETE. Nothing on this screen could remove an entry even if it tried.
 */
export function ServiceTimeline({ id }: { id: number }) {
  const { data: events, error, isPending } = useTimeline(id);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Timeline</CardTitle>
      </CardHeader>

      <CardContent className="text-sm">
        {isPending ? <Skeleton className="h-20 w-full" /> : null}

        {error ? (
          <p role="alert" className="text-destructive">
            {error.message}
          </p>
        ) : null}

        {events && events.length === 0 ? (
          <p className="text-muted-foreground">Nothing recorded yet.</p>
        ) : null}

        {events && events.length > 0 ? (
          <ol className="space-y-3">
            {events.map((event) => (
              <li key={event.id} className="flex gap-3">
                <span
                  aria-hidden
                  className="bg-muted-foreground/40 mt-1.5 size-2 shrink-0 rounded-full"
                />
                <div className="space-y-0.5">
                  <p>{describe(event)}</p>
                  <p className="text-muted-foreground text-xs">
                    {/* Null actor means the system acted rather than a person. */}
                    {event.actor?.full_name ?? "System"} ·{" "}
                    {new Date(event.created_at).toLocaleString()}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        ) : null}
      </CardContent>
    </Card>
  );
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
