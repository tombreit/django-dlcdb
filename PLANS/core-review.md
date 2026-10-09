<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Core review: dlcdb/core as the contract

**Status:** planned (2026-10-09). Review only; no batch implemented. This is a living
document: findings, decisions and progress are kept here.

## Why

`dlcdb/core` is meant to hold the central business logic: models, states, transitions, the
"contract" every other app consumes. Today a reader who opens `core/` finds 8 000 lines of
Python, of which the contract is a small part:

| Part of core | Lines | Consumed by other apps? |
|---|---|---|
| `lifecycle.py` | 523 | yes (6 apps) |
| `models/` | 2 322 | yes (Device, Record, Person, Room in 8–10 apps) |
| `admin/` | 2 495 | no — nobody imports it; it is a second UI |
| `management/` | 1 276 | no — tools |
| `utils/` | 616 | partly (`get_denormalized_user`, htmx decorators) |
| `context_processors.py`, `navigation.py` | 382 | no — presentation |
| `forms/`, `views/`, `templatetags/` | 367 | no |

And core is not a leaf. It imports Python from eight of the apps meant to consume it:
`tenants`, `dataexchange`, `inventory`, `journal`, `lending`, `organization`, `theme`,
`assets` (full list under *Findings*). Several rules exist in more than one place
("overdue" has five definitions, three of them disagree). The goal: a reader gets the
concepts from core alone; a refactoring in a consumer app relies on a contract that is
written once.

The admin stays untouched in function; the frontend apps stay the UI. Code is moved or
deleted, not added.

## The contract (target)

What `dlcdb/core` is, in one screen. This goes into `dlcdb/core/__init__.py` as the module
docstring (batch 1), and `AGENTS.md` points at it.

1. **Models.** `Device`, `Record` and its five state proxies, `LicenceRecord` (a view on
   records, not a state), `Room`, `Person`, `OrganizationalUnit`, `DeviceType`,
   `Manufacturer`, `Supplier`, `Inventory`, `Note`, `Link`, `Attachment`; the abstract
   bases `AuditBaseModel`, `SoftDeleteAuditBaseModel`, `SingletonBaseModel`,
   `TenantAwareModel`. `RoomReconcile` stays for migration reasons only (its logic is in
   `rooms`).
2. **Lifecycle.** `core/lifecycle.py` owns states, the transition table, and the only
   sanctioned ways to append a record (`transition_*`, `localise`). Record writes that
   bypass it (`save(check_transition=False)`) are allowed only in the importer and in
   repair commands, and are listed in the lifecycle docstring.
3. **Shared rules live once, in core, on the model's manager or in lifecycle:** what is
   "overdue", what is "lent", what is "expiring soon", what makes a device a licence, what
   may be relocated. Consumers call them; they do not re-spell them.
4. **Shared helpers:** `get_denormalized_user` (through `AuditBaseModel.save(user=…)`),
   `get_contact_email`, `rollback_atomic`, the two htmx decorators, `relocate_device`,
   `search_devices`, QR code generation.
5. **Dependency rule.** `core/models`, `core/lifecycle.py` and `core/utils` import no
   Python from a consumer app. Allowed references to consumers: foreign keys by string
   (`"tenants.Tenant"`, `"dataexchange.ImporterList"`) and URL names in
   `get_absolute_url` and `obj_link`. Everything that branches on *which app is
   rendering* (CSS classes, per-app action URLs, nav, hints) is presentation and lives in
   `theme` or the rendering app.
6. **Admin.** The admin stays in core, all of it (decided 2026-10-09). It is the
   operators' second UI over the core models, and like any UI it may import admin helpers
   from consumer apps (`tenants.admin`, `dataexchange.admin.ExportCsvMixin`,
   `theme.widgets`, `journal`, `lending.LendingConfiguration`). The dependency rule 5
   therefore stops at `core/admin`. What the admin may not do is hold a rule of its own:
   the lend/return dispatch it shares with `lending/views.py` becomes one core function
   (batch 6).
