# Spec 07 - Bulk Odometer Upload and Service History Export

## Overview

CSV in and CSV out. Goal 7 (bulk odometer updates with per-row results) and the
service history export, CLAUDE.md Phases 13 and 14.

Specced together because they are the same shape of problem from opposite ends,
and share nothing but that: one parses untrusted rows and must not be
all-or-nothing, the other streams trusted rows and must not be built in the
browser.

## Depends on

Specs 04 and 05. The odometer rule and the archived-vehicle rule already exist
in `vehicle_service`; this spec must reuse them rather than reimplement them
for CSV.

## Current state

Neither exists. `vehicle_service.require_odometer_not_lower` and
`require_not_archived` are the rules the upload has to apply, and they are
already written and tested.

## Bulk odometer upload

### Format

The vehicle is identified by **registration number**, not database id - a
manager uploading readings from the depot knows the plate, not a surrogate key.

Required header, exactly:

```
registration_number,odometer
```

### Business rules

1. Only a fleet manager may upload: **403** for a technician.
2. A missing or malformed header rejects the **whole upload** with **422**.
   That is the only whole-file rejection: it means the file is not the thing
   the endpoint takes, so no row in it can be trusted.
3. Every other failure is **per-row**. The response is 200 with a per-row
   result, not an error.
4. **Valid rows are applied even when other rows fail.** No transaction wraps
   the whole file. This is the rule the brief calls out, and the one an ORM
   makes easy to get wrong by accident.
5. Per-row rejections, each with a reason naming the row number:
   * unknown registration number
   * odometer missing, not an integer, or negative
   * reading lower than the vehicle's current reading
   * vehicle archived
   * the same registration appearing twice in one file
6. A reading **equal** to the current one is a success that changes nothing,
   reported as such rather than as an error.
7. A row that succeeds sets `current_odometer`. It does **not** touch
   `service_baseline_odometer` - a reading is not a service.
8. Upload size is capped (2 MB) and row count is capped (5,000). A CSV is
   read into memory to be parsed; an uncapped one is a way to take the process
   down.
9. Blank lines are skipped silently. A trailing newline is not a failed row.

### Response

```
{
  "total": 4, "succeeded": 2, "failed": 2,
  "results": [
    {"row": 1, "registration_number": "VAN001", "status": "success",
     "message": "Updated to 52300", "previous_odometer": 51000,
     "new_odometer": 52300},
    {"row": 2, "registration_number": "VAN002", "status": "rejected",
     "message": "New reading 76000 is lower than the existing reading 76500"}
  ]
}
```

Row numbers are the row in the **data**, 1-based, not counting the header -
what a person looking at the spreadsheet will count.

### API

| method | route | authorization | request | response |
|---|---|---|---|---|
| POST | `/vehicles/odometer-upload` | fleet_manager | multipart CSV | per-row report, 200 |

## Service history export

### Business rules

10. Only a fleet manager may export the whole fleet's history. A technician
    gets **403** - a fleet-wide export is not their view. (They can already see
    their own records in the UI; an export scoped to a technician is not a
    goal.)
11. The export is generated **server-side and streamed**, row by row from a
    query, never assembled in the browser and never by loading every record
    into memory first.
12. It accepts the same filters as `GET /services` - vehicle, status, date
    range - so "export what I am looking at" is the same query without paging.
13. Columns: registration, make, model, cycle, description, status, overdue,
    scheduled date, completed at, completion odometer, technicians, created at.
14. Timestamps are ISO-8601 UTC, matching the rest of the API.

### API

| method | route | authorization | response |
|---|---|---|---|
| GET | `/services/export.csv` | fleet_manager | `text/csv` stream, `Content-Disposition: attachment` |

## Audit events

Neither is audited.

An odometer upload changes vehicles, and `audit_events.service_id` is NOT NULL,
so the table cannot hold a vehicle-scoped event - the same gap already recorded
in `architecture.md`. Per-row results are returned to the caller and the run is
logged. An export changes nothing.

## Frontend

* `app/(app)/reports/page.tsx` - both, on one page, manager only.
  * Upload: file input, the expected header shown literally, and after a run a
    table of per-row results with successes and rejections distinguished by
    text as well as colour. The summary line says how many of each, because
    "12 rows, 3 rejected" is the thing a manager needs to see first.
  * Export: the same filter controls as the services page, and a download
    button.
* Download: the browser hits the URL with its bearer token via `fetch`, then
  saves the blob - an `<a download>` cannot carry an Authorization header.

## Tests

`apps/api/tests/test_bulk_odometer.py`, `test_export.py`.

Upload: a good file updates every vehicle; a technician gets 403; a missing
header is 422 and nothing is written; a malformed header is 422; **a file with
one bad row still applies the good rows** (the central one, asserted against
the database, not just the response); a lower reading is rejected with both
numbers in the message; an equal reading succeeds and changes nothing; an
unknown registration is rejected; a negative and a non-numeric odometer are
rejected; an archived vehicle's row is rejected; a duplicate registration in
one file rejects the second occurrence; blank lines are skipped; row numbers
match the data rows; a file over the row cap is refused.

Export: a manager gets CSV with the right header and one row per record; a
technician gets 403; filters narrow it; the response is a streaming response,
not a string built in memory; an overdue record reports overdue in its column;
a record with two technicians lists both in one cell.

## Definition of done

- [ ] Every rule has a test, suite passes with no skips.
- [ ] A CSV with a mix of good and bad rows is uploaded against the local
      database, and the good rows are confirmed applied by re-reading the
      vehicles - not by trusting the response.
- [ ] The malformed-header rejection leaves the database untouched.
- [ ] The export opens in a spreadsheet with readable columns.
- [ ] Reports page works against the local API, including the authenticated
      download.
- [ ] `docs/` updated: why the upload is not transactional, and why the
      identifier is the registration number.

## Risks and open questions

1. **Not wrapping the upload in a transaction is deliberate and unusual.** It
   contradicts the habit the rest of this codebase follows, so it needs to be
   said out loud in `decisions.md`: a depot upload where one row is wrong must
   not discard the other forty-nine.
2. **Per-row commits mean a partial run on a crash.** Acceptable - the rows
   that landed are all individually valid, and re-uploading is safe because a
   repeated reading is an accepted no-op. Worth stating.
3. **The export has no paging**, by design. The cap is the filter. At fleet
   scale this is fine; the streaming response is what keeps it honest if the
   dataset grows.
