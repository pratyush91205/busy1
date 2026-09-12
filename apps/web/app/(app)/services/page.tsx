"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";

import { NewServiceModal } from "@/components/services/new-service-modal";
import { StatusBadge, accentFor } from "@/components/services/status-badge";
import { Button } from "@/components/ui/button";
import { FilterBar, FilterChip } from "@/components/ui/filter-bar";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
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
import { VehiclePicker } from "@/components/vehicles/vehicle-picker";
import { useCurrentUser } from "@/hooks/use-auth";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useQueryParams } from "@/hooks/use-query-params";
import { downloadExport } from "@/hooks/use-reports";
import { useServices } from "@/hooks/use-services";
import { useTechnicians } from "@/hooks/use-technicians";
import { formatDate, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  LIFECYCLE,
  STATUS_LABELS,
  type ServiceQuery,
  type ServiceSort,
  type ServiceStatus,
} from "@/types/service";

export default function ServicesPage() {
  // useSearchParams needs a Suspense boundary for the statically-rendered
  // shell; the view below it reads the URL as its own state.
  return (
    <Suspense fallback={<TableSkeleton label="Loading services" columns={6} />}>
      <ServicesView />
    </Suspense>
  );
}

function ServicesView() {
  const { params, setParams } = useQueryParams("/services");
  const { user } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";
  const toast = useToast();

  const [creating, setCreating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Every filter the API accepts is read from the URL, so a link from the
  // dashboard - /services?technician_id=5 - arrives filtered rather than
  // quietly showing the whole fleet.
  const query: ServiceQuery = {
    search: params.get("search") || undefined,
    status: (params.get("status") as ServiceStatus) || undefined,
    vehicle_id: Number(params.get("vehicle_id")) || undefined,
    technician_id: Number(params.get("technician_id")) || undefined,
    overdue: params.get("overdue") === "true" ? true : undefined,
    sort: (params.get("sort") as ServiceSort) || "updated_at",
    order: params.get("order") === "asc" ? "asc" : "desc",
    page: Number(params.get("page")) || 1,
    limit: Number(params.get("limit")) || 20,
  };

  const { data, error, isPending, isPlaceholderData, refetch } =
    useServices(query);
  const { data: technicians } = useTechnicians(Boolean(isManager));

  // The input stays instant; only the request waits for the typing to stop.
  const [searchInput, setSearchInput] = useState(params.get("search") ?? "");
  const debouncedSearch = useDebouncedValue(searchInput, 300);

  useEffect(() => {
    const current = params.get("search") ?? "";
    if (debouncedSearch !== current) setParams({ search: debouncedSearch });
  }, [debouncedSearch, params, setParams]);

  function toggleSort(column: ServiceSort) {
    const same = query.sort === column;
    setParams({
      sort: column,
      order: same && query.order === "desc" ? "asc" : "desc",
    });
  }

  function clearFilters() {
    setSearchInput("");
    setParams({
      search: null,
      status: null,
      vehicle_id: null,
      technician_id: null,
      overdue: null,
    });
  }

  async function exportView() {
    setExporting(true);
    setExportError(null);
    try {
      // The same query object the table is showing, minus the paging: the
      // export is "what I am looking at", not "page 2 of it".
      await downloadExport(query);
      toast("Export downloaded");
    } catch (cause) {
      setExportError(
        cause instanceof Error
          ? cause.message
          : "Could not generate the export.",
      );
    } finally {
      setExporting(false);
    }
  }

  const technicianName = technicians?.find(
    (person) => person.id === query.technician_id,
  )?.full_name;

  const hasFilters = Boolean(
    query.search ||
      query.status ||
      query.vehicle_id ||
      query.technician_id ||
      query.overdue,
  );

  const sort = query.sort ?? "updated_at";
  const order = query.order ?? "desc";

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-base font-semibold">Service records</h1>
          <p className="text-muted-foreground mt-0.5 text-sm">
            {/* A technician's list is already scoped by the server, so the
                count is honest for whoever is reading it. */}
            {data
              ? isManager
                ? `${data.total} across the fleet`
                : `${data.total} assigned to you`
              : " "}
          </p>
        </div>

        {isManager ? (
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={exportView} disabled={exporting}>
              {exporting ? "Preparing…" : "Export this view"}
            </Button>
            <Button onClick={() => setCreating(true)}>New service record</Button>
          </div>
        ) : null}
      </header>

      <FilterBar>
        <Input
          type="search"
          placeholder="Search descriptions"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          className="w-56"
          aria-label="Search service records"
        />

        <VehiclePicker
          value={query.vehicle_id}
          onChange={(vehicleId) => setParams({ vehicle_id: vehicleId ?? null })}
          includeArchived
          placeholder="All vehicles"
          className="w-52"
        />

        <Select
          value={query.status ?? ""}
          onChange={(event) => setParams({ status: event.target.value })}
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          {LIFECYCLE.map((status) => (
            <option key={status} value={status}>
              {STATUS_LABELS[status]}
            </option>
          ))}
        </Select>

        {isManager ? (
          <Select
            value={query.technician_id ? String(query.technician_id) : ""}
            onChange={(event) =>
              setParams({ technician_id: event.target.value })
            }
            aria-label="Filter by technician"
          >
            <option value="">All technicians</option>
            {technicians?.map((person) => (
              <option key={person.id} value={person.id}>
                {person.full_name}
              </option>
            ))}
          </Select>
        ) : null}

        <label
          className={cn(
            "flex h-8 cursor-pointer items-center gap-2 rounded-md border px-2.5 text-sm transition-colors duration-120",
            query.overdue
              ? "border-overdue/30 bg-overdue-soft text-overdue font-medium"
              : "text-muted-foreground hover:bg-muted/60",
          )}
        >
          <input
            type="checkbox"
            checked={Boolean(query.overdue)}
            onChange={(event) => setParams({ overdue: event.target.checked })}
            className="size-3.5"
          />
          Overdue only
        </label>
      </FilterBar>

      {hasFilters ? (
        <div className="flex flex-wrap items-center gap-2">
          {query.search ? (
            <FilterChip
              label="Search"
              value={query.search}
              onClear={() => {
                setSearchInput("");
                setParams({ search: null });
              }}
            />
          ) : null}
          {query.status ? (
            <FilterChip
              label="Status"
              value={STATUS_LABELS[query.status]}
              onClear={() => setParams({ status: null })}
            />
          ) : null}
          {query.technician_id ? (
            <FilterChip
              label="Technician"
              value={technicianName ?? `#${query.technician_id}`}
              onClear={() => setParams({ technician_id: null })}
            />
          ) : null}
          {query.overdue ? (
            <FilterChip
              label="State"
              value="Overdue"
              onClear={() => setParams({ overdue: null })}
            />
          ) : null}

          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear all
          </Button>
        </div>
      ) : null}

      {exportError ? (
        <ErrorState title="Export failed" message={exportError} />
      ) : null}

      {error ? (
        <ErrorState message={error.message} onRetry={() => void refetch()} />
      ) : null}

      {isPending ? <TableSkeleton label="Loading services" columns={6} /> : null}

      {data && data.items.length === 0 ? (
        <EmptyState
          title={
            hasFilters
              ? "No service records match these filters"
              : isManager
                ? "No service records yet"
                : "Nothing is assigned to you right now"
          }
          hint={
            hasFilters
              ? "Clear a filter to widen the search."
              : isManager
                ? "Open one against a vehicle to start a service cycle."
                : "A fleet manager assigns work; anything assigned to you appears here."
          }
          action={
            hasFilters ? (
              <Button variant="outline" size="sm" onClick={clearFilters}>
                Clear filters
              </Button>
            ) : null
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
                <TableHead>Vehicle</TableHead>
                <TableHead>Description</TableHead>
                <SortableHead
                  label="Status"
                  column="status"
                  active={sort}
                  order={order}
                  onSort={toggleSort}
                />
                <SortableHead
                  label="Scheduled"
                  column="scheduled_date"
                  active={sort}
                  order={order}
                  onSort={toggleSort}
                />
                <TableHead>Technicians</TableHead>
                <SortableHead
                  label="Updated"
                  column="updated_at"
                  active={sort}
                  order={order}
                  onSort={toggleSort}
                />
              </TableRow>
            </TableHeader>

            <TableBody>
              {data.items.map((service) => (
                <TableRow
                  key={service.id}
                  className={cn(
                    "border-l-2",
                    accentFor(service.status, service.is_overdue),
                  )}
                >
                  <TableCell className="whitespace-nowrap">
                    <Link
                      href={`/services/${service.id}`}
                      className="font-medium hover:underline"
                    >
                      {service.vehicle.registration_number}
                    </Link>
                    <span className="text-muted-foreground ml-2 text-xs">
                      cycle {service.cycle_number}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground max-w-[22rem] truncate">
                    <Link
                      href={`/services/${service.id}`}
                      className="hover:text-foreground"
                    >
                      {service.description}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <StatusBadge
                      status={service.status}
                      isOverdue={service.is_overdue}
                    />
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {formatDate(service.scheduled_date)}
                  </TableCell>
                  <TableCell className="text-muted-foreground max-w-[14rem] truncate text-xs">
                    {service.technicians.length === 0 ? (
                      <span className="text-muted-foreground/70">
                        Unassigned
                      </span>
                    ) : (
                      service.technicians.map((t) => t.full_name).join(", ")
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs whitespace-nowrap">
                    {formatDateTime(service.updated_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      {data && data.total > 0 ? (
        <Pagination
          page={data}
          label="records"
          onPage={(page) => setParams({ page })}
          onLimit={(limit) => setParams({ limit, page: 1 })}
        />
      ) : null}

      {isManager ? (
        <NewServiceModal open={creating} onClose={() => setCreating(false)} />
      ) : null}
    </div>
  );
}
