<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Admin to frontend: what only the Django admin still offers

**Status:** tracking list, started 2026-11-19 after the settings pages moved to the frontend; since 2026-11-20 also the plan for the settings hub. This is a living document.

## Why

The Django admin is being phased out (AGENTS.md): new UI goes into the frontend apps. This list keeps track of what users can still reach only through the admin, so it can move module by module.

## How to use this list

- **When a module gets a frontend page:** tick its box, note the commit, point its entry in the settings hub at the frontend page (the *Admin* badge goes), and remove its *(Admin)* marker in `docs/guides/berechtigungen.md` ("Navigation" table and "Django-Admin" section).
- **A larger move gets a plan of its own** in `PLANS/`, like `settings-pages`, which was retired into `DECISIONS.md`. Its last batch ticks the box here.
- **Whether the admin stays registered after a move** is decided per module. The settings admins stayed, like the tenant admin.
- **When every box is ticked,** retire this file into `DECISIONS.md` and delete it.

## The settings hub

One page, `/settings/`, lists every setting and every admin-only module in groups, with a filter box. The gear opens it. Each entry opens its own page, as today.

Decided (2026-11-20):

- **A hub, not one page with every field** (as in VS Code or Odoo): the settings are singleton forms, record lists, logs and actions; one page would need one Save button across models. GitHub, Stripe, Linear, Slack and Snipe-IT work the same way.
- **Locality stays.** Each app adds its entries in its own `navigation.py` (slot `nav_settings`), with three new optional keys: `group`, `description` and `search_terms`. `theme` holds the ordered list of groups; an unknown group raises `ImproperlyConfigured`. Not a central settings app (`dlcdb/settings` is the Django settings package anyway).
- **`search_terms` is a hidden field:** one translatable string per entry, never shown. The filter matches it along with the label and description, so "logo" finds Organization.
- **The gear is a link to the hub**, not a dropdown. "Settings" on the settings pages links back to the hub.
- **An `admin:` entry also needs the Staff flag** and carries an "Admin" badge. Moving a module to the frontend switches its entry's `url`.
- **Unchanged:** personal preferences (theme, language, subscriptions) stay in the account menu, and master data keeps its own menu.

Groups, *(A)* marking an admin link:

- **Organization:** Organization (branding, units, positions)
- **Users and access:** Users *(A)*, Groups and permissions *(A)*, Tenants (they grant no permissions, but decide through `Tenant.groups` who sees which devices)
- **Modules:** Lending configuration, Lending regulations (`core.Link`) *(A)*, Licenses configuration, Smallstuff catalogue *(A)*, Notification messages and reports *(A)*
- **Integrations:** HR API sync
- **Data and tools:** Bulk import, Bulk decommissioning *(A)*, Inventories *(A)*, SAP comparison *(A, during an inventory)*, Room reconcile *(A)*
- **Logs:** Journal
- At the bottom, for staff: Django admin

Found while planning:

- **The frontend navbar never renders the Processes menu.** `nav_items_processes` is used only in `templates/admin/navbar.html`. Bulk decommissioning and SAP comparison have no frontend menu entry; Bulk import has only the device list's button. Batch 4 moves them into the hub.
- **Admin menu entries are shown to users without the Staff flag.** Batch 3 adds the staff check, which also hides the three admin links in Master data from those users.

Progress:

- [ ] 1. **The hub page** from the six existing settings entries: `group` and `description`, the view in `theme`, route `/settings/`; the gear links to the hub, and "Settings" on the settings pages links back. Docs (`berechtigungen.md`), NEWS.
- [ ] 2. **Filter box and `search_terms`:** a page-local script that hides groups left empty.
- [ ] 3. **Admin entries:** the staff check for `admin:` URLs in `nav()`; the *(A)* entries, each from the app that owns it.
- [ ] 4. **Data and tools:** the processes and Inventories move into the hub, the `nav_processes` slot is retired, and the admin navbar links the hub.

Open, to decide during the batches: field-level search (by introspecting the settings forms), only if search terms fall short; whether the account menu's "Django admin" entry moves into the hub.

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

- [x] **Organisational units:** on Settings › Organization, with the new positions (`person-fields`, step 9, 2026-11-20). Their admin stays registered.
- [x] **Settings › Branding, Lending configuration (with the lending profiles), Licenses configuration, HR API sync configuration:** `settings-pages`, steps 1 to 9, 2026-11-19. Their admins stay registered.
- [x] **Settings › Tenants and Settings › Journal:** earlier.
- [x] **Master data, rooms, persons, devices, lending, licences, bulk import:** earlier.
