# Spec 06 - Due Calculation, Overdue and Alerts

## Overview

When a vehicle needs servicing, when a service record has been ignored too
long, and the alerts a fleet manager sees and dismisses. Goals 6 (due and
overdue with a grace period) and 9 (overdue alerts, cycle-scoped dismissal),
and CLAUDE.md Phases 9 and 11.

## Depends on

Spec 05, for completed service records. The whole calculation counts from the
last completed service, so it has nothing to count from until records can be
completed.

## Current state

`vehicles.service_date_interval` and `service_mileage_interval` are stored and
editable but nothing reads them. `service_records.due_since` is written on
creation and cleared on completion, and nothing reads it either.
`overdue_alert_dismissals` is migrated and unused. `OVERDUE_GRACE_PERIOD_DAYS`
is already in `Settings` with a default of 7.

## Two different questions

These are easy to conflate and must not be.

**Is a vehicle due for service?** Derived from the vehicle's intervals and its
last completed service. It is a statement about a *vehicle*, and it is what
tells a manager to open a record.

**Is a service record overdue?** Derived from `status == due`, `due_since` and
the grace period. It is a statement about a *record* - one that was opened and
then left unbooked.

A vehicle can be due with no record open. A record can be overdue for a vehicle
that would not otherwise be due yet. Both are computed from persisted data and
the clock, so neither needs a background job to be correct.

## Data model

No migration.

Nothing about due-ness is stored. `due_since` is stored, but it records *when a
cycle became due*, not whether it is - that distinction is the point of
`decisions.md` 4: recomputing it would let an edit to a vehicle's intervals
silently move an overdue clock that is already running.

## Business rules

### Vehicle due-ness

1. A vehicle is due when **either** condition holds, not both:
   * `today >= last_completed_date + service_date_interval` days, or
   * `current_odometer >= last_completed_odometer + service_mileage_interval`.
2. Both are measured from the **most recent completed service**. A vehicle with
   no completed service counts from its `created_at` and the odometer it was
   created with, so a new vehicle is not instantly due.
3. An archived vehicle is never due. It is not in service.
4. Due-ness is reported with the reason - `date`, `mileage`, or `both` - and
   with what it is measured against, so a manager can see why.

### Record overdue-ness

5. A record is overdue when `status == due` **and**
   `now >= due_since + OVERDUE_GRACE_PERIOD_DAYS`.
6. Booking it stops it being overdue, immediately: the status is no longer
   `due`. That is the whole mechanism - there is nothing to clear.
7. Overdue is **derived, never stored**. It is not a fifth status, the status
   column still holds only the four, and `GET /services?status=...` still takes
   only those four. A separate `overdue=true` filter selects them.
8. Completing a cycle clears `due_since`, so a completed record is never
   overdue. Already true from spec 05; asserted here.

### Alerts

9. An alert is not a row. It **is** an overdue record. There is no table of
   alerts to create, reconcile or clean up, and therefore nothing that can
   disagree with the records themselves.
10. A fleet manager may dismiss an alert. Dismissal writes one
    `overdue_alert_dismissals` row against that `service_id`.
11. A dismissed alert does not appear in the alert list and does not count in
    the badge. The record is still overdue - dismissal hides the alert, it does
    not fix the maintenance.
12. Dismissal is **cycle-scoped by construction**: one record is one cycle, and
    the dismissal points at the record. The next cycle is a different record
    with no dismissal against it, so its alert appears without anything
    needing to reset.
13. Dismissing twice is **409**. Dismissing a record that is not overdue is
    **409** - there is nothing to dismiss.
14. Only a fleet manager sees or dismisses alerts: **403** for a technician.
    Alerts are a fleet-wide view, and a technician's world is their own
    assignments.

## Permissions

**Fleet Manager** - everything.

**Technician** - may see `is_overdue` on a record they are assigned to, because
it is part of that record. `GET /alerts` and dismissal are 403.

## API