7. **Plumbing that is not domain but has no better home** stays and is labelled as such
   in the docstring: `middleware.py` (WhiteNoise for docs), `storage.py`, `tasks.py`
   (SQLite snapshot), `formats/`, `management/commands/dlcdb_init.py`,
   `anonymize_data`, the `audit_*`/`fix_*` repair commands.

## Findings

### Core imports from consumer apps (Python)

| Core file | Imports | Fix (batch) |
|---|---|---|
| `models/device.py:19`, `models/room.py:15` | `inventory.utils.uuid2qrcode` | move to `core/utils/qrcode.py` (2) |
| `models/inventory.py:13` | `inventory.utils.update_inventory_note` | becomes `Note.objects.append_inventory_note()` in core (2) |
| `models/device.py:20`, `forms/adminactions_forms.py`, `views/relocate_views.py`, `admin/*` | `tenants.abstracts`, `tenants.shortcuts`, `tenants.admin` | `TenantAwareModel` moves into `core/models/abstracts.py`, `tenants/abstracts.py` is deleted; scoping helpers stay in `tenants` and are called only from views/admins, never from models (5) |
| `models/prx_licencerecord.py:49` | `apps.get_model("notifications.Subscription")` | the subscriber-email subquery moves to `licenses` (its only reader) (4) |
| `context_processors.py:21,80,185` | `dataexchange.ImporterList`, `assets.filters.STATE_NO_RECORD`, `organization.Branding` | `hints` and `nav` move to `theme/context_processors.py` (3) |
| `utils/helpers.py:57` | `organization.Branding` | `get_contact_email` keeps the lazy import; Branding is a singleton the contact rule needs. Accepted exception, documented (1) |
| `admin/lentrecord_admin.py:25-27` | `lending.LendingConfiguration`, `dataexchange.admin.ExportCsvMixin` | accepted: admin is UI (rule 6) |
| `admin/base_admin.py`, `admin/licencerecord_admin.py` | `journal.JournalEntry` | accepted: admin is UI (rule 6) |
| `admin/devicetype_admin.py:7` | `theme.widgets.IconPickerWidget` | accepted: admin is UI (rule 6) |
| `management/commands/mark_not_handled_assets_in_csv.py` | `inventory.sap` | move to `inventory/management/commands/` (3) |
| `management/commands/populate_devicetype_icons.py` | `theme.bootstrap_icons` | move to `assets/management/commands/` (3) |

### Presentation sitting in core

