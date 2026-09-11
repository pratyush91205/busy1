"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { LifecycleSteps } from "@/components/services/lifecycle-steps";
import { ServiceTimeline } from "@/components/services/timeline";
import { StatusBadge } from "@/components/services/status-badge";
import { TransitionActions } from "@/components/services/transition-actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
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

export default function ServiceDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const { user } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";

  const { data: service, error, isPending } = useService(id);

  if (isPending) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading service">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="space-y-2">
        <p className="text-destructive font-medium">
          {/* A technician reaching for someone else's record also lands here:
              the server answers 404 rather than confirming it exists. */}
          {error.status === 404
            ? "No such service record, or it is not assigned to you"
            : "Could not load the service record"}
        </p>
        <p className="text-muted-foreground text-sm">{error.message}</p>
        <Link href="/services" className="text-sm underline">
          Back to services
        </Link>
      </div>
    );
  }

  return (
    <main className="space-y-6">
      <nav className="text-muted-foreground text-sm">
        <Link href="/services" className="hover:underline">
          Services
        </Link>
        <span className="px-2">/</span>
        <span>
          {service.vehicle.registration_number} cycle {service.cycle_number}
        </span>
      </nav>

      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-lg font-semibold">
            <Link
              href={`/vehicles/${service.vehicle.id}`}
              className="hover:underline"
            >
              {service.vehicle.registration_number}
            </Link>
            <span className="text-muted-foreground ml-2 text-sm font-normal">
              {service.vehicle.make} {service.vehicle.model}
            </span>
          </h1>
          <StatusBadge status={service.status} isOverdue={service.is_overdue} />
        </div>

        <LifecycleSteps status={service.status} />
      </header>

      <TransitionActions service={service} isManager={isManager} />

      <div className="grid gap-4 lg:grid-cols-2">
        <DescriptionCard id={id} description={service.description} />
        <TechniciansCard
          id={id}
          technicians={service.technicians}
          isManager={isManager}
          locked={service.status === "completed"}
        />
      </div>

      {service.completed_at ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Completion</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p className="tabular-nums">
              {service.completion_odometer?.toLocaleString()} miles, recorded{" "}
              {new Date(service.completed_at).toLocaleString()}
            </p>
            <p className="text-muted-foreground mt-1 text-xs">
              The next service interval counts from here, not from when the
              vehicle was added.
            </p>
          </CardContent>
        </Card>
      ) : null}

      <NotesCard id={id} />
      <ServiceTimeline id={id} />
    </main>
  );
}

function DescriptionCard({ id, description }: { id: number; description: string }) {
  const update = useUpdateDescription(id);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(description);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-sm font-medium">
          Description
          {/* Offered to everyone: a manager, or a technician assigned to this
              record, may edit it. Anyone else gets 403 or 404 from the API. */}
          <Button
            variant="ghost"
            className="h-7 px-2 text-xs"
            onClick={() => {
              setDraft(description);
              setEditing((open) => !open);
              update.reset();
            }}
          >
            {editing ? "Cancel" : "Edit"}
          </Button>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-2 text-sm">
        {editing ? (
          <form
            className="space-y-2"
            onSubmit={(event) => {
              event.preventDefault();
              update.mutate(draft, { onSuccess: () => setEditing(false) });
            }}
          >
            <textarea
              rows={3}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
              aria-label="Service description"
            />
            {update.error ? (
              <p role="alert" className="text-destructive text-xs">
                {update.error.message}
              </p>
            ) : null}
            <Button type="submit" disabled={update.isPending}>
              {update.isPending ? "Saving…" : "Save"}
            </Button>
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
  technicians: { id: number; full_name: string }[];
  isManager: boolean;
  locked: boolean;
}) {
  const assign = useAssignTechnician(id);
  const unassign = useUnassignTechnician(id);
  // Only a manager may assign, so only a manager fetches the roster.
  const { data: roster } = useTechnicians(isManager && !locked);

  const assigned = new Set(technicians.map((t) => t.id));
  const available = roster?.filter((person) => !assigned.has(person.id)) ?? [];
  const error = assign.error ?? unassign.error;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Technicians</CardTitle>
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {technicians.length === 0 ? (
          <p className="text-muted-foreground">Nobody assigned yet.</p>
        ) : (
          <ul className="space-y-1">
            {technicians.map((person) => (
              <li key={person.id} className="flex items-center justify-between gap-2">
                <span>{person.full_name}</span>
                {isManager && !locked ? (
                  <Button
                    variant="ghost"
                    className="h-7 px-2 text-xs"
                    disabled={unassign.isPending}
                    onClick={() => unassign.mutate(person.id)}
                  >
                    Remove
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        {isManager && !locked ? (
          <select
            value=""
            disabled={assign.isPending || available.length === 0}
            onChange={(event) => assign.mutate(Number(event.target.value))}
            aria-label="Assign a technician"
            className="border-input bg-background h-9 w-full rounded-md border px-2 text-sm"
          >
            <option value="">
              {available.length === 0 ? "Everyone is assigned" : "Assign a technician…"}
            </option>
            {available.map((person) => (
              <option key={person.id} value={person.id}>
                {person.full_name}
              </option>
            ))}
          </select>
        ) : null}

        {locked ? (
          <p className="text-muted-foreground text-xs">
            This record is completed. Who worked on it is part of its history.
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
  const [draft, setDraft] = useState("");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Notes</CardTitle>
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {isPending ? <Skeleton className="h-10 w-full" /> : null}

        {notes && notes.length === 0 ? (
          <p className="text-muted-foreground">No notes yet.</p>
        ) : null}

        {notes && notes.length > 0 ? (
          <ul className="space-y-3">
            {notes.map((note) => (
              <li key={note.id} className="border-l-2 pl-3">
                <p className="whitespace-pre-wrap">{note.content}</p>
                <p className="text-muted-foreground mt-1 text-xs">
                  {note.author.full_name} ·{" "}
                  {new Date(note.created_at).toLocaleString()}
                </p>
              </li>
            ))}
          </ul>
        ) : null}

        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            add.mutate(draft, { onSuccess: () => setDraft("") });
          }}
        >
          <textarea
            rows={2}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Add a note"
            aria-label="Add a note"
            className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
          />
          {add.error ? (
            <p role="alert" className="text-destructive text-xs">
              {add.error.message}
            </p>
          ) : null}
          {/* Notes are append-only: there is no edit and no delete, here or
              in the API. */}
          <Button type="submit" disabled={add.isPending || draft.trim() === ""}>
            {add.isPending ? "Adding…" : "Add note"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
