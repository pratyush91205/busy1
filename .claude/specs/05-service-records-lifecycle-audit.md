# Spec 05 - Service Records, Assignment, Lifecycle and Audit

## Overview

The core of the system, specced as one piece because its parts cannot honestly
be separated: every mutation below must emit its audit event in the same
transaction, so building the mutations first and the audit trail later means
writing them twice.

Covers goals 3 (service records), 4 (technician assignment), 5 (service
lifecycle) and 8 (immutable audit timeline), and CLAUDE.md Phases 6, 7, 8 and
the API half of 10.

Due and overdue calculation is deliberately **not** here. It needs the
completed-service history this spec creates, and it is spec 06.

## Depends on

Specs 02 to 04. `service_records`, `service_technicians`, `service_notes` and
`audit_events` are already migrated, including `cycle_number` and `due_since`,
and `audit_events` already has the triggers that refuse UPDATE and DELETE.

## Current state

Four tables with no code above them. `test_schema.py` proves the constraints
and the immutability triggers work; nothing creates a row.

## Data model

No migration.

`cycle_number` is per vehicle and assigned by the service layer: the first
record for a vehicle is 1, each later one is `max + 1`. The unique constraint
on `(vehicle_id, cycle_number)` is what makes a concurrent double-create fail
rather than silently produce two cycle 3s.

A vehicle may have **at most one open record** - anything not `completed`.
Without that rule "the current service cycle" is not well defined, and spec 06
has nothing to compute due-ness against.

## Business rules

### Records

1. Only a fleet manager creates a service record. Technician: **403**.
2. A record is created against a live vehicle. An archived vehicle is **409**.
3. A vehicle with an open record (status not `completed`) is **409**. One open
   cycle at a time.
4. A new record starts at `due`, with `due_since` set to now. Status is not
   accepted from the client on create.
5. The description may be edited by a fleet manager, or by a technician
   **currently assigned** to that record. Any other technician: **403**.
6. The description-update endpoint accepts a description and nothing else. It
   has no `status`, no `vehicle_id` and no technician list, so an assigned
   technician cannot smuggle a reassignment through it. This is enforced by the
   schema's shape, not by filtering fields at runtime.

### Lifecycle

7. The only legal transitions are `due -> booked`, `booked -> in_service`,
   `in_service -> completed`. Everything else is **409** naming both states.
   Validation is one function, `validate_transition`, and no route decides for
   itself.
8. `booked` requires a `scheduled_date`. Booking without one is **422**.
9. Completing requires a `completion_odometer`, which must be at least the
   vehicle's `current_odometer` - the vehicle cannot have travelled backwards
   between services. Lower is **409**.
10. Completing, in one transaction: set status, write `completed_at` and
    `completion_odometer`, raise the vehicle's `current_odometer` to it, clear
    `due_since`, and write the audit event. If any part fails, none of it
    happens.
11. A manager may perform any legal transition. An assigned technician may
    perform `booked -> in_service` and `in_service -> completed` - the work they
    actually do. Booking is a manager's, because it sets the schedule.

### Assignment

12. Only a fleet manager assigns or unassigns. Technician: **403**, including
    unassigning themselves.
13. The assignee must exist and have the `technician` role. Assigning a manager
    is **409**.
14. Assigning someone already assigned is **409**; unassigning someone who is
    not is **404**.
15. Assignment is refused on a `completed` record: **409**. Its history is
    finished.

### Notes

16. A note may be added by a fleet manager or an assigned technician. Any other
    technician: **403**.
17. Notes are append-only. No endpoint updates or deletes one.

### Visibility

18. A technician sees only records they are assigned to. `GET /services`
    filters to their assignments, and `GET /services/{id}` for an unassigned
    record is **404**, not 403 - a technician should not learn which record ids
    exist.
19. A fleet manager sees everything.

## Permissions

| action | manager | technician |
|---|---|---|
| list / read services | all | assigned only |
| create record | yes | 403 |
| edit description | yes | if assigned |
| book (`due -> booked`) | yes | 403 |
| start (`booked -> in_service`) | yes | if assigned |
| complete (`in_service -> completed`) | yes | if assigned |
| assign / unassign | yes | 403 |
| add note | yes | if assigned |
| read timeline | yes | if assigned |

## API

`GET /services` query parameters: `search` (description), `vehicle_id`,
`status`, `technician_id`, `sort` (`scheduled_date` | `status` | `updated_at`,
default `updated_at`), `order`, `page`, `limit`.

| method | route | authorization | notes |
|---|---|---|---|
| GET | `/services` | any authenticated | technician scoped to own; `Page[ServiceRead]` |
| GET | `/services/{id}` | any authenticated | 404 when a technician is not assigned |
| POST | `/services` | fleet_manager | 201; vehicle must be live and have no open cycle |
| PATCH | `/services/{id}` | manager or assigned technician | description only |
| POST | `/services/{id}/transition` | role depends on transition | `{status, scheduled_date?, completion_odometer?}` |
| POST | `/services/{id}/technicians` | fleet_manager | `{technician_id}` |
| DELETE | `/services/{id}/technicians/{technician_id}` | fleet_manager | 204 |
| GET | `/services/{id}/notes` | manager or assigned | |
| POST | `/services/{id}/notes` | manager or assigned | 201 |
| GET | `/services/{id}/timeline` | manager or assigned | audit events, oldest first |