- `core/context_processors.py` (346 lines): `hints` (sticky setup messages with frontend
  URLs, ~6 queries) and `nav` (assembles every app's `navigation.py`). `theme` already owns
  `navigation.py` helpers and a context processor. Move both; `django_settings` stays
  wherever its single reader is.
- `core/utils/device_methods.py` (167): CSS classes, labels and per-app action URLs
  (`inventory:`, `assets:`, `lending:`, admin). Consumed only through
  `Device.get_state_data()` by the core DeviceAdmin, `assets/views/devices.py:184` and
  `inventory/views.py:230`. Moves to `theme/device_state.py` next to
  `theme/lifecycle_display.py`; `Device.get_state_data` is removed and the three callers
  call the function. `core/templates/core/device/state_btn_group.html` moves with it.
- `core/navigation.py`: three admin-changelist entries (Removed records, Inventories,
  Notes). Keep; it is the per-app convention.
- `core/templatetags/markdown_extras.py` and
  `core/templates/core/lentrecord/includes/interleaf.html`: used only by lending's print
  templates. Move to `lending`.
- `Room.get_inventory_status` returns CSS classes (`room.py:124-164`); `Device.get_timeline`
  holds colours (`device.py:330-403`). Return data, let the template pick the class
  (later; not blocking).
- `settings.THEME` (icons per model, `COLOR` never read) is read by one function
  (`get_icon_for_class`) for the dashboard. Move the dict into `dashboard`, delete the setting.

### Rules spelled more than once

| Rule | Copies | One place |
|---|---|---|
| State keys | `lifecycle.py:54-58`, `Record.INROOM…` (`record.py:65-69`), `notifications/models.py:45-49`, `dataexchange/reporting.py:26` | `Record.X = lifecycle.X` (keep the `Record.X` spelling, 110 uses); the other two import |
| Overdue | `lending/views.py:68`, `lending/filters.py:95`, `dashboard/views.py:161`, `core/admin/filters/lentstate_filter.py:25`, `core/admin/lentrecord_admin.py:143` (no end-date check), `notifications/reports.py:55-71` (+5 days, OR instead of AND) | `LentRecord.objects.overdue(as_of=None, tolerance_days=0)` in `prx_lentrecord.py`; the report keeps its tolerance as an argument |
| Lend / return / edit dispatch | `lending/views.py:_apply_state_machine`, `core/admin/lentrecord_admin.py:save_model` (+ the soft warnings twice) | `apply_lending(record, edited, *, user)` next to `LentRecord` in `prx_lentrecord.py` (it needs only lifecycle and the record); the soft warnings become `lending_warnings(person, desired_end)` beside it; view and admin call both |
| "Lost device cannot be lent" | `core/forms/lentrecordadmin_form.py:27`, `lending/forms.py:76`, `lending/views.py:346` | the transition table already forbids LOST → LENT (`lend.sources == (INROOM,)`) and `IllegalTransition` is a `ValidationError`; delete the three checks, keep the message |
| Licence "expires soon" (30 days) | `licenses/subscribers.py:55-67`, `notifications/tasks.py:167` | one queryset method on `LicenceRecord.objects` |
| What is a licence | `is_licence` flag (core admin filter) vs name prefixes `Lizenz::/License::/Licence::` in `licenses/forms.py:39`, `licenses/filters.py:27` | `is_licence`; the prefix list becomes one constant in `licenses` if still needed for device-type choices |
| "Any of these permissions" | `core/utils/htmx.py:51`, `theme/pickers.py:46`, `dashboard/search.py:72`, `core/context_processors.py:242` | one `has_any_perm(user, perms)` in `core/utils/helpers.py` |
| Audit stamp `obj.user, obj.username = get_denormalized_user(request.user)` | ~17 call sites | `AuditBaseModel.save(self, *args, user=None, **kwargs)` stamps when given; call sites become `obj.save(user=request.user)` |
| Tenant scoping by hand `tenant__in=request.tenants` | `core/models/inventory.py:80,89,128,137`, `core/context_processors.py:65`, `lending/filters.py:38`, `dashboard/stats.py:74,115,156`, `dataexchange/remover.py:67`; own map in `dashboard/views.py:32` | `tenants.shortcuts.tenant_scoped_queryset` everywhere; model querysets take `tenants` as an argument instead of a request |
| Person live-search, room search, device text search, has-note filter | 3–5 copies each (see `PLANS/filterbar.md` batch 2 for has-note) | one queryset method per model in core |

### Inventory workflow in a core model

`Inventory.inventorize_uuids_for_room` (`core/models/inventory.py:270-359`) is the
inventory-scan workflow (found → `localise`, not found → `relocate_lending` or
`transition_lose`, unknown → strip stamps). It is called from one place,
`inventory/views.py:146`. The *rules* it applies are lifecycle calls; the *workflow* is the
inventory app's. Move it to `inventory/services.py` (plain function taking the inventory,
room, uuids, user). `core/models/inventory.py` keeps the model and the queryset.

### Dead code (delete)

- `core/forms/lentlocalization_form.py` — unused and broken (`Room.type`, `Room.TYPE_CHOICER`
  do not exist).
- `core/views/procure_views.py`, `core/forms/procure_forms.py`,
  `core/templates/core/orderedrecord/procure.html`, URL `core_procure_device` — no inbound
  link; the assets app has `device_order` on `transition_order`. After this, `core/urls.py`
  holds only the admin relocate action target.
- `core/templates/core/room/records_snippet.html`, `core/static/.../add_form.css`.
- `Room.get_active_records`, `Room.get_lent_records`, `Device.get_fqdn_url`,
  `Record.get_proxy_instance`.
