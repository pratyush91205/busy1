"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { VehicleFormModal } from "@/components/vehicles/vehicle-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCurrentUser } from "@/hooks/use-auth";
import {
  useArchiveVehicle,
  useCreateVehicle,
  useVehicles,
} from "@/hooks/use-vehicles";
import type { Vehicle, VehicleSort } from "@/types/vehicle";

const COLUMNS: { key: VehicleSort | null; label: string }[] = [
  { key: "registration_number", label: "Registration" },
  { key: null, label: "Make & model" },
  { key: "current_odometer", label: "Odometer" },
  { key: null, label: "Service interval" },
  { key: null, label: "Status" },
  { key: null, label: "" },
];

export default function VehiclesPage() {
  // useSearchParams needs a Suspense boundary for the statically-rendered
  // shell; the page below it reads the URL as its own state.
  return (
    <Suspense fallback={<TableSkeleton />}>
      <VehiclesView />
    </Suspense>
  );
}

function VehiclesView() {
  const router = useRouter();
  const params = useSearchParams();
  const { user } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";

  const [adding, setAdding] = useState(false);
  const [archiving, setArchiving] = useState<Vehicle | null>(null);

  const query = {
    search: params.get("search") ?? "",
    include_archived: params.get("archived") === "true",
    due: params.get("due") === "true" ? true : undefined,
    sort: (params.get("sort") as VehicleSort) || "registration_number",
    order: params.get("order") === "desc" ? ("desc" as const) : ("asc" as const),
    page: Number(params.get("page")) || 1,
  };

  const { data, error, isPending, isPlaceholderData } = useVehicles(query);
  const create = useCreateVehicle();
  const archive = useArchiveVehicle();

  // The URL is the state, so a filtered view can be linked or reloaded.
  function setParam(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    // Any change to a filter invalidates the page number.
    if (!("page" in changes)) next.delete("page");
    router.replace(`/vehicles?${next.toString()}`);
  }

  function toggleSort(column: VehicleSort) {
    const sameColumn = query.sort === column;
    setParam({
      sort: column,
      order: sameColumn && query.order === "asc" ? "desc" : "asc",
    });
  }

  return (
    <main className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Vehicles</h1>
          <p className="text-muted-foreground text-sm">
            {data ? `${data.total} in view` : "Loading the fleet…"}
          </p>
        </div>

        {isManager ? (
          <Button onClick={() => setAdding(true)}>Add vehicle</Button>
        ) : null}
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <Input
          type="search"
          placeholder="Search registration, make or model"
          defaultValue={query.search}
          onChange={(event) => setParam({ search: event.target.value })}
          className="max-w-xs"
          aria-label="Search vehicles"
        />

        <label className="text-muted-foreground flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={query.due === true}
            onChange={(event) =>
              setParam({ due: event.target.checked ? "true" : null })
            }
            className="size-4"
          />
          Due only
        </label>

        <label className="text-muted-foreground flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={query.include_archived}
            onChange={(event) =>
              setParam({ archived: event.target.checked ? "true" : null })
            }
            className="size-4"
          />
          Show archived
        </label>
      </div>

      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error.message}
        </p>
      ) : null}

      {isPending ? <TableSkeleton /> : null}

      {data && data.items.length === 0 ? (
        <p className="text-muted-foreground rounded-md border border-dashed px-4 py-10 text-center text-sm">
          {query.search
            ? `No vehicles match “${query.search}”.`
            : "No vehicles yet."}
        </p>
      ) : null}

      {data && data.items.length > 0 ? (
        <div
          className="rounded-md border"
          // Dimmed while the next page loads, rather than replaced by a
          // spinner - the old rows stay readable.
          style={{ opacity: isPlaceholderData ? 0.6 : 1 }}
        >
          <Table>
            <TableHeader>
              <TableRow>
                {COLUMNS.map(({ key, label }) => (
                  <TableHead key={label}>
                    {key ? (
                      <button
                        type="button"
                        onClick={() => toggleSort(key)}
                        className="hover:text-foreground flex items-center gap-1"
                      >
                        {label}
                        {query.sort === key ? (
                          <span aria-hidden>
                            {query.order === "asc" ? "↑" : "↓"}
                          </span>
                        ) : null}
                        {query.sort === key ? (
                          <span className="sr-only">
                            sorted {query.order === "asc" ? "ascending" : "descending"}
                          </span>
                        ) : null}
                      </button>
                    ) : (
                      label
                    )}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>

            <TableBody>
              {data.items.map((vehicle) => (
                <TableRow key={vehicle.id}>
                  <TableCell className="font-medium">
                    <Link
                      href={`/vehicles/${vehicle.id}`}
                      className="hover:underline"
                    >
                      {vehicle.registration_number}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {vehicle.make} {vehicle.model}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {vehicle.current_odometer.toLocaleString()} mi
                  </TableCell>
                  <TableCell className="text-muted-foreground tabular-nums">
                    {vehicle.service_date_interval} d /{" "}
                    {vehicle.service_mileage_interval.toLocaleString()} mi
                  </TableCell>
                  <TableCell>
                    {/* Archived wins: an archived vehicle is never due. */}
                    {vehicle.is_archived ? (
                      <Badge tone="neutral">ARCHIVED</Badge>
                    ) : vehicle.service_status?.is_due ? (
                      <Badge tone="warning">DUE</Badge>
                    ) : (
                      <Badge tone="success">ACTIVE</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {isManager ? (
                      <Button
                        variant="ghost"
                        className="h-7 px-2 text-xs"
                        onClick={() => setArchiving(vehicle)}
                      >
                        {vehicle.is_archived ? "Restore" : "Archive"}
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      {data && data.total_pages > 1 ? (
        <nav
          aria-label="Pagination"
          className="flex items-center justify-between text-sm"
        >
          <span className="text-muted-foreground">
            Page {data.page} of {data.total_pages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              disabled={data.page <= 1}
              onClick={() => setParam({ page: String(data.page - 1) })}
            >
              Previous
            </Button>
            <Button
              variant="ghost"
              disabled={data.page >= data.total_pages}
              onClick={() => setParam({ page: String(data.page + 1) })}
            >
              Next
            </Button>
          </div>
        </nav>
      ) : null}

      <VehicleFormModal
        open={adding}
        onClose={() => {
          setAdding(false);
          create.reset();
        }}
        onSubmit={(values) =>
          create.mutate(values, { onSuccess: () => setAdding(false) })
        }
        error={create.error}
        isPending={create.isPending}
      />

      <Modal
        open={archiving !== null}
        onClose={() => {
          setArchiving(null);
          archive.reset();
        }}
        title={
          archiving?.is_archived
            ? `Restore ${archiving.registration_number}?`
            : `Archive ${archiving?.registration_number}?`
        }
        description={
          archiving?.is_archived
            ? "It returns to the fleet and can be edited again."
            : "It leaves the default fleet view and refuses edits. Its service history is kept, and you can restore it."
        }
      >
        {archive.error ? (
          <p role="alert" className="text-destructive text-sm">
            {archive.error.message}
          </p>
        ) : null}

        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setArchiving(null)}>
            Cancel
          </Button>
          <Button
            disabled={archive.isPending}
            onClick={() =>
              archiving &&
              archive.mutate(
                { id: archiving.id, archive: !archiving.is_archived },
                { onSuccess: () => setArchiving(null) },
              )
            }
          >
            {archive.isPending
              ? "Working…"
              : archiving?.is_archived
                ? "Restore"
                : "Archive"}
          </Button>
        </div>
      </Modal>
    </main>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading vehicles">
      {[0, 1, 2, 3, 4].map((row) => (
        <Skeleton key={row} className="h-10 w-full" />
      ))}
    </div>
  );
}
