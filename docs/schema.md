# Schema

PostgreSQL 17, as of migration `0002`. BIGINT identity primary keys,
TIMESTAMPTZ timestamps, every foreign key `ON DELETE RESTRICT`.

## Tables

**users** — email (unique), full_name, password_hash, role varchar(20) (check:
fleet_manager, technician).

**vehicles** — registration_number (unique), make, model, current_odometer int
(>= 0), service_baseline_odometer int (>= 0), service_baseline_date date,
service_date_interval int days (> 0), service_mileage_interval int miles
(> 0), is_archived bool (indexed). The two baseline columns are where the
current cycle counts from; both reset on completion.

**service_records** — vehicle_id fk, cycle_number int (unique with vehicle_id),
description text (not blank), status varchar(20) (check: due, booked,
in_service, completed), scheduled_date date, due_since timestamptz, completed_at
timestamptz, completion_odometer int. Indexed on vehicle_id, status,
scheduled_date, updated_at, due_since, and (status, due_since) for the
overdue query. One row is one service cycle.

**service_technicians** — composite pk (service_id, technician_id), assigned_at.

**service_notes** — service_id fk, author_id fk, content text (not blank),
created_at. Append-only, so no updated_at.

**audit_events** — service_id fk, actor_id fk nullable (null = the system
acted), event_type varchar(32) (check: five values), old_value, new_value,
event_metadata jsonb, created_at. Index on (service_id, created_at).

**overdue_alert_dismissals** — service_id fk (unique), dismissed_by fk,
dismissed_at.

## Relationships

One-to-many: vehicles → service_records; service_records → notes, audit_events;
users → notes, audit_events, dismissals.

Many-to-many: service_records ↔ users, through service_technicians.

One-to-at-most-one: service_records → dismissal, via the unique service_id.

## Constraints: database or application

Database: uniqueness, value ranges, the enum value sets, referential integrity,
audit immutability. Anything that corrupts the model if violated.

Application: the odometer rule (needs the existing row, and must report per-row
CSV rejections rather than throw), lifecycle transitions (a check constraint
can't see what a row used to be), authorization (the database doesn't know who
is asking).

The one I pushed down deliberately: `audit_events` has BEFORE UPDATE and BEFORE
DELETE triggers that raise. "Not editable, including by fleet managers" is too
important to rest on the absence of an endpoint.

## Denormalised

Nothing. Two deliberate omissions:

- No odometer history table. `current_odometer` is the latest reading; cycle
  maths uses the completion odometer on the service record. Cost: a
  wrong-but-higher reading can't be traced to its CSV row.
- No stored overdue alerts. Overdue is computed, so nothing can disagree with
  it. Only dismissals are stored.

`due_since` is not denormalised — it records when a cycle became due, which
can't be recomputed once a vehicle's intervals are edited.

The two baseline columns are the one thing close to a denormalisation. The
date half could be read off the newest completed record; the mileage half
genuinely can't be derived, since `current_odometer` moves. Storing both
keeps them symmetric and makes due-ness a single-table predicate instead of
a lateral join per row. Cost: they have to be reset correctly on
completion, and a bad reset is invisible until a vehicle is due at the
wrong time.

## First to break at 100x

1. `ILIKE` search over description. Needs a GIN index on a tsvector.
2. ~~The overdue query, on two single-column indexes.~~ Done in `0003`.
3. Dashboard aggregates — later, and the answer is a summary table, not a cache.
4. `audit_events` size. Grows forever by design; partition by month.
