<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Admin to frontend: what only the Django admin still offers

**Status:** tracking list, started 2026-11-19 after the settings pages moved to the frontend. This is a living document.

## Why

The Django admin is being phased out (AGENTS.md): new UI goes into the frontend apps. This list keeps track of what users can still reach only through the admin, so it can move module by module.

## How to use this list

- **When a module gets a frontend page:** tick its box, note the commit, and remove its *(Admin)* marker in `docs/guides/berechtigungen.md` ("Navigation" table and "Django-Admin" section).
- **A larger move gets a plan of its own** in `PLANS/`, like `settings-pages`, which was retired into `DECISIONS.md`. Its last batch ticks the box here.
- **Whether the admin stays registered after a move** is decided per module. The settings admins stayed, like the tenant admin.
- **When every box is ticked,** retire this file into `DECISIONS.md` and delete it.

## Menu entries that open the admin

- [ ] **Removed records:** Datenhaltung › Entfernt-Records, `admin:core_removedrecord_changelist`, `core.view_record`.
- [ ] **Inventories:** start and end an inventory. Datenhaltung › Inventuren, `admin:core_inventory_changelist`, `core.change_inventory`. Inventorizing itself runs in the frontend.
- [ ] **Notes:** Datenhaltung › Notizen, `admin:core_note_changelist`, `core.view_note`. The inventory screens add, edit and delete the notes of a room or device during an inventory.
- [ ] **Bulk decommissioning:** Prozesse › Bulk Ausmusterung, `admin:dataexchange_removerlist_changelist`, `dataexchange.view_removerlist`. Bulk import is in the frontend.
- [ ] **SAP comparison:** the upload. Prozesse › SAP-Abgleich, `admin:inventory_saplist_changelist`, `core.change_inventory`. The comparison result page is in the frontend (`inventory:compare-sap-list`).

## Admin only, without a menu entry

- [ ] **Users and groups:** create them, give permissions, deactivate, hard-delete (`accounts.CustomUser`, `auth.Group`). Needs the Staff flag.
- [ ] **Links (`core.Link`):** the regulation documents of the lending profiles. The profile form selects them but has no add button.
- [ ] **Smallstuff catalogue (`smallstuff.Thing`):** the frontend only assigns things to persons.
- [ ] **Organisational units (`core.OrganizationalUnit`):** filled by the HR sync.
- [ ] **Record attachments (`core.Attachment`).**
- [ ] **Notification messages and reports (`notifications.Message`, `notifications.Report`):** status, preview, "Send now". Subscriptions have a frontend page.
- [ ] **Room reconcile:** the upload of an Archibus CSV (`core.RoomReconcile`). The rooms list links the admin; the result page is in the frontend (`rooms:reconcile`).
- [ ] **HR sync runs:** the full list of up to 50 (`dataexchange.UdbSyncRun`). The HR sync settings page shows the latest 5 with their notes.
- [ ] **Records:** edit or delete a record (`core.Record` and its proxies). The frontend lists records read-only (`assets:record_index`) and changes states through the lifecycle.
- [ ] **Imports:** delete an import (`dataexchange.ImporterList`). Importing runs in the frontend.
- [ ] **Tenants without devices:** the action "assign a tenant" for devices and imports without one (DECISIONS: the NOT NULL follow-up would make it unnecessary).
- [ ] **Histories:** the admin history (`LogEntry`) and the tenant field history (DECISIONS: "field history for tenants").

## Superuser only, in the admin

- [ ] **Master data:** hard-delete it, and activate or deactivate it (soft delete).
- [x] **Devices:** the device admin's action "restore from REMOVED to LOST" is gone (2026-11-19). The frontend's *Restore* does the same move, one device at a time, with its transition permission.

## Frontend pages that still link into the admin

This list is also in `DECISIONS.md › Open follow-ups › Links`.

- [ ] `inventory/inventorize_room_detail.html`: the device link opens the device admin (staff only). The room scan page holds unsaved input, and DECISIONS keeps links plain where leaving drops it: decide between plain text and a new tab.
- [ ] `rooms/index.html`: "Room reconcile" (see above).
- [ ] `theme/context_processors.py`: the hint "assign a tenant" (see above).
- [x] `inventory/partials/device_search_htmx.html`: the device opens its frontend page (with `core.view_device`, back to the search), no longer the admin for every inventory user (2026-11-19).
- [x] `notifications/index.html`: a subscribed device's Edit opens its frontend page (2026-11-19).
- [x] `inventory/room_qrcodes_detail.html`: the room's QR printout lists its devices plain (2026-11-19).
- [x] `theme/device_state.py`: nothing to do. The frontend surfaces (device page, inventory search) link frontend pages; only the admin's own device list links the record admin.
- [x] `licenses/form_partial.html`: the licence page's staff-only "Admin view" became "View asset", the frontend device page (with `core.view_device`) (2026-11-19).

Kept on purpose while the admins exist: the staff-only "Admin view" button on the lending page (`obj_admin_url`), and the navbar's "Django admin" entry.

## Done

- [x] **Settings › Branding, Lending configuration (with the lending profiles), Licenses configuration, HR API sync configuration:** `settings-pages`, steps 1 to 9, 2026-11-19. Their admins stay registered.
- [x] **Settings › Tenants and Settings › Journal:** earlier.
- [x] **Master data, rooms, persons, devices, lending, licences, bulk import:** earlier.
