"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ErrorState } from "@/components/ui/states";
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
import { downloadExport, useOdometerUpload } from "@/hooks/use-reports";
import { useTechnicians } from "@/hooks/use-technicians";
import { formatMiles } from "@/lib/format";
import { cn } from "@/lib/utils";
import { LIFECYCLE, STATUS_LABELS, type ServiceStatus } from "@/types/service";

export default function ReportsPage() {
  const router = useRouter();
  const { user, isLoading } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";

  useEffect(() => {
    if (!isLoading && user && !isManager) router.replace("/my-work");
  }, [isLoading, user, isManager, router]);

  if (!isManager) return null;

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-base font-semibold">Reports</h1>
        <p className="text-muted-foreground mt-0.5 text-sm">
          Bulk odometer readings in, service history out. Both are processed by
          the API, not assembled in the browser.
        </p>
      </header>

      <div className="grid gap-4 xl:grid-cols-2">
        <OdometerUploadCard />
        <ExportCard />
      </div>
    </div>
  );
}

function OdometerUploadCard() {
  const upload = useOdometerUpload();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);

  const report = upload.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bulk odometer upload</CardTitle>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        <div className="space-y-2">
          <p className="text-muted-foreground">
            A CSV identifying each vehicle by its registration number - the
            plate a depot actually knows, not a database id. The first line
            must be exactly:
          </p>
          <pre className="bg-muted overflow-x-auto rounded px-3 py-2 font-mono text-xs">
            registration_number,odometer
          </pre>
          <p className="text-muted-foreground text-xs">
            Rows are applied one at a time. A rejected row does not stop the
            others - a reading lower than the one on record, an unknown
            registration or an archived vehicle is refused on its own and the
            rest of the file still goes through.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".csv,text/csv"
            aria-label="Odometer CSV file"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              upload.reset();
            }}
            className={cn(
              "text-muted-foreground max-w-full text-sm",
              "file:bg-background file:text-foreground file:mr-3 file:rounded-md file:border file:px-3 file:py-1.5 file:text-sm",
              "file:hover:bg-muted file:transition-colors file:duration-120",
            )}
          />
          <Button
            disabled={!file || upload.isPending}
            onClick={() =>
              file &&
              upload.mutate(file, {
                onSuccess: (result) =>
                  toast(
                    `${result.succeeded} of ${result.total} readings applied`,
                  ),
              })
            }
          >
            {upload.isPending ? "Uploading…" : "Upload readings"}
          </Button>
        </div>

        {upload.error ? (
          <ErrorState
            title="The file was refused"
            // A 422 here is the whole file being refused - a bad header.
            message={upload.error.message}
          />
        ) : null}

        {report ? (
          <div className="space-y-3">
            <div
              role="status"
              className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm"
            >
              {/* Failures first: "3 rejected" is what a manager needs to see
                  before anything else. */}
              {report.failed > 0 ? (
                <span className="text-overdue font-medium tabular-nums">
                  {report.failed} rejected
                </span>
              ) : null}
              <span className="text-completed font-medium tabular-nums">
                {report.succeeded} applied
              </span>
              <span className="text-muted-foreground tabular-nums">
                {report.total} {report.total === 1 ? "row" : "rows"} in the file
              </span>
            </div>

            <div className="max-h-96 overflow-auto rounded-md border">
              <Table className="sticky-head">
                <TableHeader>
                  <TableRow>
                    <TableHead>Row</TableHead>
                    <TableHead>Registration</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead>Reading</TableHead>
                    <TableHead>Detail</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.results.map((result) => (
                    <TableRow
                      key={result.row}
                      className={cn(
                        "border-l-2",
                        result.status === "success"
                          ? "border-l-completed"
                          : "border-l-overdue",
                      )}
                    >
                      <TableCell className="text-muted-foreground tabular-nums">
                        {result.row}
                      </TableCell>
                      <TableCell className="font-medium whitespace-nowrap">
                        {result.registration_number ?? "—"}
                      </TableCell>
                      <TableCell>
                        {/* Text, not just colour. */}
                        <Badge
                          tone={
                            result.status === "success" ? "completed" : "overdue"
                          }
                        >
                          {result.status === "success" ? "Applied" : "Rejected"}
                        </Badge>
                      </TableCell>
                      <TableCell className="whitespace-nowrap tabular-nums">
                        {result.status === "success" &&
                        result.new_odometer !== null ? (
                          <span className="text-muted-foreground">
                            {result.previous_odometer !== null
                              ? `${formatMiles(result.previous_odometer)} → `
                              : ""}
                            <span className="text-foreground">
                              {formatMiles(result.new_odometer)}
                            </span>
                          </span>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {/* The server's own wording, including the two numbers
                            that explain a rejection. */}
                        {result.message}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ExportCard() {
  const { data: technicians } = useTechnicians(true);
  const [status, setStatus] = useState<ServiceStatus | "">("");
  const [vehicleId, setVehicleId] = useState<number | undefined>(undefined);
  const [technicianId, setTechnicianId] = useState("");
  const [overdue, setOverdue] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  async function download() {
    setPending(true);
    setError(null);
    try {
      await downloadExport({
        status: status || undefined,
        vehicle_id: vehicleId,
        technician_id: technicianId ? Number(technicianId) : undefined,
        overdue: overdue ? true : undefined,
      });
      toast("Export downloaded");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Export failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Service history export</CardTitle>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        <p className="text-muted-foreground">
          Generated by the API and streamed as CSV, filtered the same way the
          service list is. Leave every filter empty to export the whole history.
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="export-vehicle">Vehicle</Label>
            <VehiclePicker
              id="export-vehicle"
              value={vehicleId}
              onChange={setVehicleId}
              includeArchived
              placeholder="All vehicles"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="export-status">Status</Label>
            <Select
              id="export-status"
              value={status}
              onChange={(event) =>
                setStatus(event.target.value as ServiceStatus | "")
              }
              className="h-8 w-full"
            >
              <option value="">All statuses</option>
              {LIFECYCLE.map((value) => (
                <option key={value} value={value}>
                  {STATUS_LABELS[value]}
                </option>
              ))}
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="export-technician">Technician</Label>
            <Select
              id="export-technician"
              value={technicianId}
              onChange={(event) => setTechnicianId(event.target.value)}
              className="h-8 w-full"
            >
              <option value="">All technicians</option>
              {technicians?.map((person) => (
                <option key={person.id} value={person.id}>
                  {person.full_name}
                </option>
              ))}
            </Select>
          </div>

          <div className="flex items-end">
            <label
              className={cn(
                "flex h-8 w-full cursor-pointer items-center gap-2 rounded-md border px-2.5 text-sm transition-colors duration-120",
                overdue
                  ? "border-overdue/30 bg-overdue-soft text-overdue font-medium"
                  : "text-muted-foreground hover:bg-muted/60",
              )}
            >
              <input
                type="checkbox"
                checked={overdue}
                onChange={(event) => setOverdue(event.target.checked)}
                className="size-3.5"
              />
              Overdue only
            </label>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button onClick={download} disabled={pending}>
            {pending ? "Preparing…" : "Download CSV"}
          </Button>
          <p className="text-muted-foreground text-xs">
            One row per service record, with its vehicle, dates, status and
            assigned technicians.
          </p>
        </div>

        {error ? <ErrorState title="Export failed" message={error} /> : null}
      </CardContent>
    </Card>
  );
}
