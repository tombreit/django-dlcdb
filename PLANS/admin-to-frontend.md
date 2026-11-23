<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Admin to frontend: what only the Django admin still offers

**Status:** tracking list, started 2026-11-19 after the settings pages moved to the frontend. This is a living document.

## Why

The Django admin is being phased out (AGENTS.md): new UI goes into the frontend apps. This list keeps track of what users can still reach only through the admin, so it can move module by module.

## How to use this list

- **When a module gets a frontend page:** tick its box, note the commit, point its entry on the settings page at the frontend page (its *Staff* badge goes), and trim the "Django-Admin" section of `docs/guides/berechtigungen.md`.
- **A larger move gets a plan of its own** in `PLANS/`, like `settings-pages`, which was retired into `DECISIONS.md`. Its last batch ticks the box here.
- **Whether the admin stays registered after a move** is decided per module. The settings admins stayed, like the tenant admin.
- **When every box is ticked,** retire this file into `DECISIONS.md` and delete it.

## Next candidates

Noted 2026-11-20, smallest first; none started yet.

1. **Lending regulations (`core.Link`):** a card on Settings › Lending configuration, like the lending profiles; the profile form could then offer "add". Small, follows an existing pattern, fixes a real gap.
2. **Room reconcile upload:** on the rooms page. The result page is already in the frontend; only the upload and the rooms list's admin link remain.

## Menu entries that open the admin

Shown only with the Staff flag. Each comes from the `navigation.py` of the app named; the settings page marks its entries with a *Staff* badge (DECISIONS: settings page).

- [x] **Removed records:** the entry is gone; *Devices* with the state *Removed* lists the decommissioned devices with their whereabouts, the removal report mail links there (2026-11-22). The admin stays registered.
- [ ] **Notes:** Datenhaltung › Notizen, `admin:core_note_changelist`, `core.view_note` (core). The inventory screens add, edit and delete the notes of a room or device during an inventory.
- [x] **Users and groups:** create them, give permissions, set passwords, deactivate: `accounts:users` and `accounts:groups` (2026-11-20, `PLANS/users-and-groups.md`, retired into DECISIONS.md). The Staff and Superuser flags and hard-deleting a user stay in the admin.
- [ ] **Links (`core.Link`):** the regulation documents of the lending profiles. The profile form selects them but has no add button. Einstellungen › Ausleih-Ordnungen, `admin:core_link_changelist`, `core.view_link` (lending).
- [x] **Smallstuff catalogue (`smallstuff.Thing`):** Einstellungen › Kleinkram-Katalog opens `smallstuff:thing:index`, the first `theme.viewsets.ModelViewSet` (2026-11-23, `PLANS/model-viewset.md`). The admin stays registered.
- [ ] **Notification messages and reports (`notifications.Message`, `reporting.Report`):** status, preview, "Send now". Subscriptions have a frontend page. Einstellungen › Benachrichtigungen and › Reports, `notifications.view_message` (notifications) and `reporting.view_report` (reporting).
- [ ] **Bulk decommissioning:** Einstellungen › Bulk-Ausmusterung, `admin:dataexchange_removerlist_changelist`, `dataexchange.view_removerlist` (dataexchange). Bulk import is in the frontend.
- [ ] **Inventories:** start and end an inventory. Einstellungen › Inventuren, `admin:core_inventory_changelist`, `core.change_inventory` (inventory). Inventorizing itself runs in the frontend.
- [ ] **SAP comparison:** the upload, during an inventory. Einstellungen › SAP-Abgleich, `admin:inventory_saplist_changelist`, `core.change_inventory` (inventory). The comparison result page is in the frontend (`inventory:compare-sap-list`).
- [ ] **Room reconcile:** the upload of an Archibus CSV (`core.RoomReconcile`). Einstellungen › Raumabgleich, `admin:core_roomreconcile_changelist`, `core.view_roomreconcile` (rooms). The rooms list links the admin too; the result page is in the frontend (`rooms:reconcile`).
- [ ] **Records:** edit or delete a record (`core.Record` and its proxies). Einstellungen › Records bearbeiten, `admin:core_record_changelist`, `core.change_record` (core); with only the view permission, Master data › Records (`assets:record_index`) lists them read-only. State changes run through the lifecycle in the frontend.
- [ ] **Record attachments (`core.Attachment`):** Einstellungen › Record-Anhänge, `admin:core_attachment_changelist`, `core.view_attachment` (core).
- [ ] **HR sync runs:** the full list of up to 50 (`dataexchange.UdbSyncRun`). Einstellungen › HR-Sync-Läufe, `admin:dataexchange_udbsyncrun_changelist`, `dataexchange.view_udbsyncrun` (dataexchange). The HR sync settings page shows the latest 5 with their notes.
- [ ] **Admin history (`LogEntry`):** Einstellungen › Admin-Historie, `admin:admin_logentry_changelist`, `admin.view_logentry` (core).

## Admin only, without a menu entry

Reached where they are, and through Settings › More › Django admin.

- [ ] **Imports:** delete an import (`dataexchange.ImporterList`). Importing runs in the frontend. No entry: the admin list is the same as the import history, which Bulk import's page links.
- [ ] **Tenants without devices:** the action "assign a tenant" for devices and imports without one (DECISIONS: the NOT NULL follow-up would make it unnecessary). No entry: an admin action, which the sticky hint links while needed.
- [x] **Tenant field history:** on the tenant's frontend page, *Changes › Field history* (`tenants:history`, `tenants.view_tenant`), group ticks included (2026-11-20).

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

Kept on purpose while the admins exist: the staff-only "Admin view" button on the lending page (`obj_admin_url`), and the "Staff area (Django admin)" entry of Settings › More.

## Done

- [x] **Organisational units:** on Settings › Organization, with the new positions (`person-fields`, step 9, 2026-11-20). Their admin stays registered.
- [x] **Settings › Branding, Lending configuration (with the lending profiles), Licenses configuration, HR API sync configuration:** `settings-pages`, steps 1 to 9, 2026-11-19. Their admins stay registered.
- [x] **Settings › Tenants and Settings › Journal:** earlier.
- [x] **Master data, rooms, persons, devices, lending, licences, bulk import:** earlier.
