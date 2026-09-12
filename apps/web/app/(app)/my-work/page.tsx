"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { StatusBadge, accentFor } from "@/components/services/status-badge";
import { TransitionButton } from "@/components/services/transition-actions";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { useCurrentUser } from "@/hooks/use-auth";
import { useServices } from "@/hooks/use-services";
import { formatDate, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ServiceRecord, ServiceStatus } from "@/types/service";

/**
 * The technician's queue.
 *
 * Four server-side queries rather than one list filtered in the browser: each
 * section asks for its own status, so the counts are the server's `total` and
 * nothing is sliced here. A technician's scope is applied in SQL by the API,
 * so "my work" is a fact about the response, not a filter this page applies.
 */
export default function MyWorkPage() {
  const router = useRouter();
  const { user, isLoading } = useCurrentUser();
  const isTechnician = user?.role === "technician";

  // A manager has the fleet-wide list; this queue would only ever be empty for
  // them, because nothing is assigned to a manager.
  useEffect(() => {
    if (!isLoading && user && !isTechnician) router.replace("/dashboard");
  }, [isLoading, user, isTechnician, router]);

  const inService = useServices({ status: "in_service", limit: 50 });
  const booked = useServices({
    status: "booked",
    sort: "scheduled_date",
    order: "asc",
    limit: 50,
  });
  const due = useServices({ status: "due", limit: 50 });
  const completed = useServices({ status: "completed", limit: 5 });

  if (!isTechnician) return null;

  const error =
    inService.error ?? booked.error ?? due.error ?? completed.error ?? null;
  const loading =
    inService.isPending || booked.isPending || due.isPending;

  const open =
    (inService.data?.total ?? 0) +
    (booked.data?.total ?? 0) +
    (due.data?.total ?? 0);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-base font-semibold">My work</h1>
        <p className="text-muted-foreground mt-0.5 text-sm">
          {loading
            ? " "
            : open === 0
              ? "Nothing assigned to you right now."
              : `${open} open ${open === 1 ? "record" : "records"} assigned to you.`}
        </p>
      </header>

      {error ? (
        <ErrorState
          message={error.message}
          onRetry={() => {
            void inService.refetch();
            void booked.refetch();
            void due.refetch();
          }}
        />
      ) : null}

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : null}

      {!loading && open === 0 && !error ? (
        <EmptyState
          title="No work assigned"
          hint="A fleet manager assigns service records to technicians. Anything assigned to you shows up here, newest work first."
        />
      ) : null}

      <Section
        title="In the bay"
        hint="Started, not finished. Completing one records the closing odometer."
        services={inService.data?.items ?? []}
      />
      <Section
        title="Booked"
        hint="Scheduled work. Start it when the vehicle arrives."
        services={booked.data?.items ?? []}
      />
      <Section
        title="Waiting on booking"
        hint="Assigned to you, but a fleet manager sets the date before work starts."
        services={due.data?.items ?? []}
      />

      {completed.data && completed.data.items.length > 0 ? (
        <section className="space-y-2">
          <h2 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
            Recently completed
          </h2>
          <ul className="divide-y rounded-md border">
            {completed.data.items.map((service) => (
              <li
                key={service.id}
                className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
              >
                <Link
                  href={`/services/${service.id}`}
                  className="min-w-0 hover:underline"
                >
                  <span className="font-medium">
                    {service.vehicle.registration_number}
                  </span>
                  <span className="text-muted-foreground ml-2 truncate">
                    {service.description}
                  </span>
                </Link>
                <span className="text-muted-foreground shrink-0 text-xs">
                  {formatDateTime(service.completed_at)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function Section({
  title,
  hint,
  services,
}: {
  title: string;
  hint: string;
  services: ServiceRecord[];
}) {
  if (services.length === 0) return null;

  return (
    <section className="space-y-2">
      <div>
        <h2 className="text-sm font-semibold">
          {title}
          <span className="text-muted-foreground ml-2 text-xs font-normal tabular-nums">
            {services.length}
          </span>
        </h2>
        <p className="text-muted-foreground text-xs">{hint}</p>
      </div>

      <ul className="space-y-2">
        {services.map((service) => (
          <JobCard key={service.id} service={service} />
        ))}
      </ul>
    </section>
  );
}

/**
 * One job, sized for a phone: what and where first, the action last, and no
 * column of metadata a technician standing in a depot has to read past.
 */
function JobCard({ service }: { service: ServiceRecord }) {
  return (
    <li
      className={cn(
        "hover:bg-muted/40 rounded-md border border-l-2 p-3 transition-colors duration-120",
        accentFor(service.status, service.is_overdue),
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href={`/services/${service.id}`}
              className="text-sm font-semibold hover:underline"
            >
              {service.vehicle.registration_number}
            </Link>
            <span className="text-muted-foreground text-xs">
              {service.vehicle.make} {service.vehicle.model}
            </span>
            <StatusBadge
              status={service.status}
              isOverdue={service.is_overdue}
            />
          </div>

          <p className="text-sm">{service.description}</p>

          <p className="text-muted-foreground text-xs">
            Cycle {service.cycle_number}
            {service.scheduled_date
              ? ` · scheduled ${formatDate(service.scheduled_date)}`
              : ""}
          </p>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-1.5">
          {/* Technicians own In Service and Completed; booking is a manager's.
              Passing isManager={false} is presentation only - the API refuses
              a technician's booking attempt regardless. */}
          <TransitionButton service={service} isManager={false} size="sm" />
          <Link
            href={`/services/${service.id}`}
            className="text-muted-foreground hover:text-foreground text-xs"
          >
            Open record
          </Link>
        </div>
      </div>

      {waitingNote(service.status)}
    </li>
  );
}

function waitingNote(status: ServiceStatus) {
  if (status !== "due") return null;

  return (
    <p className="text-muted-foreground mt-2 border-t pt-2 text-xs">
      A fleet manager books this before work can start. You can still add notes
      to the record.
    </p>
  );
}
