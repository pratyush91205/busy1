# Spec 04 - Vehicle Management

## Overview

The fleet itself: creating vehicles, editing them, configuring their service
intervals, recording odometer readings, and archiving and restoring them. This
is goal 2 (vehicle CRUD with archive/restore and intervals) and CLAUDE.md
Phase 5.

It also builds the paged-list machinery - search, filter, sort, page - once,
against vehicles, so that Phase 12 applies it to services rather than inventing
it a second time.

## Depends on

Spec 02 for the `vehicles` table, which is already migrated and needs no
change. Spec 03 for `require_role("fleet_manager")`, which guards every
mutation here.

## Current state

The model, its three CHECK constraints and the `is_archived` index exist.
Nothing reads or writes them: there is no vehicle schema, repository, service,
route or page.

## Data model

No migration. `vehicles` is used as-is.

One thing the table does not enforce and the service layer must: the unique
index on `registration_number` is case-sensitive, so `van001` and `VAN001`
would both be storable. Registrations are normalised to trimmed uppercase
before every write and every lookup, which makes the existing index
sufficient and keeps the stored value the one a depot would recognise.

## Business rules

1. Only a fleet manager may create, edit, archive or restore a vehicle. A
   technician gets **403**. A technician may still *read* the fleet - they need
   to know which vehicle a job is on.
2. `registration_number` is unique after normalisation. A duplicate is **409**,
   naming the registration.
3. `current_odometer` never decreases. An update carrying a lower reading is
   **409** stating both numbers. Equal is accepted and changes nothing.
4. Odometer, and both intervals, are rejected below their bounds by Pydantic
   before the database sees them: odometer `>= 0`, intervals `> 0`. These
   duplicate the CHECK constraints on purpose - the constraint is the guarantee,
   the schema is the readable **422**.
5. Archiving is a soft delete. `is_archived` becomes true; nothing is deleted,
   and the vehicle's service history stays readable.
6. An archived vehicle rejects every mutation except restore, with **409**.
   Restore it first. This is what later lets a bulk-odometer CSV row for an
   archived vehicle be rejected with a reason rather than silently applied.
7. Archiving an already-archived vehicle, or restoring a live one, is **409**.
   A no-op that reports success hides a mistake.
8. `GET /vehicles` excludes archived vehicles unless `include_archived=true`.
9. There is no delete endpoint. Archive is the only removal.

## Permissions

**Fleet Manager** - everything below.

**Technician** - `GET /vehicles` and `GET /vehicles/{id}` only. Every mutation
is 403.

## API

`GET /vehicles` query parameters: `search` (matches registration, make or
model), `include_archived` (default false), `sort`
(`registration_number` | `current_odometer` | `created_at` | `updated_at`,
default `registration_number`), `order` (`asc` | `desc`), `page` (default 1),
`limit` (default 20, max 100).

| method | route | authorization | request | response | errors |
|---|---|---|---|---|---|
| GET | `/vehicles` | any authenticated | query params above | `{items, total, page, limit, total_pages}` | 401, 422 bad params |
| GET | `/vehicles/{id}` | any authenticated | none | vehicle | 401, 404 |
| POST | `/vehicles` | fleet_manager | registration, make, model, odometer, both intervals | vehicle, 201 | 401, 403, 409 duplicate, 422 |
| PATCH | `/vehicles/{id}` | fleet_manager | any subset of the above | vehicle | 401, 403, 404, 409 duplicate/lower odometer/archived, 422 |
| POST | `/vehicles/{id}/archive` | fleet_manager | none | vehicle | 401, 403, 404, 409 already archived |
| POST | `/vehicles/{id}/restore` | fleet_manager | none | vehicle | 401, 403, 404, 409 not archived |

New files: `app/schemas/pagination.py` (a generic `Page[T]` and the shared
query params), `app/schemas/vehicle.py`, `app/repositories/vehicle.py`,
`app/services/vehicle_service.py`, `app/api/routes/vehicles.py`.

Filtering, sorting and pagination are SQL - `ILIKE`, `ORDER BY`, `LIMIT`,
`OFFSET`, and one `COUNT(*)` for the total. Nothing is filtered in Python.