- Stale text: `record.py:64` comment (`RECORD_TYPE_CLASSES`), docstrings of
  `core/tests/test_transition_parity.py` and `test_state_write_paths.py` (describe removed
  mechanisms), `lending/forms.py:47` vs `LentRecordAdminForm` still in use.
- Settings: `LOGIN_FIELD` (unread), second `SITE_ID`, `THEME.COLOR`.

### Settings module

`dlcdb/settings/base.py` (597 lines) is in reasonable shape: typed env reads, one `.env`,
`test.py` overriding deterministically. Findings:

- **Project settings nobody reads:** `LOGIN_FIELD`; `DLCDB_BASE_URL` only in
  `docs/conf.py`; `THEME[*].COLOR`. The local `.env` carries `UDB_*` keys nothing reads
  (UDB config is the `UdbSyncConfiguration` singleton) — `env.template` should not offer
  them.
- **Parsed on every use:** `MAX_FUTURE_LENT_DESIRED_END_DATE` is a string parsed with
  `strptime` in `prx_lentrecord.py:63,69` and `udb_sync.py:387`. Parse once in settings
  into a `date`.
- **App wiring in global settings** (keep, but comment each line with the owning app):
  `lending.loader.DatabaseLoader` as first template loader, the `inventory` context
  processor on every request, `tenants` middleware, `journal` logging handlers.
- **Security smell, fix regardless of this review:** `inventory/context_processors.py:26,32`
  puts `Token.objects.first().key` — the first API token of *any* user — into `js_vars` on
  inventory pages. The scanner should use the requesting user's token or a dedicated one.
- **`ldap.py`** star-imports from a partially initialised `base` (circular). Works; make it
  a function `apply_ldap(globals())` or inline the block guarded by `env("AUTH_LDAP")`.
- **Business thresholds hard-coded in code**, not settings: 5-day overdue tolerance,
  93-day licence warning, 30-day expires-soon, 48-hour rescan, `UDB_SYNC_FILTERS`, licence
  name prefixes, `pc`/`ntb` report prefixes, the Archibus building code. Decision: they
  stay in code as named constants next to their one definition (not in settings); the
  deployment-specific ones (`UDB_SYNC_FILTERS`, report prefixes, building code) are
  candidates for the respective admin-managed singleton, later.
- `reporting/settings.py` is an app module named "settings" (`EXPOSED_FIELDS`); rename to
  `reporting/fields.py` to stop the confusion.

### What stays in core although it looks domain-specific

- `LentRecord`, `LicenceRecord`, lending fields on `Record`, `Inventory`, `Note`, `Person`
  HR mirror fields: they are the data model, consumed by several apps, and moving a model
  between apps costs migrations for nothing.
- `LentRecord.objects` returns every active, non-removed record of lendable devices,
  INROOM included (`prx_lentrecord.py:17-30`); `lending` relies on that. Rename is not
  worth the churn; the docstring says so.
- `relocate_device` and the admin relocate view: shared by assets and the admin action.
- `core/tests/test_transition_parity.py` and `test_state_write_paths.py` drive other apps'
  views on purpose: they prove every write path goes through the lifecycle. They are
  contract tests and stay in core. `test_form_round_trip.py` (edit pages of five apps) and
  `test_native_date_widgets.py` (all ModelForms) are project-wide sweeps; they stay too.

## Decisions taken

1. **No model moves.** Everything above is Python moves, deletions and one-place rules.
2. **Core imports no Python from consumer apps** (rule 5). The one accepted exception is
   the lazy `Branding` import in `get_contact_email`, documented at the import.
3. **`Record.X` stays the public spelling of state keys**, defined as aliases of
   `lifecycle.X`.
4. **The `check_transition=False` call sites are listed in the lifecycle docstring.** A new
   one is a review item.
