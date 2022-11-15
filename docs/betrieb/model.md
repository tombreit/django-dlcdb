# Model

This chapter descibes the basic data model of the application. The following figures gives
an overview of the data model (outdated):

```{image} /_static/model.131016.png
```

Regenerate this graphic:

```bash
./manage.py graph_models --pygraphviz --group-models --all-applications \
    --exclude-models Session,AbstractBaseSession,LogEntry,ContentType, Permission, \
                     AbstractUser,Site,Attachment,RoomInventoryManagerAbstract, \
                     SoftDeleteAuditBaseModel,RemoverList, \
                     RoomReconcile,ImporterList,AuditBaseModel,Supplier,SapList, \
                     SapListComparisonResult,Note \
    --output /tmp/modelgraph.png
```

## Approach

The data model focuses on flexibility instead of hard database constraints.
Consider `Device` and `Record`. Both models represent the conjunction of
all available device and record sub types. Instead of using multitable inherintance
we using proxy inheritance, where each sub type is represented by one concrete proxy model.

## Device

The device is the central model of the dlcdb.
It represents a device from notebook to beamer.

## Record

The record represents the localization state of a given device where a device may
have multiple subsequent records over time.

Concrete records a represented by proxies. Thus the Record model provides the union of all
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

## Inventory

The Inventory model represents one inventory.
It is used to relate records or notes to an inventory.
The Inventory model provides an is_active flag. There is only one active inventory.
Whenever the inventory process is started all records and notes created during this
inventory process, are related to the current inventory.

The inventory model's purpose is to query all records that have been created during one inventory,
which is espacially useful for the sap list comparision.

## Person

Represents a person. Used by the LentRecord in order to relate the record to the person
that lents the related device.
Person data is enriched with UDB contract data.

## Room

Rooms could be compared against a CSV file (e.g. from Archibus).

## Tenant

A tenant is kind of an organizational unit using the DLCDB, only able to
manage his/her assets.

## SoftDelete

Some models are implemented as *soft delete models*: when deleting instances
of this kind of model the instance will only be marked as deleted and did not
show up in default querysets any more.