## Audit events

None. `audit_events.service_id` is `NOT NULL`, so the table cannot hold a
vehicle-scoped event. Vehicle changes are logged, not audited.

This is a real gap and belongs in `docs/architecture.md` under what was
deliberately not built: who archived a vehicle, or edited an interval, is not
recoverable. Auditing it properly means making `service_id` nullable and adding
an entity column, which is a migration and a schema change for a goal the brief
does not ask for.

## Frontend

* `app/(app)/vehicles/page.tsx` - table: registration, make and model, odometer,
  intervals, status badge. Search box, an archived toggle, sortable headers,
  pagination controls. All of it drives query parameters, so the URL is the
  state and a filtered view can be linked.
* `app/(app)/vehicles/[id]/page.tsx` - the vehicle, its intervals and its
  current maintenance state. Service history arrives in spec 05; until then the
  section says so rather than rendering an empty table.
* `components/vehicles/vehicle-form.tsx` - React Hook Form and Zod, used by
  both create and edit. The Zod schema mirrors the Pydantic one; it is UX, and
  the server's 409s still surface as form errors.
* `components/vehicles/archive-button.tsx` - confirmation dialog, because
  archiving removes a vehicle from every default view.
* Manager-only actions are not rendered for a technician. That is tidiness, not
  authorization - the endpoints refuse them regardless.

## Tests

`apps/api/tests/test_vehicles.py`.

1. A manager creates a vehicle; a technician creating one gets 403. (rule 1)
2. A technician can list and read vehicles. (rule 1)
3. A duplicate registration is 409, including when it differs only in case or
   whitespace. (rule 2)
4. Registration is stored normalised.
5. Raising the odometer succeeds; lowering it is 409 and leaves the stored
   value untouched; an equal reading is accepted. (rule 3)
6. A negative odometer and a zero interval are 422, not 500. (rule 4)
7. Archiving sets the flag and deletes nothing; the vehicle is still readable
   by id. (rule 5)
8. Editing an archived vehicle is 409; restoring it then editing succeeds.
   (rule 6)
9. Double archive and restoring a live vehicle are both 409. (rule 7)
10. The default list excludes archived vehicles and `include_archived=true`
    includes them. (rule 8)
11. Search matches registration, make and model, and is case-insensitive.
12. Sorting by odometer ascending and descending returns the documented order.
13. Pagination: page 2 of limit 2 over 5 vehicles returns the right slice and
    `total`, `total_pages` are right; a page past the end is an empty list, not
    a 404.
14. No route deletes a vehicle. (rule 9)

## Definition of done

- [ ] All six endpoints behave as tabled, verified with curl against the local
      database.
- [ ] A technician's token is refused every mutation and allowed both reads.
- [ ] Lowering an odometer is refused and the stored reading is unchanged.
- [ ] Archive hides from the default list, keeps the row, and keeps the vehicle
      readable by id.
- [ ] The list query is one SELECT plus one COUNT; no filtering in Python.
- [ ] Vehicles page works against the local API: search, sort, page, archive
      toggle, create, edit, archive, restore.
- [ ] Tests pass with no skips.
- [ ] Several commits: pagination primitives, repository and service, routes,
      tests, list page, form, detail page.
- [ ] `docs/` updated: the no-vehicle-audit gap in `architecture.md`, the
      normalisation and archive-blocks-edits decisions in `decisions.md`.

## Risks and open questions

1. **Editing an archived vehicle is refused (rule 6), which the brief does not
   require.** Chosen because it gives the bulk-odometer CSV a clear per-row
   answer later, and because an archived vehicle is not part of the operating
   fleet. Cost: restoring to correct a typo is two calls.
2. **No vehicle audit trail**, per the Audit events section. Named in the docs
   rather than left for a reviewer to notice.
3. **`ILIKE '%term%'` will not use an index.** Fine at fleet scale - hundreds of
   vehicles, not millions - and already listed in `schema.md` as the first thing
   to break at 100x. Not worth a tsvector column now.
