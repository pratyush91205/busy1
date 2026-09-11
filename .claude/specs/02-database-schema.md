# Spec 02 - Database Schema and Migrations

## Overview

Create the whole domain schema in one migration: users, vehicles, service
records, the technician assignment join table, notes, audit events and overdue
alert dismissals. This is Phase 3 of the CLAUDE.md Development Order. It
satisfies no goal on its own and every goal depends on it. `due_since` and the
service cycle identifier are created now, not retrofitted, because both are
load-bearing for overdue correctness (goals 4 and 10) and neither can be added
later without rewriting history that was never recorded.

## Depends on

Spec 01 (walking skeleton). Alembic, `Base`, the session factory and the test
harness all exist and work; this spec adds revision `0002` on top of `0001`.

Deployment is deliberately deferred at the user's instruction. Nothing here
depends on it, and the schema is what the eventual deploy will migrate.

## Current state

Not started.

* Present: `deployment_check` (revision `0001`), its model, repository, schema,
  route, frontend card and four tests.
* Missing: every domain table, and the enums they constrain.

## Data model

Conventions for every table below: `BIGINT` identity primary key named `id`;
`created_at TIMESTAMPTZ NOT NULL DEFAULT now()`; `updated_at TIMESTAMPTZ NOT
NULL DEFAULT now()` maintained by SQLAlchemy `onupdate` on tables that change.
Append-only tables (`service_notes`, `audit_events`) have `created_at` only.
**Every foreign key is `ON DELETE RESTRICT`**: nothing in this system is hard
deleted, vehicles are archived, and audit history must outlive everything.

Enums are stored as `VARCHAR` with a `CHECK` constraint, not as native
PostgreSQL enum types, so that adding a value later is a one-line migration
rather than an `ALTER TYPE` dance. Stored values are snake_case; display labels
belong to the UI.

### users

| column | type | constraints |
|---|---|---|
| email | text | not null, **unique** |
| full_name | text | not null |
| password_hash | text | not null |
| role | varchar(20) | not null, check in (`fleet_manager`, `technician`) |

### vehicles

| column | type | constraints |
|---|---|---|
| registration_number | text | not null, **unique** |
| make | text | not null |
| model | text | not null |
| current_odometer | integer | not null, check `>= 0` |
| service_date_interval | integer | not null, check `> 0` (unit: days) |
| service_mileage_interval | integer | not null, check `> 0` (unit: miles) |
| is_archived | boolean | not null, default false |

Column names follow the CLAUDE.md Vehicle Management list. The units are not in
the names; they are recorded as PostgreSQL column comments so the meaning lives
with the schema.

### service_records

| column | type | constraints |
|---|---|---|
| vehicle_id | bigint | not null, fk -> vehicles.id |
| cycle_number | integer | not null, check `> 0`, **unique (vehicle_id, cycle_number)** |
| description | text | not null, check length > 0 |
| status | varchar(20) | not null, check in (`due`, `booked`, `in_service`, `completed`) |
| scheduled_date | date | nullable - set when the record is booked |
| due_since | timestamptz | nullable - when this cycle first became Due |
| completed_at | timestamptz | nullable |
| completion_odometer | integer | nullable, check null or `>= 0` |

`cycle_number` **is** the service cycle identifier: one service record is one
service cycle for its vehicle, numbered from 1. This is the "or equivalent
mechanism" CLAUDE.md allows, and it is what makes alert dismissal
cycle-scoped for free - a new cycle is a new row, so it cannot inherit an old
dismissal.

`due_since` is persisted rather than recomputed so that editing a vehicle's
intervals cannot silently move an existing overdue clock. Overdue remains
derived (`status = due` AND `due_since + grace <= now()`); there is no fifth
status value.

### service_technicians

| column | type | constraints |
|---|---|---|
| service_id | bigint | not null, fk -> service_records.id |
| technician_id | bigint | not null, fk -> users.id |
| assigned_at | timestamptz | not null, default now() |

Composite primary key `(service_id, technician_id)`, which makes a duplicate
assignment a database error rather than a service-layer check.