One `transition` endpoint rather than `/book`, `/start`, `/complete`: the
target status is data, the validation table is one place, and adding a status
later does not add a route.

There is **no** update or delete for audit events, and none for notes.

## Audit events

Written in the same transaction as the change they describe, never after.

| trigger | type | old_value | new_value | metadata |
|---|---|---|---|---|
| record created | `service_created` | null | `due` | `{vehicle_id, cycle_number}` |
| transition | `status_changed` | old status | new status | `{scheduled_date}` or `{completion_odometer}` |
| assign | `technician_assigned` | null | technician id | `{technician_name}` |
| unassign | `technician_unassigned` | technician id | null | `{technician_name}` |
| note added | `note_added` | null | note id | `{}` |

`actor_id` is the authenticated user on every one of these.

## Frontend

* `app/(app)/services/page.tsx` - table with search, vehicle, status and
  technician filters, sortable columns, paging, all in the URL. A technician
  gets the same page already scoped by the server.
* `app/(app)/services/[id]/page.tsx` - vehicle, description, status, the
  lifecycle rendered as four steps with the current one marked, assigned
  technicians, notes, and the timeline.
* Only legal next actions are offered, and only to a user allowed them. The
  server still enforces both; the UI is saving a round trip, not deciding.
* `components/services/status-badge.tsx` - one mapping from status to label and
  tone, used everywhere. Overdue is added to it in spec 06.
* Vehicle detail's "service history" placeholder is replaced with the real list.

## Tests

`apps/api/tests/test_services.py`, `test_lifecycle.py`, `test_assignment.py`,
`test_audit.py`.

Lifecycle, as a table: all three legal transitions succeed; `due -> completed`,
`due -> in_service`, `completed -> booked`, `completed -> in_service`,
`booked -> due` and every other pair are 409. Same status to itself is 409.

Records: manager creates, technician 403; archived vehicle 409; a second open
record for one vehicle 409; a new record is `due` with `due_since` set; a
client-supplied `status` on create is ignored; description edited by manager
and by assigned technician, 403 for an unassigned one; the update schema
rejects `status` and `technician_ids` outright.

Completion: vehicle odometer rises to the completion reading; a completion
odometer below the vehicle's is 409; `due_since` is cleared; and - the one that
matters - if the audit insert fails, the status change is rolled back too.

Assignment: manager assigns and unassigns; technician 403 both ways; assigning
a manager 409; double assign 409; unassign of a non-assignee 404; assignment on
a completed record 409.

Visibility: a technician's list contains only their records, across more than
one vehicle; another technician's record is 404 not 403.

Audit: each of the five events is written with the right actor, old and new
values; the timeline is ordered oldest first; UPDATE and DELETE on
`audit_events` still raise (already covered in `test_schema.py`, asserted again
through the API surface by confirming no such route exists).

## Definition of done

- [ ] Every rule above has a test, and the suite passes with no skips.
- [ ] The full manager workflow works with curl against the local database:
      create vehicle, create record, assign two technicians, book, start,
      complete, and read a timeline showing every step with its actor.
- [ ] A technician's token: sees only their own records, can start and complete
      an assigned one, is refused booking, assignment and another's record.
- [ ] Completing raises the vehicle odometer and clears `due_since`.
- [ ] A forced failure inside the completion transaction leaves the service
      unchanged - verified by a test, not by reading the code.
- [ ] No route updates or deletes an audit event or a note.
- [ ] Services and service detail pages work against the local API.
- [ ] Roughly eight to twelve commits.
- [ ] `docs/` updated: the one-open-cycle rule, the single transition endpoint,
      404-not-403 for technician visibility.

## Risks and open questions

1. **One open record per vehicle (rule 3)** is an invented constraint. Without
   it "the current cycle" is ambiguous and spec 06 cannot compute due-ness.
   Cost: a fleet that services a vehicle twice concurrently cannot be modelled.
   Worth stating in `decisions.md`.
2. **404 rather than 403 for a technician reading another's record (rule 18)**
   trades a slightly confusing error for not leaking which ids exist. State it,
   because a reviewer may otherwise read it as a bug.
3. **The transition endpoint takes fields only some transitions use.**
   `scheduled_date` and `completion_odometer` are optional and validated per
   target status. The alternative, three endpoints, spreads the transition
   table across three handlers.
4. **Technicians may complete a service**, which also writes the vehicle
   odometer. That is the job, but it means a technician can move a vehicle's
   odometer without the bulk-upload permission. The monotonic rule still
   applies, so the worst case is a reading that is too high.
