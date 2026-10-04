# Model

This chapter describes the basic data model of the application. The
following diagram gives an overview of the core models and their
relations (hand-maintained; source of truth: `dlcdb/core/models/`):

```{eval-rst}
.. mermaid::

   erDiagram
      DEVICE ||--o{ RECORD : "collects"
      DEVICE ||--o| RECORD : "active_record"
      DEVICE }o--o| DEVICE_TYPE : "device_type"
      DEVICE }o--o| MANUFACTURER : "manufacturer"
      DEVICE }o--o| SUPPLIER : "supplier"
      DEVICE }o--o| TENANT : "tenant"
      RECORD }o--o| ROOM : "room"
      RECORD }o--o| PERSON : "person (lent)"
      RECORD }o--o| INVENTORY : "inventory"
      NOTE }o--o| DEVICE : ""
      NOTE }o--o| ROOM : ""
      NOTE }o--o| INVENTORY : ""
```

## Approach

The data model focuses on flexibility instead of hard database constraints.
Consider `Device` and `Record`. Both models represent the conjunction of
all available device and record sub types. Instead of using multitable inheritance
we use proxy inheritance, where each sub type is represented by one concrete proxy model.

For what devices, records and states mean to users, see
[Konzept](../konzept.md); this page covers how they are stored.

## Device

The central model, from notebook to beamer. A device holds a `OneToOne`
pointer (`active_record`) to its current record; its state lives only in the
record chain. Field-level changes to the master data are versioned via
django-simple-history.

## Record

Records are append-only: saving a new record closes the previous one (sets its
`effective_until` timestamp) and becomes the device's `active_record`.
Allowed state changes are defined and enforced by the finite state machine in
`dlcdb/core/lifecycle.py`: it owns the states, the transition table and the
transition functions that write records, and `Record.save()` rejects an illegal
transition on insert (importers and repair commands opt out with
`save(check_transition=False)`). `record_type` holds stable keys (`INROOM`,
`LENT`, …), enforced by a `CheckConstraint`; only their labels are translated.

Concrete records are represented by proxies, so the Record model provides the
union of all fields over all types. Constraints and validations live in the
proxies' model validation or in the form layer.

| Proxy | `record_type` |
|---|---|
| `OrderedRecord` | `ORDERED` |
| `InRoomRecord` | `INROOM` |
| `LentRecord` | `LENT` |
| `LostRecord` | `LOST` |
| `RemovedRecord` | `REMOVED` |
| `LicenceRecord` | none of its own: the active, not removed records of devices flagged `is_licence`, see [Lizenzen](../guides/lizenzen.md) |

## Inventory

The Inventory model represents one inventory.
It is used to relate records or notes to an inventory.
The Inventory model provides an is_active flag. There is only one active inventory.
Whenever the inventory process is started all records and notes created during this
inventory process, are related to the current inventory.

The inventory model's purpose is to query all records that have been created during one inventory,
which is especially useful for the sap list comparison.

## Person

Represents a person. Used by the LentRecord in order to relate the record to the person
that lents the related device.
Person data is enriched with contract data from the HR system.

## Room

A room a device can be located in. Two rooms carry a special flag
(`is_external`, `is_auto_return_room`), see
[Räume anlegen](../guides/erste_schritte.md#6-räume-anlegen).

## Tenant

Shown as *Mandant* in the UI; for who sees what, see
[Berechtigungen › Mandanten](../guides/berechtigungen.md#mandanten).
`Device` and `ImporterList` (imports) carry a tenant; records, lendings and
licences are scoped through their device. A tenant has a set of `auth.Group`s,
and a user's tenants are the union over their groups. Both foreign keys use
`on_delete=PROTECT` and are nullable for legacy rows only; new devices and
imports always get a tenant.

## SoftDelete

Some models are implemented as *soft delete models*: when deleting instances
of this kind of model the instance will only be marked as deleted and does not
show up in default querysets any more. This allows you to "hide" and then
"unhide" assets — the function is labeled "Activate/Deactivate". Deactivated
assets are no longer available for future assignments, but remain in place
for existing assignments. Only superusers can use it, in the Django admin.
