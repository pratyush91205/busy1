# Schema

PostgreSQL 17, as of migration `0002_domain_schema`. All tables use `BIGINT`
identity primary keys and `TIMESTAMPTZ` timestamps. Every foreign key is
`ON DELETE RESTRICT` — nothing here is hard deleted.

## Tables

**users** — `email` (unique), `full_name`, `password_hash`, `role`
(varchar(20), check in `fleet_manager`/`technician`), timestamps.

**vehicles** — `registration_number` (unique), `make`, `model`,
`current_odometer` (int, check >= 0), `service_date_interval` (int days, check
> 0), `service_mileage_interval` (int miles, check > 0), `is_archived` (bool,
indexed), timestamps.

**service_records** — `vehicle_id` (fk, indexed), `cycle_number` (int, unique
with vehicle_id), `description` (text, check not blank), `status` (varchar(20),
check in `due`/`booked`/`in_service`/`completed`), `scheduled_date` (date,
null until booked), `due_since` (timestamptz), `completed_at`,
`completion_odometer` (int, check null or >= 0), timestamps. Indexed on
`vehicle_id`, `status`, `scheduled_date`, `updated_at`, `due_since`.

One row is one service cycle. `cycle_number` counts from 1 per vehicle.

**service_technicians** — composite pk `(service_id, technician_id)`,
`assigned_at`. Extra index on `technician_id` only; `service_id` is already the
leading column of the pk index.

**service_notes** — `service_id` (fk, indexed), `author_id` (fk), `content`
(check not blank), `created_at`. No `updated_at`; notes are append-only.

**audit_events** — `service_id` (fk), `actor_id` (fk, nullable = the system
acted), `event_type` (varchar(32), check against five values), `old_value`,
`new_value`, `event_metadata` (jsonb), `created_at`. Composite index on
`(service_id, created_at)`.

**overdue_alert_dismissals** — `service_id` (fk, unique), `dismissed_by` (fk),
`dismissed_at`.

## Relationships

One-to-many: vehicles to service_records; service_records to service_notes and
to audit_events; users to notes (author), audit events (actor) and dismissals.

Many-to-many: service_records to users, through `service_technicians`.

One-to-at-most-one: service_records to overdue_alert_dismissals, held by the
unique constraint on `service_id`.

## Where the constraint line falls

In the database: anything that corrupts the model if violated. Uniqueness,
value ranges, the closed set of enum values, referential integrity, and audit
immutability.

In the service layer: anything needing context about the request. The odometer
rule needs the existing row to compare against and has to produce a per-row CSV
rejection, not an exception. Lifecycle transitions are rules about *change*, and
a check constraint only sees one row as it is now. Authorization needs to know
who is asking.

One rule I pushed into the database on purpose: `audit_events` has `BEFORE
UPDATE` and `BEFORE DELETE` triggers that raise. "Not editable, including by
fleet managers" is too important to rest on the absence of an endpoint. Triggers
don't fire on `TRUNCATE`, which is how the tests clean up.

Statuses are varchar + check rather than a native enum, so adding a value is a
one-line migration instead of `ALTER TYPE`.

## Denormalisation

None. Two things I chose not to add:

- **No odometer history table.** `current_odometer` is the latest reading, and
  the odometer for cycle maths is the completion odometer on the service record.
  Cost: a wrong-but-higher reading can't be traced to the CSV row that caused it.
- **No stored overdue alerts.** Overdue is computed. Stored rows would need
  something to create them, and then the row and the computation can disagree.

`due_since` isn't denormalised — it's not derivable. It records when a cycle
became due, so editing a vehicle's intervals can't move a clock already running.

## What breaks first at 100x

1. Text search over `description`, which is an `ILIKE` scan. Fix is a GIN index
   on a tsvector, or `pg_trgm` for substrings.
2. The overdue query, using two single-column indexes. A composite
   `(status, due_since)` would serve it; adding one now would be guesswork.
3. Dashboard aggregates. Stays cheap much longer; the answer then is a summary
   table updated on completion, not a cache.
4. `audit_events` size — the only table that grows forever, by design.
   Partition by month eventually.
