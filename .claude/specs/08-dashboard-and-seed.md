# Spec 08 - Dashboard and Seed Data

## Overview

The fleet manager's dashboard, and the demo data that makes it worth looking
at. Goal 10 and CLAUDE.md Phases 15 and 16. This is the last spec before final
verification: every other goal is built.

## Depends on

Everything. The dashboard reads what specs 04 to 07 created, and the seed
script drives the same service layer rather than writing rows behind it.

## Current state

`/dashboard` is a placeholder showing who is signed in and the API status card.
`scripts/create_user.py` seeds users and nothing else.

## Time handling

This is the part most easily got wrong, so it is decided here once.

Everything is UTC. The database session is already pinned to UTC (spec 04), and
timestamps are stored `timestamptz`.

A week is an **ISO-8601 week**: Monday 00:00:00 UTC to Sunday 23:59:59.999 UTC.
"This week" is the ISO week containing now. "The last eight weeks" is the eight
ISO weeks ending with the current one - so the current week is the eighth
bucket, not a ninth.

Weeks with no completions are **included with a zero**. A chart that silently
drops empty weeks tells the reader the fleet was busy every week.

PostgreSQL's `date_trunc('week', ...)` is ISO - it starts on Monday - so the
bucketing is one SQL expression rather than Python date arithmetic.

## Business rules

1. The dashboard is fleet-manager only: **403** for a technician. It is a
   fleet-wide summary, and a technician's world is their assignments.
2. Every figure is computed by an **aggregate query**. No endpoint loads
   records and counts them in Python, and the frontend receives numbers, not
   rows.
3. Counts respect the same definitions as the rest of the system:
   * *Vehicles due* uses the same predicate as `GET /vehicles?due=true`.
   * *Overdue* uses the same predicate as the alerts list, **including**
     excluding dismissed alerts - the dashboard and the badge must not
     disagree.
   * Archived vehicles are excluded from every vehicle count.
4. "Completed this week" counts records whose `completed_at` falls in the
   current ISO week, in UTC.
5. The eight-week series returns exactly eight buckets, oldest first, each with
   its week-start date and a count, zeros included.
6. "By status" returns all four stored statuses, including those with zero.
   Overdue is not among them - it is derived, and is reported separately.
7. "By technician" returns every technician, including those with nothing
   assigned, so an idle technician is visible rather than absent.

## API

| method | route | authorization | response |
|---|---|---|---|
| GET | `/dashboard` | fleet_manager | the whole summary in one response |

One endpoint, not six. The dashboard is one screen; six round trips to paint it
would be six chances for a partial render, and the queries are cheap.

```
{
  "vehicles": {"total": 12, "due": 3, "overdue": 1, "in_service": 2, "archived": 1},
  "services": {"completed_this_week": 4, "open": 7},
  "by_status": [{"status": "due", "count": 3}, ...],
  "by_technician": [{"technician_id": 5, "full_name": "Sam Okafor", "open": 2, "completed": 9}, ...],
  "completed_per_week": [{"week_start": "2026-07-20", "count": 2}, ...]
}
```

## Seed data

`apps/api/scripts/seed_demo.py`, idempotent: it refuses to run against a
database that already has vehicles unless `--reset` is passed, so it cannot
quietly double the fleet.

It drives the **service layer**, not raw SQL. Seeding through `create_vehicle`,
`create_service`, `assign_technician` and `transition` means the demo data
obeys every rule the application does - and audit events, cycle numbers and
baselines come out right without being reproduced by hand.

It must produce:

* 2 fleet managers, 4 technicians
* ~12 vehicles, one archived
* Records in all four lifecycle states
* At least 2 vehicles due by mileage and 1 by date
* At least 2 overdue records, one of them dismissed, so both states show
* Completed services spread over the last eight weeks so the chart has shape
* Notes and a full audit timeline on several records

Backdating: completed records need `completed_at` in the past, which the
service layer always sets to now. The script writes those timestamps directly
**after** the transition, as a deliberate, commented exception - it is the one
thing the rules cannot express, because the rules are about the present.

Credentials go in `SUBMISSION.md`, which Claude drafts and the user pastes.

## Frontend

`app/(app)/dashboard/page.tsx` replaces the placeholder:

* Four stat tiles: due, overdue, in service, completed this week. Each is a
  link to the filtered list behind it, because a number a manager cannot act on
  is decoration.
* Records by status, as labelled bars with counts.
* Completed per week, an eight-bar chart. Recharts, as the stack specifies.
* Technician workload, a small table.
* A technician landing on `/dashboard` is redirected to `/services`.

Loading, empty and error states for each, not one spinner for the page.

## Tests

`apps/api/tests/test_dashboard.py`.

A technician gets 403. Every count matches a hand-built fixture: a due vehicle,
an overdue record, an in-service record and a completion this week produce
exactly 1 in each tile. Archived vehicles are excluded. A dismissed alert is
excluded from the overdue count, and the dashboard agrees with
`GET /alerts/count` - asserted by comparing them, since the two must never
disagree. `by_status` has four entries even when three are zero.
`by_technician` includes a technician with nothing assigned. The eight-week
series has exactly eight buckets, oldest first, with zeros for quiet weeks, and
a completion 60 days ago falls outside it.

## Definition of done

- [ ] Every rule has a test; the suite passes with no skips.
- [ ] The dashboard's overdue count and the alert badge agree, verified against
      the local database as well as in a test.
- [ ] `seed_demo.py` produces a database where every tile is non-zero and the
      chart has more than one non-zero week.
- [ ] The dashboard renders against seeded data.
- [ ] A technician is redirected away and the API refuses them.
- [ ] `docs/` updated: the UTC week definition and the one-endpoint decision.
- [ ] `SUBMISSION.md` draft handed over with demo credentials.

## Risks and open questions

1. **Backdating in the seed script bypasses the service layer.** Deliberate and
   commented, but it is the one place demo data is written by hand, and if the
   completion rules change it will not follow them.
2. **Six queries in one request.** Cheap at fleet scale and all indexed. If it
   ever matters the answer is a summary table, not a cache - already noted in
   `schema.md`.
3. **Recharts is the first chart dependency.** The stack names it, and one
   eight-bar chart does not justify hand-rolled SVG.
