"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCurrentUser } from "@/hooks/use-auth";
import { downloadExport, useOdometerUpload } from "@/hooks/use-reports";
import { useVehicles } from "@/hooks/use-vehicles";
import { LIFECYCLE, STATUS_LABELS, type ServiceStatus } from "@/types/service";

export default function ReportsPage() {
  const router = useRouter();
  const { user, isLoading } = useCurrentUser();
  const isManager = user?.role === "fleet_manager";

  useEffect(() => {
    if (!isLoading && user && !isManager) router.replace("/services");
  }, [isLoading, user, isManager, router]);

  if (!isManager) return null;

  return (
    <main className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">Reports</h1>
        <p className="text-muted-foreground text-sm">
          Bulk odometer readings in, service history out.
        </p>
      </header>

      <OdometerUploadCard />
      <ExportCard />
    </main>
  );
}

function OdometerUploadCard() {
  const upload = useOdometerUpload();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);

  const report = upload.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          Bulk odometer upload
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        <div className="space-y-2">
          <p className="text-muted-foreground">
            A CSV identifying each vehicle by its registration number. The first
            line must be exactly:
          </p>
          <pre className="bg-muted overflow-x-auto rounded-md px-3 py-2 font-mono text-xs">
            registration_number,odometer
          </pre>
          <p className="text-muted-foreground text-xs">
            Rows are applied one at a time. A rejected row does not stop the
            others — a reading lower than the one on record, an unknown
            registration or an archived vehicle is refused on its own and the
            rest of the file still goes through.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            aria-label="Odometer CSV file"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              upload.reset();
            }}
            className="text-sm file:mr-3 file:rounded-md file:border file:bg-background file:px-3 file:py-1.5 file:text-sm"
          />
          <Button
            disabled={!file || upload.isPending}
            onClick={() => file && upload.mutate(file)}
          >
            {upload.isPending ? "Uploading…" : "Upload readings"}
          </Button>
        </div>

        {upload.error ? (
          <p
            role="alert"
            className="border-destructive/40 bg-destructive/10 text-destructive rounded-md border px-3 py-2"
          >
            {/* A 422 here is the whole file being refused - a bad header. */}
            {upload.error.message}
          </p>
        ) : null}

        {report ? (
          <div className="space-y-3">
            <p
              className="font-medium"
              role="status"
              // The count first: "12 rows, 3 rejected" is what a manager needs
              // to see before any detail.
            >
              {report.total} {report.total === 1 ? "row" : "rows"} ·{" "}
              {report.succeeded} applied · {report.failed} rejected
            </p>

            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Row</TableHead>
                    <TableHead>Registration</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead>Detail</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.results.map((result) => (
                    <TableRow key={result.row}>
                      <TableCell className="tabular-nums">{result.row}</TableCell>
                      <TableCell className="font-medium">
                        {result.registration_number ?? "—"}
                      </TableCell>
                      <TableCell>
                        {/* Text, not just colour. */}
                        <Badge
                          tone={result.status === "success" ? "success" : "danger"}
                        >
                          {result.status === "success" ? "APPLIED" : "REJECTED"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
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
  const { data: vehicles } = useVehicles({ limit: 100, include_archived: true });
  const [status, setStatus] = useState<ServiceStatus | "">("");
  const [vehicleId, setVehicleId] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setPending(true);
    setError(null);
    try {
      await downloadExport({
        status: status || undefined,
        vehicle_id: vehicleId ? Number(vehicleId) : undefined,
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Export failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          Service history export
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        <p className="text-muted-foreground">
          Generated by the API and streamed as CSV. Leave the filters empty to
          export the whole history.
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={vehicleId}
            onChange={(event) => setVehicleId(event.target.value)}
            aria-label="Filter the export by vehicle"
            className="border-input bg-background h-9 rounded-md border px-2 text-sm"
          >
            <option value="">All vehicles</option>
            {vehicles?.items.map((vehicle) => (
              <option key={vehicle.id} value={vehicle.id}>
                {vehicle.registration_number}
              </option>
            ))}
          </select>

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as ServiceStatus | "")}
            aria-label="Filter the export by status"
            className="border-input bg-background h-9 rounded-md border px-2 text-sm"
          >
            <option value="">All statuses</option>
            {LIFECYCLE.map((value) => (
              <option key={value} value={value}>
                {STATUS_LABELS[value]}
              </option>
            ))}
          </select>

          <Button onClick={download} disabled={pending}>
            {pending ? "Preparing…" : "Download CSV"}
          </Button>
        </div>

        {error ? (
          <p role="alert" className="text-destructive">
            {error}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