### service_notes

| column | type | constraints |
|---|---|---|
| service_id | bigint | not null, fk -> service_records.id |
| author_id | bigint | not null, fk -> users.id |
| content | text | not null, check length > 0 |

### audit_events

| column | type | constraints |
|---|---|---|
| service_id | bigint | not null, fk -> service_records.id |
| actor_id | bigint | nullable, fk -> users.id (null = system, e.g. a record becoming Due) |
| event_type | varchar(32) | not null, check in (`service_created`, `status_changed`, `technician_assigned`, `technician_unassigned`, `note_added`) |
| old_value | text | nullable |
| new_value | text | nullable |
| event_metadata | jsonb | nullable |

Immutability is enforced **in the database**, not only by omitting endpoints: a
row-level trigger raises an exception on `UPDATE` or `DELETE` of any
`audit_events` row. This holds for a Fleet Manager, for the ORM, and for anyone
with a psql prompt. Row triggers do not fire on `TRUNCATE`, which is how tests
clean up.

### overdue_alert_dismissals

| column | type | constraints |
|---|---|---|
| service_id | bigint | not null, **unique**, fk -> service_records.id |
| dismissed_by | bigint | not null, fk -> users.id |
| dismissed_at | timestamptz | not null, default now() |

There is no table of alert rows. An overdue alert is derived from the service
record plus the grace period, and this table records only the dismissal. That
satisfies "the current state should be derivable from persisted data and the
current time" without a background job creating rows, and makes reappearance in
a new cycle automatic. See Risks.

### Indexes

Unique indexes come from the constraints above (`users.email`,
`vehicles.registration_number`, `service_records(vehicle_id, cycle_number)`,
`overdue_alert_dismissals.service_id`). Non-unique, per the CLAUDE.md Database
Standards list plus the two the overdue query needs:

`vehicles.is_archived`, `service_records.vehicle_id`, `service_records.status`,
`service_records.scheduled_date`, `service_records.updated_at`,
`service_records.due_since`, `service_technicians.technician_id`,
`service_technicians.service_id`, `service_notes.service_id`,
`audit_events.service_id`.

### Migration `0002_domain_schema`

Creates all seven tables, constraints, indexes, column comments and the audit
trigger, and **drops `deployment_check`**. `downgrade()` reverses all of it,
including recreating `deployment_check` with its seed row so that `0001` remains
truthful.

Removed with the table, because they cannot work without it:
`app/models/deployment_check.py`, `app/schemas/deployment_check.py`,
`app/repositories/deployment_check.py`, `app/api/routes/deployment_check.py`,
`tests/test_deployment_check.py`, `apps/web/components/deployment-check-card.tsx`,
`apps/web/types/deployment-check.ts`.

`GET /health` stays: it needs no table, it is Render's health check, and it
keeps the frontend's smoke test alive.

## Business rules

Schema-level only. No service layer or endpoint is added by this spec, so these
are enforced by PostgreSQL and surfaced as `IntegrityError` until the phases
that own them translate them into HTTP responses.

1. Two vehicles cannot share a `registration_number`; the second insert is
   rejected by the unique constraint.
2. `current_odometer` below 0 is rejected by a check constraint. The
   "never decreases" rule is service-layer and belongs to Phase 5.
3. A `role` outside (`fleet_manager`, `technician`) is rejected.
4. A `status` outside the four stored values is rejected. `overdue` is not one
   of them and must not become one.
5. Both service interval columns must be `> 0`; a zero or negative interval
   would make a vehicle permanently due.
6. A service record whose `vehicle_id` does not exist is rejected.
7. The same technician cannot be assigned twice to one service record.
8. Two service records cannot share a `cycle_number` for one vehicle.
9. `UPDATE` or `DELETE` on `audit_events` raises, whoever attempts it.
10. Deleting a vehicle or user that is still referenced is rejected; archiving
    is the supported operation.

## Permissions

None. This spec adds no endpoint. `users.role` and `password_hash` are created
here; authentication and authorization arrive in Phase 4 (spec 03), and no
route may read a role until then.

