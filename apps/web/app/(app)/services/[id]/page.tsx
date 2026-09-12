"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { LifecycleSteps } from "@/components/services/lifecycle-steps";
import { StatusBadge } from "@/components/services/status-badge";
import { ServiceTimeline } from "@/components/services/timeline";
import { TransitionPanel } from "@/components/services/transition-actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useCurrentUser } from "@/hooks/use-auth";
import {
  useAddNote,
  useAssignTechnician,
  useNotes,
  useService,
  useUnassignTechnician,
  useUpdateDescription,
} from "@/hooks/use-services";
import { useTechnicians } from "@/hooks/use-technicians";
import { daysSince, formatDate, formatDateTime, formatMiles } from "@/lib/format";
import type { UserSummary } from "@/types/service";

export default function ServiceDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const { user } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";

  const { data: service, error, isPending } = useService(id);

  if (isPending) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading service">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-16 w-full" />
        <div className="grid gap-4 lg:grid-cols-3">
          <Skeleton className="h-48 lg:col-span-2" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="max-w-lg space-y-2">
        <p className="text-destructive font-medium">
          {/* A technician reaching for someone else's record also lands here:
              the server answers 404 rather than confirming it exists. */}
          {error.status === 404
            ? "No such service record, or it is not assigned to you"
            : "Could not load the service record"}
        </p>
        <p className="text-muted-foreground text-sm">{error.message}</p>
        <Link href="/services" className="inline-block text-sm underline">
          Back to services
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <nav className="text-muted-foreground text-sm">
        <Link href="/services" className="hover:text-foreground">
          Services
        </Link>
        <span className="px-1.5">/</span>
        <span className="text-foreground">
          {service.vehicle.registration_number} cycle {service.cycle_number}
        </span>
      </nav>

      <header className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-base font-semibold">
                <Link
                  href={`/vehicles/${service.vehicle.id}`}
                  className="hover:underline"
                >
                  {service.vehicle.registration_number}
                </Link>
              </h1>
              <span className="text-muted-foreground text-sm">
                {service.vehicle.make} {service.vehicle.model}
              </span>
              <StatusBadge
                status={service.status}
                isOverdue={service.is_overdue}
              />
            </div>

            <p className="text-muted-foreground text-sm">
              Cycle {service.cycle_number} &middot; opened{" "}
              {formatDate(service.created_at)}
              {service.is_overdue && service.overdue_since
                ? ` · overdue for ${daysSince(service.overdue_since)} days`
                : ""}
            </p>
          </div>
        </div>

        <LifecycleSteps
          status={service.status}
          isOverdue={service.is_overdue}
          className="max-w-2xl"
        />
      </header>

      <TransitionPanel service={service} isManager={isManager} />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <DescriptionCard id={id} description={service.description} />
          <NotesCard id={id} />
          <ServiceTimeline id={id} />
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-y-2.5 text-sm">
                <dt className="text-muted-foreground">Vehicle</dt>
                <dd className="text-right">
                  <Link
                    href={`/vehicles/${service.vehicle.id}`}
                    className="hover:underline"
                  >
                    {service.vehicle.registration_number}
                  </Link>
                </dd>

                <dt className="text-muted-foreground">Scheduled</dt>
                <dd className="text-right tabular-nums">
                  {formatDate(service.scheduled_date)}
                </dd>

                <dt className="text-muted-foreground">Due since</dt>
                <dd className="text-right tabular-nums">
                  {service.due_since ? formatDate(service.due_since) : "—"}
                </dd>

                <dt className="text-muted-foreground">Last updated</dt>
                <dd className="text-right">
                  {formatDateTime(service.updated_at)}
                </dd>

                {service.completed_at ? (
                  <>
                    <dt className="text-muted-foreground">Completed</dt>
                    <dd className="text-right">
                      {formatDateTime(service.completed_at)}
                    </dd>

                    <dt className="text-muted-foreground">Closing odometer</dt>
                    <dd className="text-right tabular-nums">
                      {formatMiles(service.completion_odometer)}
                    </dd>
                  </>
                ) : null}
              </dl>

              {service.completed_at ? (
                <p className="text-muted-foreground mt-3 border-t pt-3 text-xs">
                  The vehicle&rsquo;s next service interval counts from this
                  date and this reading.
                </p>
              ) : null}
            </CardContent>
          </Card>

          <TechniciansCard
            id={id}
            technicians={service.technicians}
            isManager={isManager}
            locked={service.status === "completed"}
          />
        </div>
      </div>
    </div>
  );
}

