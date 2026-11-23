<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Viewset alignment: one component for a model's list, add, edit and delete pages

**Status:** batch 3 done (lending profiles); next: batch 4, the wrap-up. Started 2026-11-23.

## Why

`theme.viewsets.ModelViewSet` serves the smallstuff catalogue, units and positions (DECISIONS.md). An audit on 2026-11-23 found the same flow still written by hand elsewhere:

- **Device types, manufacturers, distributors** (suppliers) run on a parallel copy: `assets/views/masterdata.py` (`MasterdataSpec`, 269 lines) with six templates. The viewset lacks what they use:
  - extra index filters (`has_note`)
  - a search placeholder
  - cell markup (the type's icon, the note marker, the count badge, a truncated contact)
  - an edit page without the audit card (Manufacturer and Supplier have no audit fields)
  - the "Usage: N devices" card
  - no delete page
- **Lending profiles** (`lending/views_profiles.py`) map one to one, but need a history page.
- **Tenants, rooms and persons** hand-write the same flow with more of their own (see Open follow-ups).
- **Duplicated template skeletons:**
  - `tenants/delete.html` ≈ `lending/profile_delete.html` ≈ `accounts/groups/delete.html`
  - `tenants/history.html` ≈ `lending/profile_history.html`
  - the add pages of rooms, persons, tenants and lending profiles
  - the index list partial in rooms, persons, users, journal, imports, licences, lending, devices and records, forced while cells can't be rendered generically
  - hand-written read-only blocks in rooms, tenants and persons

## Decisions

- **This round moves the device master data, then the lending profiles.** Tenants, rooms, persons and the read-only lists are follow-ups.
- **Master data keep having no delete page**: the docs and group profiles leave deleting and deactivating them to superusers in the admin. The viewset can leave a page out (`delete_view_class = None`).
- **The edit page's usage card is generic** (`Usage`: label, count annotation, list URL, filter parameter, view permission): a count linked to the filtered list. It replaces the units' template and the master data's card.
- **Cells get markup through `Column.cell_template_name`** (Wagtail's name), with shared cells in `theme` (a count badge, a name with the note marker). Every list's counts look alike.
- **Wagtail's names where Wagtail has one:** `filterset_class`, `Column.cell_template_name`, `HistoryView` / `history_view_class`.
- **The add page takes initial values from GET, as the admin does**, form fields only: the lending page's "Add one?" preselects the device type without extra code.
- **Lending profiles get their own Settings list**, like units; the card on Settings › Lending configuration goes.

## Pitfalls

- DeviceType is soft-deleted: its `delete()` sets `deleted_at` and never asks the `Collector`, so the generic delete page would deactivate a type devices still use.
- `protected_objects` isn't tenant-aware: a delete page for a model that devices use would list other tenants' devices.
- The dashboard links the device types with `?ordering=-assets`: the count annotation keeps the name `assets`.

## Open follow-ups

- **Tenants:** the group × tenant matrix as a custom index; the generic history page; the generic delete page lists the devices and imports that keep a tenant.
- **Rooms:**
  - their own filterset;
  - cell templates;
  - the changes card as an edit-view subclass;
  - no delete page.
- **Persons:**
  - as rooms;
  - a queryset that depends on the request (lendings of the user's tenants);
  - read-only per object (HR sync);
  - the `+` buttons;
  - photo cleanup on save.
- **Read-only lists** (journal, import history, reporting): a viewset without add, edit and delete, with an inspect page and a request-scoped queryset.
- **Not CRUD, stay as they are:** groups, users, licences, notifications, the lending list, devices, records, inventory.

## Progress

- [x] **0.** This plan.
- [x] **1. Viewset features**, adopted by the existing viewsets:
  - `filterset_class`;
  - `search_placeholder`;
  - `Column.cell_template_name` with the shared count cell; the note cell comes with its first user in batch 2;
  - the audit card only for audit models;
  - `Usage`, replacing `organization/name_edit.html`;
  - a left-out page; `filterset_class`, the placeholder and the left-out page are tested through their first user in batch 2.
- [x] **2. Device types, manufacturers, suppliers** on `ModelViewSet`:
  - `MasterdataSpec`, its six templates and two filters go;
  - URL names `assets:device_type:edit` etc.;
  - no delete page;
  - DeviceType's verbose names in sentence case (migration);
  - the device type list's "created" sort is gone (no column).
- [x] **3. Lending profiles** on `ModelViewSet`:
  - a generic `HistoryView`;
  - initial values from GET;
  - `form_fields_template`;
  - their own Settings entry;
  - `LendingProfile.__str__` names the device type;
  - no permission is listed under *Other* on the group pages any more: lending profiles were the last without a menu entry.
- [ ] **4. Wrap-up:** this plan retires into DECISIONS.md.