| method | route | authorization | response |
|---|---|---|---|
| GET | `/alerts` | fleet_manager | `Page[AlertRead]` - overdue, undismissed, oldest first |
| GET | `/alerts/count` | fleet_manager | `{count}` for the nav badge |
| POST | `/alerts/{service_id}/dismiss` | fleet_manager | 204; 409 if already dismissed or not overdue |

Extended, not new:

* `ServiceRead` gains `is_overdue` and `overdue_since`.
* `GET /services` gains `overdue=true|false`.
* `VehicleRead` gains a `service_status` object: `is_due`, `reason`,
  `next_due_date`, `next_due_odometer`, `last_completed_at`, `has_open_record`.
* `GET /vehicles` gains `due=true` to list vehicles needing a record.

All of it computed in SQL where it drives a filter, so paging and totals stay
honest. Nothing is filtered in Python after the fact.

## Audit events

Dismissal is **not** audited. `audit_events.service_id` is `NOT NULL` so the
table could hold it, but the five event types are a closed set with a CHECK
constraint, and adding a sixth for a UI convenience is a migration for little
gain. The dismissal row already records who and when.

Worth a line in `docs/architecture.md` - the dismissal table *is* the record.

## Frontend

* `app/(app)/alerts/page.tsx` - overdue records, how long each has been
  overdue, the vehicle, and a Dismiss button with a confirmation that says
  plainly that dismissing does not fix the maintenance.
* Nav badge on Alerts showing the count, polled on a modest interval. Manager
  only; a technician never sees it.
* `StatusBadge` gains `overdue` - shown in place of `DUE`, still with readable
  text, and still a `due` record underneath.
* Vehicle detail gains a "Next service" panel: due or not, why, and what it is
  counted from.
* Vehicles list gains a DUE badge and a "due only" filter.

## Tests

`apps/api/tests/test_due.py`, `test_overdue_alerts.py`.

Due: date interval reached → due; mileage interval reached → due; neither →
not due; both → due with reason `both`; measured from the last completed
service, not from vehicle creation, proved by completing a service and watching
a due vehicle stop being due; a vehicle with no completed service counts from
creation; an archived vehicle is never due.

Overdue: due plus grace exceeded plus unbooked → overdue; due within grace →
not overdue; booked past the grace period → not overdue; completed → not
overdue; the grace period is read from settings, proved by building an app with
a different value and getting a different answer.

Alerts: an overdue record appears; dismissing removes it from the list and the
count; the record is still overdue afterwards; dismissing twice is 409;
dismissing a non-overdue record is 409; a technician gets 403 on both; and the
one that matters - complete the cycle, open the next, age it past the grace
period, and a new alert appears with no dismissal needed.

`overdue=true` on the service list returns exactly the overdue ones, and
`status=overdue` is still a 422.

## Definition of done

- [ ] Every rule has a test; suite passes with no skips.
- [ ] A vehicle becomes due by date and by mileage independently, verified
      against the local database by editing intervals and odometers.
- [ ] Completing a service makes a due vehicle not due, and the next interval
      counts from the completion.
- [ ] An alert appears after the grace period, is dismissed, stays dismissed,
      and a new cycle produces a new alert.
- [ ] The grace period comes from `OVERDUE_GRACE_PERIOD_DAYS`, with no
      hard-coded 7 anywhere in the service layer.
- [ ] Alerts page and nav badge work against the local API.
- [ ] `docs/` updated: the two-questions distinction, and why alerts are not a
      table.

## Risks and open questions

1. **Due-ness for a vehicle with no completed service counts from
   `created_at`.** Reasonable - a vehicle added today should not be instantly
   due - but it means a vehicle seeded with a long history looks freshly
   serviced. The seed data in Phase 16 must create completed records with real
   dates rather than relying on this.
2. **Time is injected, not taken from `datetime.now()` inside the rules.** The
   due and overdue functions take `now` as an argument so tests can age a
   record without sleeping or patching the clock. Slightly more verbose;
   the alternative is untestable.
3. **The nav badge polls.** No websockets, no push. A count that is up to a
   minute stale is not a correctness problem, because nothing acts on it.
