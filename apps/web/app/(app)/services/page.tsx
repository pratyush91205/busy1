"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { StatusBadge } from "@/components/services/status-badge";
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
import { useCreateService, useServices } from "@/hooks/use-services";
import { useVehicles } from "@/hooks/use-vehicles";
import { LIFECYCLE, STATUS_LABELS, type ServiceSort, type ServiceStatus } from "@/types/service";

export default function ServicesPage() {
  return (
    <Suspense fallback={<ListSkeleton />}>
      <ServicesView />
    </Suspense>
  );
}

function ServicesView() {
  const router = useRouter();
  const params = useSearchParams();
  const { user } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";

  const [creating, setCreating] = useState(false);

  const query = {
    search: params.get("search") ?? "",
    status: (params.get("status") as ServiceStatus) || undefined,
    vehicle_id: Number(params.get("vehicle_id")) || undefined,
    sort: (params.get("sort") as ServiceSort) || "updated_at",
    order: params.get("order") === "asc" ? ("asc" as const) : ("desc" as const),
    page: Number(params.get("page")) || 1,
  };

  const { data, error, isPending, isPlaceholderData } = useServices(query);

  function setParam(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    if (!("page" in changes)) next.delete("page");
    router.replace(`/services?${next.toString()}`);
  }

  function toggleSort(column: ServiceSort) {
    const same = query.sort === column;
    setParam({
      sort: column,
      order: same && query.order === "desc" ? "asc" : "desc",
    });
  }

  return (
    <main className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Services</h1>
          <p className="text-muted-foreground text-sm">
            {/* A technician's list is already scoped by the server, so the
                count is honest for whoever is reading it. */}
            {isManager
              ? `${data?.total ?? "…"} across the fleet`
              : `${data?.total ?? "…"} assigned to you`}
          </p>
        </div>

        {isManager ? (
          <Button onClick={() => setCreating(true)}>New service record</Button>
        ) : null}
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <Input
          type="search"
          placeholder="Search descriptions"
          defaultValue={query.search}
          onChange={(event) => setParam({ search: event.target.value })}
          className="max-w-xs"
          aria-label="Search service records"
        />

        <select
          value={query.status ?? ""}
          onChange={(event) => setParam({ status: event.target.value || null })}
          aria-label="Filter by status"
          className="border-input bg-background h-9 rounded-md border px-2 text-sm"
        >
          <option value="">All statuses</option>
          {LIFECYCLE.map((status) => (
            <option key={status} value={status}>
              {STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error.message}
        </p>
      ) : null}

      {isPending ? <ListSkeleton /> : null}

      {data && data.items.length === 0 ? (
        <p className="text-muted-foreground rounded-md border border-dashed px-4 py-10 text-center text-sm">
          {query.search || query.status
            ? "No service records match these filters."
            : isManager
              ? "No service records yet. Open one from a vehicle."
              : "Nothing is assigned to you right now."}
        </p>
      ) : null}

      {data && data.items.length > 0 ? (
        <div
          className="rounded-md border"
          style={{ opacity: isPlaceholderData ? 0.6 : 1 }}
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Vehicle</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>
                  <SortButton
                    label="Status"
                    column="status"
                    query={query}
                    onSort={toggleSort}
                  />
                </TableHead>
                <TableHead>
                  <SortButton
                    label="Scheduled"
                    column="scheduled_date"
                    query={query}
                    onSort={toggleSort}
                  />
                </TableHead>
                <TableHead>Technicians</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {data.items.map((service) => (
                <TableRow key={service.id}>
                  <TableCell className="font-medium whitespace-nowrap">
                    <Link
                      href={`/services/${service.id}`}
                      className="hover:underline"
                    >
                      {service.vehicle.registration_number}
                    </Link>
                    <span className="text-muted-foreground ml-2 text-xs">
                      cycle {service.cycle_number}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground max-w-xs truncate">
                    {service.description}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={service.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap tabular-nums">
                    {service.scheduled_date ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs">
                    {service.technicians.length === 0
                      ? "Unassigned"
                      : service.technicians.map((t) => t.full_name).join(", ")}
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

      {isManager ? (
        <NewServiceModal open={creating} onClose={() => setCreating(false)} />
      ) : null}
    </main>
  );
}

function SortButton({
  label,
  column,
  query,
  onSort,
}: {
  label: string;
  column: ServiceSort;
  query: { sort: ServiceSort; order: "asc" | "desc" };
  onSort: (column: ServiceSort) => void;
}) {
  const active = query.sort === column;

  return (
    <button
      type="button"
      onClick={() => onSort(column)}
      className="hover:text-foreground flex items-center gap-1"
    >
      {label}
      {active ? <span aria-hidden>{query.order === "asc" ? "↑" : "↓"}</span> : null}
      {active ? (
        <span className="sr-only">
          sorted {query.order === "asc" ? "ascending" : "descending"}
        </span>
      ) : null}
    </button>
  );
}

function NewServiceModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const create = useCreateService();
  // Only live vehicles: an archived one refuses new records, so offering it
  // would be offering a 409.
  const { data: vehicles } = useVehicles({ limit: 100 });
  const [vehicleId, setVehicleId] = useState("");
  const [description, setDescription] = useState("");

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Open a service record"
      description="It starts Due, and the overdue clock starts now."
    >
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          create.mutate(
            { vehicle_id: Number(vehicleId), description },
            {
              onSuccess: () => {
                setVehicleId("");
                setDescription("");
                onClose();
              },
            },
          );
        }}
      >
        <div className="space-y-1.5">
          <label htmlFor="vehicle" className="text-sm font-medium">
            Vehicle
          </label>
          <select
            id="vehicle"
            required
            value={vehicleId}
            onChange={(event) => setVehicleId(event.target.value)}
            className="border-input bg-background h-9 w-full rounded-md border px-2 text-sm"
          >
            <option value="">Choose a vehicle</option>
            {vehicles?.items.map((vehicle) => (
              <option key={vehicle.id} value={vehicle.id}>
                {vehicle.registration_number} — {vehicle.make} {vehicle.model}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="description" className="text-sm font-medium">
            Description
          </label>
          <textarea
            id="description"
            required
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Brake inspection"
            className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        {create.error ? (
          <p
            role="alert"
            className="border-destructive/40 bg-destructive/10 text-destructive rounded-md border px-3 py-2 text-sm"
          >
            {create.error.message}
          </p>
        ) : null}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={create.isPending || !vehicleId}>
            {create.isPending ? "Opening…" : "Open record"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading services">
      {[0, 1, 2, 3, 4].map((row) => (
        <Skeleton key={row} className="h-10 w-full" />
      ))}
    </div>
  );
}
