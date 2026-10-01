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

## Device

The device is the central model of the dlcdb.
It represents a device from notebook to beamer.
A device holds a `OneToOne` pointer (`active_record`) to its current
record; all state is stored in the append-only record chain (see
[Konzept](../konzept.md)). Field-level changes to the device master data
are additionally versioned via django-simple-history.

## Record

The record represents the localization state of a given device where a device may
have multiple subsequent records over time. Records are append-only:
saving a new record deactivates the previous one (setting its
`effective_until` timestamp) and becomes the device's `active_record`.
Allowed state changes are defined and enforced by the finite state machine in
`dlcdb/core/lifecycle.py`: it owns the states, the transition table and the
transition functions that write records, and `Record.save()` rejects an illegal
transition on insert (importers and repair commands opt out with
`save(check_transition=False)`).

Concrete records are represented by proxies. Thus the Record model provides the union of all
fields over all types. Potential constraints or validations are implemented either in the
proxies' model validation methods or in the form layer.

The data model provides the following proxies:

- **OrderedRecord**

  A device does not exist yet, but it has been ordered.

- **InRoomRecord**

  Whenever a device is located somewhere it must provide an InRoomRecord.

- **LentRecord**

  A device is lent.

- **RemovedRecord**

  A device has been removed (aka "deinventarisiert").

- **LostRecord**

  A device could not be found.

- **LicenceRecord**

  Represents a software licence or contract (for devices flagged
  `is_licence`), managed via the licenses frontend.

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

A room a device can be located in. Two rooms carry a special flag: the
*external* room (devices without a physical location, e.g. lent to a home
office) and the *auto return* room (target of every returned lending).

## Tenant

A tenant is an organizational unit using the DLCDB, only able to manage its own
assets. `Device` is the only tenant-aware model (`Device.tenant`); records,
lendings and licences are scoped through their device. A tenant owns a set of
`auth.Group`s, and a user's tenants are derived from the groups they belong to:
several tenants mean their union. Users only see devices of their tenants and
may move a device between them. Superusers are no exception: they see only the
tenants of their groups. Devices without tenant are listed nowhere, only by the
Tenant admin action that assigns them. Tenants grant no permissions. A tenant
that still has devices cannot be deleted (`on_delete=PROTECT`); `Device.tenant`
is nullable for legacy devices only, new devices always get one. See
[Berechtigungen › Tenants](../guides/berechtigungen.md#tenants).

## SoftDelete

Some models are implemented as *soft delete models*: when deleting instances
of this kind of model the instance will only be marked as deleted and does not
show up in default querysets any more. This allows you to "hide" and then
"unhide" assets — the function is labeled "Activate/Deactivate". Deactivated
assets are no longer available for future assignments, but remain in place
for existing assignments. This function is only available in the Django admin
and only to superusers.