5. **Thresholds stay in code**, one named constant each; not in settings.
6. **The admin stays in core** (asked 2026-10-09). Moving `LentRecordAdmin`,
   `LicenceRecordAdmin`, `RoomAdmin`, `PersonAdmin`, `DeviceAdmin` and the others to the
   apps that own the frontend was considered (admin URL names would survive, since they
   derive from the model's app label) and rejected: the admin is one UI over the core
   models and reads better in one place.

## Open questions

- `rename_lifecycle_permissions` (201 lines): a one-off migration helper. Delete once every
  known instance has run it?
- Should lifecycle transitions write a journal entry (one `JournalEntry.objects.log` in
  `Record.save`)? Not now; noted as an idea.

## Batches

Each batch is one commit; `pytest .` green after each. Order is by risk: deletions and
docstrings first, moves second, one-place rules third, the shared lend dispatch last.

### 1 — The map, dead code, stale text
- `dlcdb/core/__init__.py`: the contract as a module docstring (section *The contract*).
  `AGENTS.md`: one line pointing at it.
- Delete the dead code listed above; fix the stale comments and docstrings.
- Settings: drop `LOGIN_FIELD`, the second `SITE_ID`; `env.template` loses the `UDB_*` keys.
- Commit: `Core review, step 1: core/__init__.py states the contract; dead procure view,
  broken LentLocalizationForm and unused model methods removed`

### 2 — Core stops importing inventory
- `core/utils/qrcode.py` gets `uuid2qrcode`; `inventory.utils` imports it from there
  (callers: `inventory/management/commands/generate_qrcodes.py`, the inventory context
  processor).
- `update_inventory_note` becomes `Note.objects.append_inventory_note(inventory, device,
  msg)` in `core/models/note.py`; inventory imports it.
- `Inventory.inventorize_uuids_for_room` → `inventory/services.py:inventorize_room(...)`;
  the four lifecycle calls go with it; `inventory/views.py:146` calls the function.
- Tests: the existing inventory tests cover the workflow; `core/tests` that import the
  method follow it.
- Commit: `Core review, step 2: QR codes and inventory notes are core helpers, the
  inventory scan workflow moves to inventory/services.py`

### 3 — Presentation leaves core
- `hints`, `nav`, `_app_navigation` → `theme/context_processors.py`; settings
  `TEMPLATES[...].context_processors` updated; `core/tests/test_hints.py` and
  `test_context_processor_queries.py` move to `theme/tests`.
- `core/utils/device_methods.py` → `theme/device_state.py`; `state_btn_group.html` →
  `theme/templates/theme/device/`; `Device.get_state_data` removed; callers updated.
- `core/utils/links.py` → with its users (`hints` → theme). `linked_message` stays in core
  if lending still uses it, otherwise moves to lending.
- `markdown_extras` + `interleaf.html` → `lending`.
- `settings.THEME` → `dashboard/icons.py`; `get_icon_for_class` moves with it.
- `mark_not_handled_assets_in_csv` → `inventory`; `populate_devicetype_icons` → `assets`.
- Commit: `Core review, step 3: hints, navigation, device state buttons and the icon map
  move to the apps that render them`

### 4 — One definition each (several small commits)
- 4a state keys: `Record.X = lifecycle.X`; `notifications/models.py` and
  `dataexchange/reporting.py` import them.
- 4b `LentRecord.objects.overdue()`; the six readers call it; one test pins the semantics
  (desired end ≤ today, not returned). The notification report passes its tolerance.
- 4c lost-device checks deleted (lifecycle enforces); test that the lending form shows the
  lifecycle message.
- 4d `LicenceRecord.objects.expiring_soon()`; subscriber-email subquery moves to licenses;
  licence prefixes become one constant.
- 4e `has_any_perm`; `AuditBaseModel.save(user=…)` replaces the 17 stamp sites.
- 4f person/room/device search methods on the model querysets (coordinate with
  `PLANS/filterbar.md` batch 2, which already consolidates the has-note filter).
- Commits: `Core review, step 4x: …` one line each.

### 5 — Tenant scoping has one path
- `TenantAwareModel` into `core/models/abstracts.py`; delete `tenants/abstracts.py`
  (no migration: same field definition, abstract base).
- `tenant_scoped_queryset` replaces every hand-written `tenant__in`; `InventoryQuerySet`
  methods take `tenants` instead of `request`.
- `dashboard/views.py:TENANT_FILTERS` goes away in favour of the helper's `tenant_field`.
- Commit: `Core review, step 5: tenant scoping goes through tenants.shortcuts everywhere;
  TenantAwareModel lives with the other core abstract bases`

### 6 — One lend dispatch for frontend and admin
- `core/models/prx_lentrecord.py`: `apply_lending(record, edited, *, user)` (the
  INROOM → `transition_lend`, LENT + end date → `transition_return_lending`, LENT →
  in-place save dispatch) and `lending_warnings(person, desired_end)` (the two HR contract
  warnings, returned as messages, not sent).
- `lending/views.py:_apply_state_machine` and `_lending_soft_warnings`, and
  `core/admin/lentrecord_admin.py:save_model`, call them. The module-level
  `session = SessionStore()` in `lentrecord_admin.py:36`, shared by all requests, is
  replaced by `request.session`.
- Tests: `core/tests/test_transition_parity.py` already drives both paths; one test that
  the admin and the view produce the same record chain for lend → edit → return.
- Commit: `Core review, step 6: lending frontend and admin share one lend/return/edit
  dispatch and one set of contract warnings`

### 7 — Settings
- `MAX_FUTURE_LENT_DESIRED_END_DATE` parsed once; `ldap.py` without the circular import;
  owning-app comments on the wired lines; `reporting/settings.py` → `fields.py`.
- The inventory token context processor: own batch, own NEWS line, before everything else
  if the user agrees it is a bug.
- Commit: `Core review, step 7: settings parse dates once, LDAP settings apply without the
  circular import`

## Alternatives considered and rejected

| Approach | Why not |
|---|---|
| A `services.py` layer in core for every workflow | Adds a layer; the lifecycle functions already are the service API. Workflows (inventory scan, lending dispatch) belong to the app that owns the screen. |
| Moving `Tenant` into core | Migration churn for a model that only core references by string anyway. |
| Signals on `Record` for journaling/notifications | Project rule (journal plan, decision 8): explicit calls, no signals. |
| Moving the model admins to the frontend apps | Asked and rejected (decision 6): one UI over the core models reads better in one place; the admin may import consumer helpers. |
| Retiring the admin UI for lending/licences | Out of scope; the admin is still the operators' second UI. |
| Putting thresholds into settings | Nobody tunes them per deployment; a named constant next to its one definition is easier to find. |

## Pitfalls

- `tenants/abstracts.py` exists to break an import cycle; moving `TenantAwareModel` into
  core resolves it the other way round (tenants.models imports core, core references
  `"tenants.Tenant"` as a string only). Check `makemigrations --check` stays clean.
- `LentRecord.objects` includes INROOM records. Any new "lent" query must filter
  `record_type=LENT` explicitly (the dashboard stat at `stats.py:76` does not).
- The lifecycle `transition_*` functions check state, not permissions. Permission checks
  stay in views/admins (`lifecycle.available`).
- Moving a template that an admin references by path (`core/device/state_btn_group.html`)
  means renaming it at every `render`/`include` site; grep for the path before the move.

## Progress

- [x] 0 — This document
- [ ] 1 — The map, dead code, stale text
- [ ] 2 — Core stops importing inventory
- [ ] 3 — Presentation leaves core
- [ ] 4 — One definition each (a–f)
- [ ] 5 — Tenant scoping has one path
- [ ] 6 — One lend dispatch for frontend and admin
- [ ] 7 — Settings

## Verification (each batch)

- `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- `.venv/bin/python manage.py makemigrations --check --dry-run` (no model moves, so no new
  migration may appear)
- `.venv/bin/pytest .`
- A grep guard, run by hand after batches 2, 3 and 5:
  `grep -rn "from dlcdb\.\(assets\|inventory\|lending\|licenses\|theme\|journal\|organization\|dataexchange\|tenants\)" dlcdb/core --include=*.py | grep -v "tests\|/admin/"`
  must list only the accepted exception (`Branding` in `get_contact_email`).
- `/verify` after batch 3 and 6: navbar, hints band, device list state buttons, inventory
  room page, admin lend/return round trip.
