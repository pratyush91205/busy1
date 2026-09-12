"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";

import { VehicleFormModal } from "@/components/vehicles/vehicle-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FilterBar } from "@/components/ui/filter-bar";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { TableSkeleton } from "@/components/ui/skeleton";
import { SortableHead } from "@/components/ui/sortable-head";
import { EmptyState, ErrorState } from "@/components/ui/states";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { useCurrentUser } from "@/hooks/use-auth";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useQueryParams } from "@/hooks/use-query-params";
import {
  useArchiveVehicle,
  useCreateVehicle,
  useVehicles,
} from "@/hooks/use-vehicles";
import { formatDate, formatMiles } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Vehicle, VehicleQuery, VehicleSort } from "@/types/vehicle";

export default function VehiclesPage() {
  // useSearchParams needs a Suspense boundary for the statically-rendered
  // shell; the view below it reads the URL as its own state.
  return (
    <Suspense fallback={<TableSkeleton label="Loading vehicles" columns={6} />}>
      <VehiclesView />
    </Suspense>
  );
}

function VehiclesView() {
  const { params, setParams } = useQueryParams("/vehicles");
  const { user } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";
  const toast = useToast();

  const [adding, setAdding] = useState(false);
  const [archiving, setArchiving] = useState<Vehicle | null>(null);

  const query: VehicleQuery = {
    search: params.get("search") || undefined,
    include_archived: params.get("archived") === "true" || undefined,
    due: params.get("due") === "true" ? true : undefined,
    sort: (params.get("sort") as VehicleSort) || "registration_number",
    order: params.get("order") === "desc" ? "desc" : "asc",
    page: Number(params.get("page")) || 1,
    limit: Number(params.get("limit")) || 20,
  };

  const { data, error, isPending, isPlaceholderData, refetch } =
    useVehicles(query);
  const create = useCreateVehicle();
  const archive = useArchiveVehicle();

  const [searchInput, setSearchInput] = useState(params.get("search") ?? "");
  const debouncedSearch = useDebouncedValue(searchInput, 300);

  useEffect(() => {
    const current = params.get("search") ?? "";
    if (debouncedSearch !== current) setParams({ search: debouncedSearch });
  }, [debouncedSearch, params, setParams]);

  function toggleSort(column: VehicleSort) {
    const same = query.sort === column;
    setParams({
      sort: column,
      order: same && query.order === "asc" ? "desc" : "asc",
    });
  }

  const sort = query.sort ?? "registration_number";
  const order = query.order ?? "asc";

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-base font-semibold">Vehicles</h1>
          <p className="text-muted-foreground mt-0.5 text-sm">
            {data
              ? `${data.total} in view${query.include_archived ? ", archived included" : ""}`
              : " "}
          </p>
        </div>

        {isManager ? (
          <Button onClick={() => setAdding(true)}>Add vehicle</Button>
        ) : null}
      </header>

      <FilterBar>
        <Input
          type="search"
          placeholder="Search registration, make or model"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          className="w-64"
          aria-label="Search vehicles"
        />

        <Toggle
          checked={query.due === true}
          onChange={(checked) => setParams({ due: checked })}
          tone="due"
          label="Due for service"
        />

        <Toggle
          checked={Boolean(query.include_archived)}
          onChange={(checked) => setParams({ archived: checked })}
          label="Include archived"
        />
      </FilterBar>

      {error ? (
        <ErrorState message={error.message} onRetry={() => void refetch()} />
      ) : null}

      {isPending ? <TableSkeleton label="Loading vehicles" columns={6} /> : null}

      {data && data.items.length === 0 ? (
        <EmptyState
          title={
            query.search
              ? `No vehicles match “${query.search}”`
              : query.due
                ? "Nothing is due for service"
                : "No vehicles yet"
          }
          hint={
            query.due
              ? "A vehicle becomes due when either its date interval or its mileage interval is reached."
              : query.search
                ? "Search covers registration, make and model."
                : isManager
                  ? "Add the first vehicle to start tracking its service intervals."
                  : "The fleet appears here once a manager adds vehicles."
          }
        />
      ) : null}

      {data && data.items.length > 0 ? (
        <div
          className={cn(
            "overflow-hidden rounded-md border transition-opacity duration-120",
            // Dimmed while the next page loads, rather than replaced by a
            // spinner - the old rows stay readable.
            isPlaceholderData && "opacity-60",
          )}
        >
          <Table>
            <TableHeader>
              <TableRow>
                <SortableHead
                  label="Registration"
                  column="registration_number"
                  active={sort}
                  order={order}
                  onSort={toggleSort}
                />
                <TableHead>Make &amp; model</TableHead>
                <SortableHead
                  label="Odometer"
                  column="current_odometer"
                  active={sort}
                  order={order}
                  onSort={toggleSort}
                />
                <TableHead>Service interval</TableHead>
                <TableHead>Next service</TableHead>
                <TableHead>State</TableHead>
                {isManager ? <TableHead /> : null}
              </TableRow>
            </TableHeader>

            <TableBody>
              {data.items.map((vehicle) => {
                const status = vehicle.service_status;
                const due = !vehicle.is_archived && status?.is_due;

                return (
                  <TableRow
                    key={vehicle.id}
                    className={cn(
                      "border-l-2",
                      due ? "border-l-due" : "border-l-transparent",
                      vehicle.is_archived && "opacity-65",
                    )}
                  >
                    <TableCell className="font-medium whitespace-nowrap">
                      <Link
                        href={`/vehicles/${vehicle.id}`}
                        className="hover:underline"
                      >
                        {vehicle.registration_number}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap">
                      {vehicle.make} {vehicle.model}
                    </TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">
                      {formatMiles(vehicle.current_odometer)}
                    </TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap tabular-nums">
                      {vehicle.service_date_interval} d /{" "}
                      {vehicle.service_mileage_interval.toLocaleString()} mi
                    </TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap text-xs">
                      {vehicle.is_archived || !status ? (
                        "—"
                      ) : (
                        <>
                          {formatDate(status.next_due_date)}
                          <span className="px-1">or</span>
                          {formatMiles(status.next_due_odometer)}
                        </>
                      )}
                    </TableCell>
                    <TableCell>
                      {/* Archived wins: an archived vehicle is never due. */}
                      {vehicle.is_archived ? (
                        <Badge tone="neutral">Archived</Badge>
                      ) : due ? (
                        <span className="flex items-center gap-1.5">
                          <Badge tone="due">Due</Badge>
                          <span className="text-muted-foreground text-xs">
                            {reason(status?.reason)}
                          </span>
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-xs">
                          On schedule
                        </span>
                      )}
                    </TableCell>
                    {isManager ? (
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setArchiving(vehicle)}
                        >
                          {vehicle.is_archived ? "Restore" : "Archive"}
                        </Button>
                      </TableCell>
                    ) : null}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      ) : null}

      {data && data.total > 0 ? (
        <Pagination
          page={data}
          label="vehicles"
          onPage={(page) => setParams({ page })}
          onLimit={(limit) => setParams({ limit, page: 1 })}
        />
      ) : null}

      <VehicleFormModal
        open={adding}
        onClose={() => {
          setAdding(false);
          create.reset();
        }}
        onSubmit={(values) =>
          create.mutate(values, {
            onSuccess: (vehicle) => {
              setAdding(false);
              toast(`${vehicle.registration_number} added`);
            },
          })
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
            variant={archiving?.is_archived ? "default" : "danger"}
            disabled={archive.isPending}
            onClick={() =>
              archiving &&
              archive.mutate(
                { id: archiving.id, archive: !archiving.is_archived },
                {
                  onSuccess: (vehicle) => {
                    setArchiving(null);
                    toast(
                      `${vehicle.registration_number} ${
                        vehicle.is_archived ? "archived" : "restored"
                      }`,
                    );
                  },
                },
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
    </div>
  );
}

/** A filter that is on or off, styled as a control rather than a bare checkbox. */
function Toggle({
  checked,
  onChange,
  label,
  tone,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  tone?: "due";
}) {
  return (
    <label
      className={cn(
        "flex h-8 cursor-pointer items-center gap-2 rounded-md border px-2.5 text-sm transition-colors duration-120",
        checked
          ? tone === "due"
            ? "border-due/30 bg-due-soft text-due font-medium"
            : "bg-muted text-foreground font-medium"
          : "text-muted-foreground hover:bg-muted/60",
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="size-3.5"
      />
      {label}
    </label>
  );
}

/** Either interval makes a vehicle due; they are not required together. */
function reason(value: "date" | "mileage" | "both" | null | undefined): string {
  switch (value) {
    case "date":
      return "on date";
    case "mileage":
      return "on mileage";
    case "both":
      return "date and mileage";
    default:
      return "";
  }
}