## API

No new endpoints. One removed: `GET /api/deployment-check`, superseded as spec
01 anticipated. `GET /health` is unchanged.

## Audit events

The `audit_events` table and its immutability trigger are created here. No event
is emitted yet - there is no mutation to describe. From Phase 6 onward every
mutation writes its event in the same transaction, per CLAUDE.md.

## Frontend

`apps/web/app/page.tsx` loses the deployment check card and shows a minimal API
status card reading `GET /health` instead, keeping the loading, error and empty
states already built. The component is renamed to
`components/api-status-card.tsx` with `types/health.ts`. No new pages; the real
UI starts with login in Phase 4.

## Tests

`apps/api/tests/test_schema.py`, plus an updated `test_migrations.py`. All run
against the local PostgreSQL 17 instance via `TEST_DATABASE_URL`.

1. `alembic upgrade head` applies to an empty database and `downgrade base`
   reverses it, with the chain now two revisions long. (migration)
2. After upgrade, every table, column and index listed above exists, and
   `deployment_check` does not. (data model)
3. Duplicate `registration_number` raises `IntegrityError`. (rule 1)
4. `current_odometer = -1` raises. (rule 2)
5. `role = 'admin'` raises. (rule 3)
6. `status = 'overdue'` raises - the regression guard against adding a fifth
   lifecycle state. (rule 4)
7. `service_date_interval = 0` raises. (rule 5)
8. A service record with a non-existent `vehicle_id` raises. (rule 6)
9. Inserting the same `(service_id, technician_id)` twice raises. (rule 7)
10. Two records with the same `(vehicle_id, cycle_number)` raises. (rule 8)
11. `UPDATE audit_events SET new_value = ...` raises, and
    `DELETE FROM audit_events` raises. (rule 9)
12. Deleting a vehicle that has a service record raises. (rule 10)

## Definition of done

- [ ] Local PostgreSQL 17 is running and `apps/api/.env` points `DATABASE_URL`
      and `TEST_DATABASE_URL` at two separate local databases.
- [ ] `alembic upgrade head` and `alembic downgrade base` both succeed against a
      real database, twice in a row.
- [ ] All seven tables exist with the constraints, indexes and column comments
      above; `\d service_records` shows `due_since` and `cycle_number`.
- [ ] The audit trigger blocks `UPDATE` and `DELETE` from a raw psql session,
      not just through the ORM.
- [ ] `status` has no `overdue` value anywhere in the schema.
- [ ] `deployment_check` and all seven files listed above are gone; `pytest`
      passes with no skips.
- [ ] `apps/web` builds and the API status card renders against `/health`.
- [ ] Several commits, roughly: models, migration, audit trigger, schema tests,
      remove the walking skeleton table, frontend status card.
- [ ] `docs/schema.md` draft handed to the user (protected file).

## Risks and open questions

1. **`overdue_alert_dismissals` instead of an `OverdueAlert` table.** CLAUDE.md
   lists `OverdueAlert` as a domain entity. Storing only dismissals is the
   "equivalent mechanism" it permits, and it avoids a job that materialises
   alert rows and a second source of truth for overdue state. If the user wants
   a literal alert table, this is the moment to say so - changing it after
   Phase 11 means a migration and a rewrite of the alerts query.
2. **Who creates the next cycle's service record.** The schema supports either
   answer. Completing a service could immediately create the next record
   (`status = due` once an interval is reached), or the due calculation could
   create it lazily on read. This is a Phase 8/9 decision; it needs settling
   before spec 04, not now.
3. **`updated_at` is maintained by SQLAlchemy, not a trigger.** Any future raw
   `UPDATE` that bypasses the ORM would leave it stale, and "sort by last
   updated" is a required feature. Acceptable while all writes go through the
   service layer; revisit if a bulk path ever writes SQL directly.
4. **Demo seed data is not in this spec.** It lands in Phase 16, and it needs
   users with real password hashes, which do not exist until Phase 4.