function DescriptionCard({
  id,
  description,
}: {
  id: number;
  description: string;
}) {
  const update = useUpdateDescription(id);
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(description);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Description</CardTitle>
        {/* Offered to everyone: a manager, or a technician assigned to this
            record, may edit it. Anyone else gets 403 or 404 from the API. */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setDraft(description);
            setEditing((open) => !open);
            update.reset();
          }}
        >
          {editing ? "Cancel" : "Edit"}
        </Button>
      </CardHeader>

      <CardContent className="text-sm">
        {editing ? (
          <form
            className="space-y-2"
            onSubmit={(event) => {
              event.preventDefault();
              update.mutate(draft, {
                onSuccess: () => {
                  setEditing(false);
                  toast("Description saved");
                },
              });
            }}
          >
            <Textarea
              rows={3}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              aria-label="Service description"
            />
            {update.error ? (
              <p role="alert" className="text-destructive text-xs">
                {update.error.message}
              </p>
            ) : null}
            <div className="flex justify-end">
              <Button
                type="submit"
                size="sm"
                disabled={update.isPending || draft.trim() === ""}
              >
                {update.isPending ? "Saving…" : "Save"}
              </Button>
            </div>
          </form>
        ) : (
          <p className="whitespace-pre-wrap">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

function TechniciansCard({
  id,
  technicians,
  isManager,
  locked,
}: {
  id: number;
  technicians: UserSummary[];
  isManager: boolean;
  locked: boolean;
}) {
  const assign = useAssignTechnician(id);
  const unassign = useUnassignTechnician(id);
  const toast = useToast();
  // Only a manager may assign, so only a manager fetches the roster.
  const { data: roster } = useTechnicians(isManager && !locked);

  const assigned = new Set(technicians.map((person) => person.id));
  const available = roster?.filter((person) => !assigned.has(person.id)) ?? [];
  const error = assign.error ?? unassign.error;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Technicians</CardTitle>
        <span className="text-muted-foreground text-xs tabular-nums">
          {technicians.length}
        </span>
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {technicians.length === 0 ? (
          <p className="text-muted-foreground">Nobody assigned yet.</p>
        ) : (
          <ul className="divide-y">
            {technicians.map((person) => (
              <li
                key={person.id}
                className="flex items-center justify-between gap-2 py-1.5 first:pt-0 last:pb-0"
              >
                <div className="min-w-0">
                  <p className="truncate">{person.full_name}</p>
                  <p className="text-muted-foreground truncate text-xs">
                    {person.email}
                  </p>
                </div>
                {isManager && !locked ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={unassign.isPending}
                    onClick={() =>
                      unassign.mutate(person.id, {
                        onSuccess: () => toast(`${person.full_name} removed`),
                      })
                    }
                  >
                    Remove
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        {isManager && !locked ? (
          <Select
            value=""
            disabled={assign.isPending || available.length === 0}
            onChange={(event) => {
              const technicianId = Number(event.target.value);
              const person = available.find((item) => item.id === technicianId);
              assign.mutate(technicianId, {
                onSuccess: () => toast(`${person?.full_name} assigned`),
              });
            }}
            aria-label="Assign a technician"
            className="h-9 w-full"
          >
            <option value="">
              {available.length === 0
                ? "Everyone is assigned"
                : "Assign a technician…"}
            </option>
            {available.map((person) => (
              <option key={person.id} value={person.id}>
                {person.full_name}
              </option>
            ))}
          </Select>
        ) : null}

        {locked ? (
          <p className="text-muted-foreground text-xs">
            This record is completed. Who worked on it is part of its history.
          </p>
        ) : null}

        {!isManager && !locked ? (
          <p className="text-muted-foreground text-xs">
            Assignments are set by a fleet manager.
          </p>
        ) : null}

        {error ? (
          <p role="alert" className="text-destructive text-xs">
            {error.message}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function NotesCard({ id }: { id: number }) {
  const { data: notes, isPending } = useNotes(id);
  const add = useAddNote(id);
  const toast = useToast();
  const [draft, setDraft] = useState("");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notes</CardTitle>
        <span className="text-muted-foreground text-xs">
          Append-only &middot; {notes?.length ?? 0}
        </span>
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {isPending ? <Skeleton className="h-10 w-full" /> : null}

        {notes && notes.length === 0 ? (
          <p className="text-muted-foreground">
            No notes yet. Anything recorded here stays on the record.
          </p>
        ) : null}

        {notes && notes.length > 0 ? (
          <ul className="space-y-3">
            {notes.map((note) => (
              <li key={note.id} className="border-l-2 pl-3">
                <p className="whitespace-pre-wrap">{note.content}</p>
                <p className="text-muted-foreground mt-1 text-xs">
                  {note.author.full_name} &middot;{" "}
                  {formatDateTime(note.created_at)}
                </p>
              </li>
            ))}
          </ul>
        ) : null}

        <form
          className="space-y-2 border-t pt-3"
          onSubmit={(event) => {
            event.preventDefault();
            add.mutate(draft, {
              onSuccess: () => {
                setDraft("");
                toast("Note added");
              },
            });
          }}
        >
          <Textarea
            rows={2}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Add a note"
            aria-label="Add a note"
          />
          {add.error ? (
            <p role="alert" className="text-destructive text-xs">
              {add.error.message}
            </p>
          ) : null}
          {/* Notes are append-only: there is no edit and no delete, here or
              in the API. */}
          <div className="flex justify-end">
            <Button
              type="submit"
              size="sm"
              disabled={add.isPending || draft.trim() === ""}
            >
              {add.isPending ? "Adding…" : "Add note"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
