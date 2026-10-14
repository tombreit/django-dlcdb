<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Follow-ups before the merge

**Status:** implemented (batches 1–2, 2026-10-14). Branch `LoginRequiredMiddleware`, before it merges into `main`.
Follow-up of `PLANS/protected-media.md` and its merge review. This is a living document.

## Why

The merge review of `PLANS/login-required.md` and `PLANS/protected-media.md` left three
follow-ups. The user wants them settled on this branch, before the merge:

1. **Tenant scoping per media file.** Media access checks permissions, not tenants. A user with
   `core.view_record` can fetch an attachment of another tenant's record if they know its path;
   the same holds for device QR codes and import CSVs.
2. **Report spreadsheets over HTTP.** They are mailed as attachments and linked only from the
   report admin. Do they need to be served at all?
3. **Inventory note views.** `get_note_btn`, `update_note_view` and `delete_note_view`
   (`inventory/views.py`) load objects without tenant scoping. An unknown `obj_type`, uuid or pk
   gives a 500, and `delete_note_view` deletes any note by pk, including device notes from outside
   the inventory.

Which media directories belong to tenant-owned objects (checked 2026-10-14):

| Directory | Owner | Tenant |
|---|---|---|
| `qrcode/` | `core.Device` (also the `licenses.LicenseAsset` proxy), `core.Room` | the device's; rooms are organisation-wide |
| `attachments/` | `core.Record.attachments` (M2M; attachments are created in the admin only) | the record's device |
| `imported_csv/` | `dataexchange.ImporterList.file` | the import's |
| `person_images/` | `core.Person` | none: persons are organisation-wide |
| `toremove_csv/`, `sap_csv/`, `sap_list_comparison_results/`, `reporting/`, `rooms_reconcile/`, `branding/`, `links/` | — | none |

## Decisions taken

1. **Files of tenant-owned objects follow their tenant.**
   - A file that a tenant-owned object references is served only when the user sees one of the
     owners' tenants. Otherwise it is a 404, like the owner's own pages
     (`tenant_scoped_queryset` plus `get_object_or_404`).
   - A file no tenant-owned object references needs only the permission: a room's QR code, or an
     attachment on no record yet.
   - An owner without a tenant counts as owned. Its file is refused, as `tenant_scoped_queryset`
     never includes objects without a tenant.
   - There is no exception for superusers or for admin-only users (`core.view_attachment`). To see
     every tenant, a group is attached to every tenant.
2. **Declarative, next to `MEDIA_PERMISSIONS`.** A second table in `core/views/media_views.py`
   names each directory's owners as `(model label, file lookup, tenant lookup)`. The models are
   resolved with `apps.get_model()`, so core imports no other app. The view reads `request.tenants`
   from the middleware, so it needs no import of `tenants.shortcuts` either. It counts owners
   through `_base_manager`, so a soft-deleted device's QR code does not become tenant-less.
3. **Report spreadsheets stay served** (`reporting.view_report`). The admin is the documented
   place for generated reports (`berechtigungen.md`, *Django-Admin*), and downloading one there,
   for example after a lost mail, stays possible. No code change.
4. **Inventory note views stay tenant-unscoped, by design.**
   - The QR scanner fetches scanned devices through the REST API, which is deliberately unscoped,
     and records other tenants' devices found in the room. Notes on those devices belong to the
     same workflow: "inventory writes by uuid" in `PLANS/flexible-tenants.md`.
   - The views are hardened instead:
     - an unknown `obj_type` or uuid gives a 404. An unknown pk on delete keeps its existing
       "No note found" message, which never raised;
     - the views work on the active inventory only: without one they answer 404, and
       `delete_note_view` deletes only notes of the active inventory, the same ones
       `update_note_view` edits (`get_latest_note` filters on `inventory__is_active`).
   - The documented unscoped list names the notes explicitly.

## Alternatives considered and rejected

- **Per-app registry for media owners** (`register_media_directory` in `AppConfig.ready()`).
  Rejected again: three entries, strings only, one table to read.
- **Scoping the note views by the inventory's `device_search_tenant_aware` switch.** Notes on
  scanned devices of other tenants would fail while the switch is on. The scan itself (through the
  API) and `inventorize_uuids_for_room` stay unscoped.
- **Stop serving report spreadsheets.** The report admin would lose its download link.

## Pitfalls

- **Multi-valued join:** the attachment check goes through `Record.attachments`. The tenant
  condition must sit in the same `filter()` call as `attachments__file` (AGENTS.md).
- **`Device.qrcode` has no index.** The QR check scans the device table once per QR image. That
  is fine at today's size; an index would be a migration.
- **Tenant refusals are 404s, permission refusals 403s.** The permission check runs first: a user
  without the permission learns nothing about the tenant.

## Batches

### 1. Inventory note views: 404 instead of 500, active inventory only

- `inventory/views.py`, all three note views:
  - an unknown `obj_type` gives `Http404`;
  - lookups use `get_object_or_404`, with the same querysets as today;
  - without an active inventory they answer 404;
  - `delete_note_view` filters `Note` by `pk` and `inventory__is_active=True`. A note of another
    inventory, or one without inventory, gets the existing "No note found" message.
- `docs/guides/berechtigungen.md` (*Nicht auf die eigenen Mandanten eingeschränkt sind*) and
  `PLANS/flexible-tenants.md` (*Deliberately unscoped*): name the inventory notes next to the
  scan writes.
- Tests in `inventory/tests/test_note_views.py`:
  - unknown `obj_type` or uuid gives 404;
  - no active inventory gives 404;
  - deleting a note of another inventory or a non-inventory note leaves it in place;
  - deleting a note of the active inventory still works.

### 2. Media files of tenant-owned objects follow their tenant

- `core/views/media_views.py`:
  - `MEDIA_TENANT_OWNERS`:
    - `qrcode`: `("core.Device", "qrcode", "tenant")`;
    - `attachments`: `("core.Record", "attachments__file", "device__tenant")`;
    - `imported_csv`: `("dataexchange.ImporterList", "file", "tenant")`.
  - `_media_path` raises `Http404` after the permission check when the file is owned but no owner
    is in `request.tenants`.
- Tests in `core/tests/test_media_views.py`:
  - device QR: own tenant served, other tenant 404, device without tenant 404;
  - room QR served;
  - attachment on a record of the own tenant served, of another tenant 404, on no record served;
  - import CSV of another tenant 404;
  - every owner lookup resolves (a query per entry).
- `docs/guides/berechtigungen.md` (*Mandanten*): files of devices, records and imports follow the
  tenant of their object.
- NEWS: one line.

## Progress

- [x] **0. This document**
- [x] **1. Inventory note views: 404 instead of 500, active inventory only**
- [x] **2. Media files of tenant-owned objects follow their tenant**
