<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Core review: dlcdb/core as the contract

**Status:** planned (2026-10-09). Reordered on 2026-10-10 into atomic steps, easiest
first, after checking every finding against the code. Steps 0–14, 16, 17, 20–25,
27–41 and 21b done, 15 skipped, 18 and 19 postponed. All steps are done; what is left
is under *Postponed* and *Open questions*. Step 41 (the dashboard's lent bar, found
while checking the contract for step 36) ran before 36. Steps 37–40 (admin-only model members, added 2026-10-12) ran before phase E.
This is a living document: findings, decisions and progress are kept here.

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

And core is not a leaf. It imports Python from consumer apps (`tenants`, `dataexchange`,
`inventory`, `organization`, `theme`, `assets`, `notifications`; full list under
*Findings*). Several rules are written in more than one place ("overdue" has six
definitions, and three of them disagree). The goal: a reader understands the concepts
from core alone, and a refactoring in a consumer app can rely on a contract that is
written once.

The admin stays untouched in function; the frontend apps stay the UI. Code is moved or
deleted, not added.

## How we work through it

- **One concern per commit.** A commit deletes, moves, or merges one thing. A move never
  also changes behaviour. Where merging copies changes what a user sees, the
  behaviour-preserving part goes first, and the change gets its own commit that says so.
- **Easiest first.** Phase A changes no running code. Phase B holds small standalone fixes.
  Phase C moves code without changing it. Phase D merges duplicated rules. Phase E needs
  design work and comes last.
- After each step: verification (bottom of this document), tick the box, suggest the
  commit message, stop. The user commits before the next step starts.
- Commit messages: `Core review, step N: …`, one self-explanatory line.
- NEWS.md: only the token fix (step 0) needs a line. Everything else is internal.

## The contract (target)

What `dlcdb/core` is, in one screen. This text becomes the module docstring of
`dlcdb/core/__init__.py` once it is true (last step), and `AGENTS.md` points at it.

Written down in step 36 (2026-10-12) as a short docstring with only the rules that
cannot be read off the code (see step 36). The lists below stay here as planning notes;
they are not code documentation.

1. **Models.** `Device`, `Record` and its five state proxies, `LicenceRecord` (a view on
   records, not a state), `Room`, `Person`, `OrganizationalUnit`, `DeviceType`,
   `Manufacturer`, `Supplier`, `Inventory`, `Note`, `Link`, `Attachment`; the abstract
   bases `AuditBaseModel`, `SoftDeleteAuditBaseModel`, `SingletonBaseModel`,
   `TenantAwareModel` (postponed: it still lives in `tenants`, see *Postponed*).
   `RoomReconcile` stays for migration reasons only (its logic is in
   `rooms`).
2. **Lifecycle.** `core/lifecycle.py` owns states, the transition table, and the only
   sanctioned ways to append a record (`transition_*`, `localise`). Record writes that
   bypass it (`save(check_transition=False)`) are allowed only in the importer and in
   repair commands, and are listed in the lifecycle docstring.
3. **Shared rules live once, in core, on the model's manager or in lifecycle:** what is
   "overdue", what is "lent", what makes a device a licence, what may be relocated,
   which persons match a search term.
   Consumers call them; they do not re-spell them.
4. **Shared helpers:** `get_denormalized_user` (through `AuditBaseModel.stamp_user()`),
   `get_contact_email`, `rollback_atomic`, the two htmx decorators, `relocate_device`,
   `obj_link`/`linked_message`, `search_devices`, QR code generation.
5. **Dependency rule.** `core/models`, `core/lifecycle.py` and `core/utils` import no
   Python from a consumer app. Allowed references to consumers: foreign keys by string
   (`"tenants.Tenant"`, `"dataexchange.ImporterList"`) and URL names in
   `get_absolute_url` and `obj_link`. Anything that depends on *which app is rendering*
   (CSS classes, per-app action URLs, nav, hints) is presentation and lives in `theme` or
   the rendering app. Three postponed exceptions (see *Postponed*): `core/models/device.py`
   imports `tenants.abstracts.TenantAwareModel`, `core/utils/device_methods.py` builds the
   device state buttons with per-app action URLs, and `core/models/inventory.py` imports
   `inventory.utils.update_inventory_note` for the scan workflow.
6. **Admin.** The admin stays in core, all of it (decided 2026-10-09). It is the
   operators' second UI over the core models, and like any UI it may import admin helpers
   from consumer apps (`tenants.admin`, `dataexchange.admin.ExportCsvMixin`,
   `theme.widgets`, `journal`, `lending.LendingConfiguration`). The admin action form
   (`core/forms/adminactions_forms.py`) and the relocate action target
   (`core/views/relocate_views.py`) are part of the admin too. Rule 5 therefore does not
   apply to the admin. What the admin may not do is hold a rule of its own: the
   lend/return dispatch it shares with `lending/views.py` is one core method,
   `LentRecord.apply_lending` (step 32). The admin is being phased out (2026-10-12);
   rule 8 keeps the models free of it.
7. **Plumbing that is not domain but has no better home** stays and is labelled as such
   in the docstring: `middleware.py` (WhiteNoise for docs), `storage.py`, `tasks.py`
   (SQLite snapshot), `formats/`, `management/commands/dlcdb_init.py`,
   `anonymize_data`, the `audit_*`/`fix_*` repair commands.
8. **Admin-only code lives in the admin** (2026-10-12). A model method or property that
   only the admin reads is part of the admin: a `ModelAdmin` method, the admin form, or
   the context the admin passes to its templates. The models keep what core itself, a
   frontend app or a command reads, so retiring the admin later means deleting
   `core/admin`, its forms and templates, without touching the models. See *Admin-only
   members on core models* and steps 37–40.

## Findings

Verified against the code on 2026-10-10. Line numbers are as of that date.

### Core imports from consumer apps (Python)

| Core file | Imports | Fix (step) |
|---|---|---|
| `models/device.py:19`, `models/room.py:15` | `inventory.utils.uuid2qrcode` | move to `core/utils/qrcode.py` (14) |
| `models/inventory.py:13` | `inventory.utils.update_inventory_note` | was: goes away with the scan workflow (19); postponed with the inventory refactoring, see *Postponed* |
| `models/device.py:20` | `tenants.abstracts.TenantAwareModel` | was: move into `core/models/abstracts.py` (15); postponed, see *Postponed* |
| `models/prx_licencerecord.py:49` | `apps.get_model("notifications", "Subscription")` | the subscriber-email subquery moves to `licenses`, its only reader (25) |
| `context_processors.py:21,80,185` | `dataexchange.ImporterList`, `assets.filters.STATE_NO_RECORD`, `organization.Branding` | `hints` and `nav` move to `theme/context_processors.py` (20, 21) |
| `management/commands/mark_not_handled_assets_in_csv.py` | `inventory.sap` | move to `inventory/management/commands/` (11) |
| `management/commands/populate_devicetype_icons.py` | `theme.bootstrap_icons` | move to `assets/management/commands/` (12) |
| `utils/helpers.py:57` | `organization.Branding` | `get_contact_email` keeps the lazy import, because the contact rule needs the Branding singleton. Accepted exception, documented at the import |
| `forms/adminactions_forms.py`, `views/relocate_views.py` | `tenants.models`, `tenants.shortcuts` | accepted: admin (rule 6) |
| `admin/lentrecord_admin.py`, `admin/base_admin.py`, `admin/licencerecord_admin.py`, `admin/devicetype_admin.py` | `lending`, `dataexchange.admin`, `journal`, `theme.widgets` | accepted: admin (rule 6) |

### Presentation sitting in core

- `core/context_processors.py` (346 lines): `hints` (sticky setup messages with frontend
  URLs, ~6 queries), `nav` (assembles every app's `navigation.py`) and `django_settings`
  (read by `templates/403.html` and `registration/login.html`). `theme` already owns the
  navigation helpers and a context processor. All three move there, and the file is
  deleted.
- `core/utils/device_methods.py` (167): CSS classes, labels and per-app action URLs
  (`inventory:`, `assets:`, `lending:`, admin). It is consumed only through
  `Device.get_state_data()`, by the core DeviceAdmin, `assets/views/devices.py:182` and
  `inventory/views.py:230`. It moves to `theme/device_state.py`, next to
  `theme/lifecycle_display.py`. `Device.get_state_data` is removed, and the three callers
  call the function directly. `core/templates/core/device/state_btn_group.html` moves
  with it. The template moved in step 17; the function itself is postponed (step 18, see
  *Postponed*).
- `core/navigation.py`: three admin-changelist entries (Removed records, Inventories,
  Notes). Keep; it is the per-app convention.
- `core/templatetags/markdown_extras.py` and
  `core/templates/core/lentrecord/includes/interleaf.html` are used only by lending's print
  templates. Move them to `lending`. The library name `markdown_extras` must stay: lending
  profile templates stored in the database load it (`lending/migrations/0006_…`).
- `settings.THEME` (an icon for each model; `COLOR` is never read) is read only by
  `get_icon_for_class`, which has two callers: the dashboard tiles and the note badge in
  `core/admin/base_admin.py`. Move the dict and the function to `theme`, the presentation
  app that both callers may import. Delete the setting.
- `core/utils/links.py` stays in core: `relocate_device`, the core admin, the relocate
  view and `lending/views.py` use it, and `hints` does not.
- Later, not blocking: `Room.get_inventory_status` returns CSS classes, and
  `Device.get_timeline` holds colours. Both should return data and let the template pick
  the class.

### Rules spelled more than once

| Rule | Copies | One place |
|---|---|---|
| State keys | `lifecycle.py:54-58`, `Record.INROOM…` (`record.py:65-69`), `notifications/models.py:45-49` (report events) | `Record.X = lifecycle.X`. Keep the `Record.X` spelling (235 uses). The notification events reuse `lifecycle.X` as their values. (`dataexchange/reporting.py`'s `Outcome.REMOVED` is an import outcome, not a state key, so it stays.) |
| Overdue | `lending/views.py:68`, `lending/filters.py:105`, `dashboard/views.py:162`, `core/admin/filters/lentstate_filter.py:26`, `core/admin/lentrecord_admin.py:143` (no not-returned check), `notifications/reports.py:55-71` (+5 days tolerance, OR instead of AND) | `LentRecord.objects.overdue(today=None, tolerance_days=0)` in `prx_lentrecord.py`, built on one `Q` so the admin's `Case/When` annotation can share it |
| Lend / return / edit dispatch | `lending/views.py:_apply_state_machine`, `core/admin/lentrecord_admin.py:save_model`, and the soft warnings twice | `LentRecord.apply_lending(user=…)` and `LentRecord.contract_warnings()` in `prx_lentrecord.py`. View and admin call both (done in step 32) |
| "Lost device cannot be lent" | `core/forms/lentrecordadmin_form.py:30`, `lending/forms.py:79`, a guard in `lending/views.py:339` and `print_sheet` | The rule was already in the lifecycle (`lend` starts only from INROOM). `LentRecord.check_lending()` asks it; the admin form, the lending view and `print_sheet` call it (done in step 33) |
| Licence "expires soon" notice (30 days before expiry) | `licenses/subscribers.py:60`, `notifications/tasks.py:167` | Both compute a schedule date, not a queryset, so the rule becomes one named constant in `notifications`. The 93-day warning in the `LicenceRecord` annotation is a different rule and stays |
| Licence device-type prefixes `Lizenz::/License::/Licence::` | `licenses/forms.py:40`, `licenses/filters.py:28` | one constant in `licenses` (device-type choices still need it; the `is_licence` flag is the rule for devices) |
| Audit stamp `obj.user, obj.username = get_denormalized_user(request.user)` | 17 call sites in 8 files | `AuditBaseModel.stamp_user(user)`, so call sites become `obj.stamp_user(request.user)` (a `save(user=…)` keyword was planned first; see step 27) |
| Person live search, room search, device text search | several copies each (has-note is already done: `theme/filters.py`, filterbar step 2) | After the inventory (step 35): only "a person matches by name or email" is one rule, now `Person.search_q`. Room and device searches are per-page choices and stay |

### Tenant scoping

The first draft wanted `tenants.shortcuts.tenant_scoped_queryset` everywhere. In the code
it does not fit the remaining hand-written sites:

- `tenant_scoped_queryset` takes a request. `InventoryQuerySet`, `dashboard/stats.py` and
  `dataexchange/remover.py` already take `tenants`, and core models may not import
  `tenants` anyway (rule 5). `tenant__in=tenants` is the plain ORM spelling there.
- `dashboard/views.py` already calls the helper. `TENANT_FILTERS` is its per-model field
  map and stays.
- `lending/filters.py:39` and `core/context_processors.py:65` must keep the tenant
  condition inside the same `filter()`/`Q` as the other conditions (multi-valued
  relation). A second `filter()` would match different records.

What was left is the `TenantAwareModel` move (step 15, postponed: see *Postponed*).
Rule: request-level scoping goes through the helper; querysets and functions that receive
`tenants` filter with `tenant__in`.

### Inventory workflow in a core model

`Inventory.inventorize_uuids_for_room` (`core/models/inventory.py:270-359`) is the
inventory-scan workflow (found → `localise`, not found → `relocate_lending` or
`transition_lose`, unknown → strip stamps). It is called only from `inventory/views.py:146`
and from tests. The *rules* it applies are lifecycle calls; the *workflow* belongs to the
inventory app. It moves to `inventory/services.py` as a plain function.
`core/models/inventory.py` keeps the model and the queryset. Postponed (step 19): part of
a separate inventory refactoring, see *Postponed*.

### Dead code (delete)

- `core/forms/lentlocalization_form.py`: unused and broken (`Room.type` and
  `Room.TYPE_CHOICER` do not exist).
- `core/views/procure_views.py`, `core/forms/procure_forms.py`,
  `core/templates/core/orderedrecord/procure.html`, URL `core_procure_device`: nothing links
  to them, and the assets app's `device_order` covers ordering through `transition_order`.
  After this, `core/urls.py` holds only the admin relocate action target.
- `core/templates/core/room/records_snippet.html`,
  `core/static/core/proxyrecord_admin/add_form.css` (and the commented-out reference in
  `core/forms/proxyrecord_admin_form.py`).
- `core/tests/test_record_type_choicer.py`: one empty test (`pass`) and a string holding
  code from the initial commit (found during step 2).
- `Room.get_active_records`, `Room.get_lent_records`, `Record.get_proxy_instance` (only
  tests call them), and `Record.get_proxy_model`, whose only caller is
  `get_proxy_instance` (found during step 3).
- **Not dead:** `Device.get_fqdn_url`. Three notification mail templates (`*.txt`) use it.
- Stale text: the `record.py:62-64` comment (`RECORD_TYPE_CLASSES`), the docstrings of
  `core/tests/test_transition_parity.py`, `test_state_write_paths.py` and
  `test_fsm_contract.py` (they describe removed mechanisms and the procure form), and the
  `LendingForm` docstring ("Replaces `LentRecordAdminForm`", which is still in use).
  Found during step 4: the docstrings of `core/tests/test_device_state_data.py`,
  `core/tests/test_record_append_only.py` and `api/tests/test_record_state_contract.py`
  still name `STATE_TRANSITIONS` or a "consolidated FSM" to come.
- Settings: `LOGIN_FIELD` (never read), the second `SITE_ID` (`base.py:132` and `:316`).

### Admin-only members on core models

Scanned on 2026-10-12 (rule 8). The scan is a procedure, run by hand in step 37 and
again in step 36:

1. List every method and property (not `save`, `clean`, `__str__`,
   `get_absolute_url` and other Django hooks) of the classes in `dlcdb/core/models`, with
   `ast`. On 2026-10-12: 55.
2. `grep -rnw` each name over `dlcdb` (`*.py`, `*.html`, `*.txt`, `*.js`), without
   migrations and without the definitions of that name.
3. Sort the readers into admin, frontend, tests and models. Admin code is
   `core/admin/**`, `*admin.py`, `core/templates/admin/**`, the admin's own templates
   `core/templates/core/{device,inroomrecord,lentrecord,lostrecord,record,room,actions}/`
   (its `change_form_template` and `change_list_template`),
   `core/forms/adminactions_forms.py` and `core/views/relocate_views.py`. A
   `list_display` string that names the admin's own `def name(self, obj)` is not a
   reader of the model member.
4. A member with admin readers and no frontend reader, or with no reader at all, is a
   candidate. Check each candidate by hand: generic names give false hits. A member read
   only inside its own model file is a helper, not a candidate.
   `core/utils/device_methods.py` builds the state buttons for the admin and the
   frontend, so its readers need a look too (that is how `get_admin_action_url` was
   found).

| Member | Only reader | Fix (step) |
|---|---|---|
| `Device.get_lent_start_date`, `get_lent_desired_end_date`, `get_lent_end_date`, `get_lent_note`, `get_room`, `get_edv_id` (+ `short_description`) | none, and no dynamic `getattr`; the lending and licence admins define their own `get_edv_id` and `get_lent_desired_end_date` | delete (37) |
| `Device.has_record_notes()` | `DeviceAdmin.has_record_notes_badge` | into `DeviceAdmin` (38) |
| `Device.get_is_currently_lented`, `Device.get_person` | `core/inroomrecord/change_form.html` (`InRoomRecordAdmin`) | `InRoomRecordAdmin.render_change_form` passes the device's unreturned lending (39) |
| `Record.get_admin_action_url()` | `core/utils/device_methods.py`, the admin branch of the state buttons | the URL is built there (40) |

Noted, not moved:
- Members that both the admin and a frontend app read stay, for example
  `Device.get_state_data`, `Device.get_current_inventory_record` and
  `Record.is_type_lent`.
- `Record.get_proxy_model_by_record_type` is read only by tests. It isn't admin code;
  it's a candidate for the dead-code list.
- Outside core, only `inventory.SapList.get_file_name` is admin-only. It waits for the
  postponed inventory refactoring (see *Postponed*).

### Settings module

`dlcdb/settings/base.py` (597 lines) is in reasonable shape: typed env reads, one `.env`,
`test.py` overriding deterministically. Findings:

- **Project settings nobody reads:** `LOGIN_FIELD`; `THEME[*].COLOR`. `DLCDB_BASE_URL` is
  read only by `docs/conf.py`, which is fine. The `UDB_*` keys exist only in the local
  `.env`, not in `env.template`, so there is nothing to change in the repo.
- **Parsed on every use:** `MAX_FUTURE_LENT_DESIRED_END_DATE` is a string, parsed with
  `strptime` in `prx_lentrecord.py:63` and `udb_sync.py:387`. Resolved in step 10: the
  bound is gone, not parsed once.
- **App wiring in global settings** (keep): `lending.loader.DatabaseLoader` as the first
  template loader, the `inventory` context processor on every request, the `tenants`
  middleware, the `journal` logging handlers. The dotted path already names the app.
  Rule (2026-10-11): a docstring says what a component does, what it needs and who reads
  its output; a settings comment is only for what the settings alone show, such as a
  position in a list (order, inside or outside the template cache) or where a handler
  must not be attached.
- **Security bug, independent of this review:** `inventory/context_processors.py:26`
  puts `Token.objects.first().key` into `js_vars` on inventory pages. `Token`'s primary key
  is the key itself, so this is the token whose key sorts first: in practice the dedicated
  API user's token from `docs/betrieb/api.md`. Every user with `core.can_inventorize` gets
  it in the page source. History (git):
  - 2022-02 (initial commit): the API accepts only `TokenAuthentication`.
  - 2023-01-27 (`3fef951c`): the scanner starts calling the API, so it needs a token. It
    borrows the first one.
  - 2023-09-11 (`14c6376c`): `SessionAuthentication` is added, listed *first*, for the
    browsable API. From then on the scanner's token has no effect.
  - 2025-07-21 (`5d6c70a1`, `4d6ec252`): a relative API base URL and
    `credentials: 'include'` on one fetch, as an "experiment" for use behind an Apache
    reverse proxy.

  Checked with a scratch test (2026-10-10): a logged-in request to `/api/v2/devices/`
  authenticates as the *session* user, whether its token header is bogus, valid or absent.
  Without a session, the leaked token authenticates as its owner, from anywhere. So the
  scanner works today only through the session, and the token's only effect is the leak.
  The data exposure is no larger than what the session already gives, because the API is
  read-only and documented as not tenant-filtered. The real damage is a long-lived
  credential that is separate from the user's own account: it keeps working after their
  session expires, after a password change, or after their account is disabled, until
  the token is rotated. Removing the header also makes the scanner independent of how a
  proxy treats `Authorization` (`WSGIPassAuthorization` is still needed for real token
  clients).
- **`ldap.py`** star-imports from a partially initialised `base` (circular). It works.
  The block moves into `base.py`, guarded by `env("AUTH_LDAP")` (step 34; a function
  `apply_ldap(globals())` was rejected, see *Alternatives*).
- **Business thresholds hard-coded in code**, not settings: 5-day overdue tolerance,
  93-day licence warning, 30-day expires-soon notice, 48-hour rescan, `UDB_SYNC_FILTERS`,
  licence name prefixes, `pc`/`ntb` report prefixes, the Archibus building code. Decision:
  they stay in code as named constants next to their one definition. The
  deployment-specific ones (`UDB_SYNC_FILTERS`, report prefixes, building code) are
  candidates for the respective admin-managed singleton, later.
- `reporting/settings.py` is an app module named "settings" (`EXPOSED_FIELDS`). Rename it
  to `reporting/fields.py` to stop the confusion.

### Bugs found on the way

- **Fixed (2026-10-11, step 9):** `core/admin/lentrecord_admin.py:36-37`:
  `session = SessionStore()` at module level. One unsaved session object was shared by
  every request in the process, and held the "new lending" pk between `save_model` and
  `response_change`, so overlapping lends could redirect to each other's lending.
- **Fixed (2026-10-11):** `Device.get_absolute_url` returned `None` for non-licence devices,
  so device mails (`default_body.txt`, `device_decommissioned_body.txt`) printed
  `URL: None`. Regular devices now get their detail page (`assets:device_detail`);
  `obj_link` and the journal no longer work around the `None`, and the admin shows "View on
  site" for every device.
- **Fixed (2026-10-11):** `LentRecord.clean()` (`prx_lentrecord.py:57`) checked
  `lent_end_date` against the UTC date (`datetime.date(now())`), while the return form
  prefills `timezone.localdate()`. From midnight to 02:00 CEST (01:00 CET), returning a
  lending with the prefilled date failed with "The return date cannot be in the future!".
  `Device.get_timeline` and the report titles (`reporting/services.py`, the window start
  is read back in UTC) also used the UTC date. Two tests failed in that window too:
  `test_form_round_trip[lending_return]` (this bug) and
  `test_modified_column_uses_naturaltime_for_recent_edits_only` (it formatted a UTC date
  that the page shows in local time). `date.today()` is not affected: Django sets the
  process timezone to `TIME_ZONE`.
- **Fixed (2026-10-11):** `BaseTest._create_device` drew a random `sap_id` from 0–19999; a
  test creating 26 devices collided in about 1.6 % of runs
  (`test_pager_swaps_only_the_card_newest_first`). Generated IDs are now running numbers
  (`auto-<n>`, `99999-<n>`).
- **Fixed (2026-10-11, before step 10):** the overdue query (`notifications/reports.py`
  `get_lent_overdue_records`) added the 5-day tolerance to every desired return date in
  the database. On SQLite, Django does that in Python, so one lending dated near
  9999-12-31 (the last date Python knows) crashed the overdue report and the overdue
  reminder mails (`DataError: string or blob too big`). The query now subtracts the
  tolerance from today. This is the overflow `MAX_FUTURE_LENT_DESIRED_END_DATE` guarded
  against (step 10).
- Out of scope, noted (2026-10-12): the 403 page (`templates/403.html`) shows only
  `DEFAULT_FROM_EMAIL` as contact, while the login page and the mails use the Branding IT
  address first (`get_contact_email`). Found while tracing `django_settings` (step 21b).
- Out of scope, noted (2026-10-11): the licence iCal export (`licenses/views_calendar.py:59`)
  computes `date + 1 day` for a licence's contract dates and overflows for 9999-12-31.
  Licence dates never had a bound.
- Out of scope, noted (2026-10-12): the licence form schedules the licence notices with
  a plain date (`licenses/subscribers.py`), so Django warns about a naive datetime and
  takes local midnight; the scheduler (`notifications/tasks.py`) makes the same moment
  aware itself. Same result, but one warning per notice. Found in step 24.

### What stays in core although it looks domain-specific

- `LentRecord`, `LicenceRecord`, lending fields on `Record`, `Inventory`, `Note`, `Person`
  HR mirror fields: they are the data model, consumed by several apps, and moving a model
  between apps costs migrations for nothing.
- `LentRecord.objects` returns every active, non-removed record of lendable devices,
  INROOM included (`prx_lentrecord.py:17-30`); `lending` relies on that. A rename is not
  worth the churn; the docstring says so.
- `relocate_device`, `links.py` and the admin relocate view: shared by assets, lending and
  the admin.
- `core/tests/test_transition_parity.py` and `test_state_write_paths.py` drive other apps'
  views on purpose: they prove every write path goes through the lifecycle. They are
  contract tests and stay in core. `test_form_round_trip.py` (edit pages of five apps) and
  `test_native_date_widgets.py` (all ModelForms) are project-wide sweeps; they stay too.

## Decisions taken

1. **No model moves.** Everything here is Python moves, deletions and one-place rules.
2. **Core models, lifecycle and utils import no Python from consumer apps** (rule 5). The
   one accepted exception is the lazy `Branding` import in `get_contact_email`,
   documented at the import.
3. **`Record.X` stays the public spelling of state keys**, defined as aliases of
   `lifecycle.X`.
4. **The `check_transition=False` call sites are listed in the lifecycle docstring.** A new
   one is a review item.
5. **Thresholds stay in code**, one named constant each; not in settings.
6. **The admin stays in core** (asked 2026-10-09). Moving `LentRecordAdmin`,
   `LicenceRecordAdmin`, `RoomAdmin`, `PersonAdmin`, `DeviceAdmin` and the others to the
   apps that own the frontend was considered and rejected (admin URL names would have
   survived, since they derive from the model's app label): the admin is one UI over the
   core models and reads better in one place.
7. **Atomic commits, easiest first** (2026-10-10). Refactors that keep behaviour come
   before, and never mix with, commits that change behaviour.
8. **The inventory scanner uses the session, not an API token** (2026-10-10). The token
   was needed only while the API accepted tokens alone (until 2023). Since then the
   session has served every scanner call, and the token's only effect is the leak. Step
   0 removes it. Operators rotate the exposed token after deploying.
9. **No `has_any_perm` helper** (2026-10-10). It would replace three one-line
   `any(user.has_perm(p) for p in perms)` and delete nothing; no real gain. Step 26 is
   dropped. The other step numbers stay as they are.
10. **The admin is being phased out** (2026-10-12, user). Members that only the admin
    reads leave the models (rule 8). The scan that finds them is a plan step (37), re-run
    in step 36; it is not a test or a script. Steps 37–40 run before phase E and keep
    numbers after 36, so that 32–36 keep theirs.

## Changes against the first draft (2026-10-10)

The plan was checked against the code before reordering. These points differ from the
first draft and need the user's confirmation:

- `Device.get_fqdn_url` is not dead (mail templates); it stays.
- `env.template` has no `UDB_*` keys; that item is gone.
- `update_inventory_note` does not become a `Note` manager method. Once the scan workflow
  has moved (step 19, now postponed), core no longer calls it, and all remaining callers
  are in `inventory`.
- The icon map goes to `theme`, not `dashboard`, because the core admin reads it too.
- `links.py` stays in core (it has no connection to `hints`).
- `dataexchange/reporting.py` has no state keys (its `REMOVED` is an import outcome).
- "Expires soon" becomes a constant, not `LicenceRecord.objects.expiring_soon()`: neither
  copy is a queryset.
- The tenant-scoping batch shrinks to the `TenantAwareModel` move (see *Tenant scoping*).
- The lost-device checks cannot simply be deleted: neither dispatch reaches
  `transition_lend` for a LOST record, and the admin can show a `ValidationError` only from
  form `clean()`. This now comes after the shared dispatch (step 33, where it was
  decided).
- The contract docstring in `core/__init__.py` is written last, when it is true. Until
  then this document is the map.
- The module-level `SessionStore` in the lending admin is fixed on its own (step 9),
  instead of inside the dispatch merge.

## Open questions

- `rename_lifecycle_permissions` (201 lines): a one-off migration helper. Delete it once
  every known instance has run it?
- Should lifecycle transitions write a journal entry (one `JournalEntry.objects.log` in
  `Record.save`)? Not now; noted as an idea.

## Postponed

Topics taken out of this review on purpose. They are kept here so that later steps and
the contract do not quietly assume them done.

### Where `TenantAwareModel` lives (step 15, skipped 2026-10-11)

- **Today:** the abstract `TenantAwareModel` (the `tenant` foreign key: `PROTECT`, nullable
  for legacy devices) is in `tenants/abstracts.py`. Its only user is
  `core/models/device.py` (`Device(TenantAwareModel, SoftDeleteAuditBaseModel)`). The
  module is kept apart from `tenants/models.py` to break an import cycle: core's models
  import it, and `tenants.models` imports core's `AuditBaseModel`.
- **What step 15 would have done:** move it into `core/models/abstracts.py` and delete
  `tenants/abstracts.py`. Skipped by user decision.
- **Consequences while it stays:**
  - Rule 5 has one exception: `core/models/device.py` imports Python from `tenants`.
  - Rule 1 lists `TenantAwareModel` among core's abstract bases, which is not true yet.
  - The contract text (step 36) has to name this exception, unless the move is done by
    then.
- **If it is taken up again:** a small move (one abstract model, one importer, same field
  definition). `makemigrations --check` must stay clean; see *Pitfalls*.

### Device state buttons built in core (step 18, postponed 2026-10-12)

- **Today:** `core/utils/device_methods.py` (`get_device_state_data`, reached through
  `Device.get_state_data`) builds the state badge and its action dropdown: label, CSS
  classes, the badge link, and an action URL per screen. `app_name == "assets"` routes to
  `assets:relocate`, `assets:device_order` and `lending:detail`; `"inventory"` to
  `inventory:inventorize-room`; otherwise to admin pages. *Which* actions are offered
  comes from `lifecycle.available`, which stays in core either way. Callers: the core
  DeviceAdmin (2), `assets/views/devices.py`, `inventory/views.py`. The template it fills
  is in theme since step 17 (`theme/device/state_btn_group.html`).
- **What step 18 would have done:** move the module to `theme/device_state.py`, remove
  `Device.get_state_data`, let the callers call the function, and move
  `core/tests/test_device_state_data.py` to `theme/tests/`.
- **Why postponed (user decision):** nothing is broken. The module imports no Python
  from another app; it only passes URL names to `reverse()`. The move changes no behaviour
  but touches three callers, the model and about 490 lines of tests. Its gain is
  structural: core would stop knowing how other apps route their screens.
- **Consequences while it stays:**
  - Rule 5 has a second exception: core names `assets:`, `lending:` and `inventory:` URLs
    outside `get_absolute_url` and `obj_link`.
  - A new screen that wants its own action routing needs a new `app_name` branch in core.
  - The template is in theme, the data that fills it in core.
- **If it is taken up again:** as step 18 describes. Also update the references in the
  `lifecycle.py` docstring and the `assets/…/_set_state.html` comment.

### Inventory scan workflow in the `Inventory` model (step 19, postponed 2026-10-12)

- **Today:** `Inventory.inventorize_uuids_for_room` (`core/models/inventory.py`) is the
  inventory scan workflow: found → `lifecycle.localise`, not found → `relocate_lending` or
  `transition_lose`, unknown → strip the inventory stamps. It is called from
  `inventory/views.py` and from tests (`inventory/tests/test_inventory.py`,
  `core/tests/test_state_write_paths.py`). For the inventory notes it imports
  `inventory.utils.update_inventory_note`.
- **What step 19 would have done:** move the method to `inventory/services.py` as a plain
  function (`inventorize_room(...)`), so that core no longer imports from `inventory`.
- **Why postponed (user decision):** the inventory app gets its own refactoring as a
  separate task; this move belongs there.
- **Consequences while it stays:**
  - Rule 5 has a third exception: `core/models/inventory.py` imports from `inventory`.
  - Core keeps a workflow that is not a shared rule (the rules it applies are lifecycle
    calls).
- **For the inventory task:** the move as described, then `update_inventory_note` has
  only inventory callers left (see *Changes against the first draft*).

## Steps

### 0 — Out of band: inventory scanner token (security)

Not part of the core review. It goes first because it is a security fix and small
(decision 8).

- `inventory/context_processors.py`: drop `apiToken` and the `Token` import.
  `inventory/assets/js/modules/inventorize.js`: drop the two `Authorization` headers.
  `npm run build`. A test that inventory pages expose no token. One NEWS line that also
  tells operators to rotate the token that was exposed (delete it and create a new one
  for the API user).
- `/verify`: scan a device and a room on the inventory page.
- Commit: `Inventory scanner: pages no longer embed another user's API token; the scanner
  authenticates with the session`

### Phase A — Delete and correct text (no running code changes)

#### 1 — Procure page
- Delete `core/views/procure_views.py`, `core/forms/procure_forms.py`,
  `core/templates/core/orderedrecord/procure.html` and the `core_procure_device` URL. Drop
  the `procure_forms` sentence from the `test_fsm_contract.py` docstring.
- Commit: `Core review, step 1: the unlinked procure page is removed; devices are ordered
  in assets`

#### 2 — Unused files
- Delete `core/forms/lentlocalization_form.py`, `core/templates/core/room/records_snippet.html`
  and `core/static/core/proxyrecord_admin/add_form.css`, with its commented-out reference in
  `proxyrecord_admin_form.py`, plus the empty `core/tests/test_record_type_choicer.py`.
- Commit: `Core review, step 2: unused LentLocalizationForm, room records snippet, admin
  add_form.css and an empty test file removed`

#### 3 — Unused model methods
- Delete `Room.get_active_records`, `Room.get_lent_records`, `Record.get_proxy_instance`
  and `Record.get_proxy_model` (its only caller), plus the tests that cover only them
  (`test_record_model.py`, `test_fsm_contract.py`).
- Commit: `Core review, step 3: unused Room.get_active_records, Room.get_lent_records,
  Record.get_proxy_instance and Record.get_proxy_model removed`

#### 4 — Stale text
- `record.py:62-64` comment; docstrings of `test_transition_parity.py`,
  `test_state_write_paths.py`, `test_fsm_contract.py`, `test_device_state_data.py`,
  `test_record_append_only.py` and `api/tests/test_record_state_contract.py` describe
  today's code; the `LendingForm` docstring no longer claims to replace
  `LentRecordAdminForm`.
- Commit: `Core review, step 4: comments and test docstrings describe the current lifecycle
  instead of removed mechanisms`

#### 5 — Lifecycle docstring lists the bypasses
- List the `check_transition=False` call sites: `dataexchange/importer.py` (3) and
  `inventory/management/commands/fix_inventory_lost_lendings.py` (1). (Decision 4.)
  `Record.save()` points to the list.
- Commit: `Core review, step 5: the lifecycle docstring lists every record write that skips
  the transition check`

#### 6 — Unread settings
- Drop `LOGIN_FIELD` and one of the two `SITE_ID = 1`.
- Commit: `Core review, step 6: settings lose the unread LOGIN_FIELD and the duplicate
  SITE_ID`

#### 7 — Wiring requirements in the docstrings
- The docstrings of `CurrentTenantMiddleware` (needs `request.user`, so after
  `AuthenticationMiddleware`; views across the apps read `request.tenants`),
  `lending.loader.DatabaseLoader` (stays outside the cached loader) and the `inventory`
  context processor (runs on every request, empty outside the inventory app) state their
  wiring requirements. `settings/base.py` is unchanged: its existing comments on the
  lending loader and the journal handlers explain a position and stay. (First done as
  "owning app" comments in settings; reworked on 2026-10-11, see the settings finding.)
- Commit: `Core review, step 7: middleware, template loader and context processor
  docstrings state their wiring requirements`

#### 8 — `reporting/settings.py` → `reporting/fields.py`
- Readers: `reporting/utils/representations.py`, `reporting/tests/test_reports.py`, and the
  path in `docs/guides/notifications.md`.
- Commit: `Core review, step 8: reporting's field list moves to reporting/fields.py, out of
  a module named settings`

### Phase B — Small standalone fixes

#### 9 — Lending admin without a process-wide session
- `lentrecord_admin.py`: replace the module-level `session = SessionStore()` with an
  attribute on the request (`request.new_lending`), set in `save_model` and read in
  `response_change`. Both run in the same request, so nothing needs to persist;
  `request.session` (the first idea) would have carried the pk into later requests.
  Tests: two overlapping lends each redirect to their own lending, and a lend followed by
  an edit redirects to the right record (`core/tests/test_lentrecord_admin.py`).
- Commit: `Core review, step 9: the lending admin keeps the new-lending redirect per request,
  not in one session object shared by all requests`

#### 10 — No upper bound for the desired return date
- First planned as "parse `MAX_FUTURE_LENT_DESIRED_END_DATE` once into a date". Its history
  (git): 2022 a constant 2099-12-31 (DB CheckConstraint plus `LentRecord.clean()`);
  2026-06 the HR sync has to skip contract ends past it; 2026-07 an env var (the user's
  instance: 2999-12-31) and the DB constraint removed. Its reason: adding days to a date
  near 9999-12-31, the last date Python knows, overflows. The only such calculation was
  the overdue query, now written without it (fixed before this step).
- Decision (2026-10-11): remove the bound instead of moving it into the lending
  configuration. Deleted: the check in `LentRecord.clean()`, the skip in the HR sync, the
  setting, the env var (`env.template`) and the 31.12.2099 line in `docs/guides/ausleihe.md`.
  A NEWS line says the env var can go from `.env`. The sync test now pins that a contract
  end in 2100 is taken over.
- Commits: `Overdue lendings: the tolerance is subtracted from today instead of added to
  every desired return date, so dates near 9999-12-31 cannot overflow`, then `Core review,
  step 10: the desired return date has no upper bound; the
  MAX_FUTURE_LENT_DESIRED_END_DATE setting and env var are gone`
- The first commit changes the overdue query that steps 29–31 consolidate later.

### Phase C — Moves, no behaviour change (one move per commit)

#### 11 — `mark_not_handled_assets_in_csv` → `inventory/management/commands/`
- The command name stays the same; its row in `docs/betrieb/management_commands.md` moves
  to the inventory commands.
- Commit: `Core review, step 11: the SAP CSV check command moves to inventory`

#### 12 — `populate_devicetype_icons` → `assets/management/commands/`
- Commit: `Core review, step 12: the device type icon command moves to assets`

#### 13 — Lending print helpers → `lending`
- `markdown_extras` → `lending/templatetags/` (same library name; DB-stored profiles load
  it). `interleaf.html` → `lending/templates/lending/includes/`, and the include in
  `printout_base.html` is updated. `core/templatetags/` is gone. A print test with the
  starter sheet covers both (`lending/tests/test_views.py`).
- Commit: `Core review, step 13: the markdown filter and the print interleaf move to lending,
  their only user`

#### 14 — `uuid2qrcode` → `core/utils/qrcode.py`
- Callers import it from core: `core/models/device.py`, `core/models/room.py` and
  `inventory/management/commands/generate_qrcodes.py`. Removed from `inventory/utils.py`.
- `core/models/inventory.py` still imports `inventory.utils.update_inventory_note`; that
  belongs to step 19, now postponed.
- Commit: `Core review, step 14: QR code generation is a core helper; Device and Room no
  longer import inventory`

#### 15 — Skipped
- Skipped (2026-10-11, user decision). The plan was: move `TenantAwareModel` from
  `tenants/abstracts.py` to `core/models/abstracts.py`. It stays in `tenants`.
  `core/models/device.py` keeps importing it. See *Postponed*.

#### 16 — Model icons → `theme`
- `settings.THEME` becomes a dict in `theme` (e.g. `theme/icons.py`), together with
  `get_icon_for_class`. `COLOR` is dropped. Readers: `dashboard/views.py`,
  `core/admin/base_admin.py`. Done as `theme/icons.py` (`MODEL_ICONS`); a small test
  pins it (`theme/tests/test_icons.py`), none covered the icons before.
- Commit: `Core review, step 16: the model icon map moves from settings to theme`

#### 17 — `state_btn_group.html` → `theme/templates/theme/device/`
- Three render sites: `core/admin/device_admin.py` (2) and `inventory/views.py`. Grep for
  the path first.
- Commit: `Core review, step 17: the device state button template moves to theme`

#### 18 — Postponed
- Postponed (2026-10-12, user decision). The plan was: move `core/utils/device_methods.py`
  to `theme/device_state.py` and remove `Device.get_state_data`. It stays in core for now.
  See *Postponed*.

#### 19 — Postponed
- Postponed (2026-10-12, user decision): the whole inventory refactoring is a separate
  task. The plan was: move `Inventory.inventorize_uuids_for_room` to
  `inventory/services.py`. See *Postponed*.

#### 20 — `nav` → `theme/context_processors.py`
- `nav` and `_app_navigation`; update `TEMPLATES[...]["context_processors"]` and the test
  imports.
- Commit: `Core review, step 20: the navbar context processor moves to theme`

#### 21 — `hints` → `theme/context_processors.py`
- Split from `django_settings` on 2026-10-12 (see 21b). `hints` (with its nested
  `StickyMessage`) moves unchanged; `test_hints.py` and `test_context_processor_queries.py`
  move to `theme/tests/`. Core's context processors no longer import `dataexchange`.
- Commit: `Core review, step 21: the setup hints move to theme`

#### 21b — `django_settings` → `theme/context_processors.py`
- Traced on 2026-10-12: it exposes only `DEFAULT_FROM_EMAIL`, read by two project-level
  templates, `templates/403.html` and `templates/registration/login.html`, for their
  contact line. Offered alternative: a `contact_email` from core's `get_contact_email()`.
  Decision (user): move it unchanged, as planned.
- Delete `core/context_processors.py`. Run the guard grep. No test covered the contact
  line, so `theme/tests/test_contact_line.py` now checks it on both pages.
- Commit: `Core review, step 21b: the settings context processor moves to theme; core has
  no context processors left`

### Phase D — One definition per rule

#### 22 — State keys
- `Record.ORDERED = lifecycle.ORDERED` and so on. The notification report events use
  `lifecycle.X` as their values. A test pins that the report events are exactly the state
  keys (`notifications/tests/test_report_selection.py`).
- Commit: `Core review, step 22: state keys are defined once in lifecycle; Record and the
  notification events reuse them`

#### 23 — Licence device-type prefixes
- `LICENSE_DEVICE_TYPE_PREFIXES` and `license_device_types()` in `licenses/models.py`;
  `forms.py` and `filters.py` both take the queryset from it. A test pins that both offer
  exactly the prefixed types (`licenses/tests/test_device_types.py`). The user guide
  (`docs/guides/lizenzen.md`) named the example type *Lizenz - Grafik*, which no licence
  form offers; it now names the prefixes.
- Commit: `Core review, step 23: the licence device-type prefixes are one constant`

#### 24 — Contract "expires soon" notice
- `Subscription.CONTRACT_EXPIRES_SOON_DAYS = 30`, read by `licenses/subscribers.py` and
  `notifications/tasks.py`. A test pins that the licence form and the scheduler schedule
  the notice for the same moment (`licenses/tests/test_subscribers.py`).
- Commit: `Core review, step 24: the 30-day contract expiry notice is one constant`

#### 25 — Subscriber emails → `licenses`
- The annotation leaves the `LicenceRecord` manager and becomes `subscriber_emails()` in
  `licenses/subscribers.py`. The licence list view annotates it as `subscriber_emails`
  (was `get_subscribers`), and `index.html` reads that. `test_licencerecord_subscribers.py`
  moves to `licenses/tests/test_subscriber_emails.py`; a new view test checks that the
  list shows a subscriber's email. Also gone from core: the commented-out
  `Device.get_subscribers` and a commented-out `prefetch_related("device__subscription_set")`.
  Guard grep: only `Branding` and the postponed `tenants`/`inventory` imports remain.
- Reviewed on 2026-10-12: the licence list was the only reader of `get_subscribers`, ever
  (since 2024-12). The licence admin computed the subquery per row without showing it; it
  no longer does. `dashboard/search.py` cited it as one reason to search licences as
  Devices; the other two reasons stand, so that comment lost its third.
- Commit: `Core review, step 25: licence subscriber emails are annotated in licenses; core no
  longer looks up notifications`

#### 26 — Dropped
- No `has_any_perm` helper (decision 9).

#### 27 — `AuditBaseModel.stamp_user()`, admin side
- Decision (user, 2026-10-12): a model method `stamp_user(user)` instead of a
  `save(user=…)` keyword. In the admin, `save(user=…)` would have meant skipping
  `super().save_model()`, Django's documented idiom (set the fields, then call super),
  and in `TenantAdmin` also django-simple-history's `save_model`. A method also needs no
  keyword threaded through the eight `save()` overrides, and no `update_fields` handling.
- Admin call sites: `core/admin/base_admin.py`, `tenants/admin.py` (2) and
  `dataexchange/admin.py` (2) call `obj.stamp_user(request.user)`.
  `CustomBaseModelAdmin.save_formset` is removed (user decision): none of the 14 admins
  built on it has inlines, so it never ran.
- Tests: `core/tests/test_audit_stamp.py` (`CustomBaseModelAdmin` and `TenantAdmin`), and
  `test_decommission_journal.py` now checks the remover admin's stamp. The importer admin
  and the tenant-assign action were already covered.
- Commit: `Core review, step 27: audit models stamp their editor through stamp_user(); the
  admins use it`

#### 28 — `stamp_user()`, frontend side
- `tenants/views.py` (3), `persons/views.py` (2), `rooms/views.py` (2),
  `assets/views/devices.py` (2), `assets/views/masterdata.py` (2), `dataexchange/views.py`
  (1). `lending/views.py` followed in step 32. `lifecycle.py` and `journal` read
  `get_denormalized_user` differently and stay as they are.
- Done 2026-10-12. The existing tests covered the create views and the three tenant views,
  not the four edit views. `test_edit_unsynced_person` and
  `test_edit_room_returns_to_the_filtered_index` now also check the stamp, and the new
  `test_edit_device_stamps_the_editor` and `test_edit_device_type_stamps_the_editor`
  cover devices and device types. Each of the 12 call sites now fails a test without its
  stamp.
- Commit: `Core review, step 28: frontend views stamp the user through stamp_user()`

#### 29 — `LentRecord.objects.overdue()`, same-meaning readers
- Add the method, built on one `Q` and filtering `record_type=LENT` explicitly (see
  *Pitfalls*), plus one test that pins the meaning: desired end + tolerance ≤ today, not
  returned. Switch over the readers that already mean exactly this: `lending/views.py`,
  `lending/filters.py`, `dashboard/views.py`.
- Done 2026-10-12. `LentRecord.overdue_q(today=None, tolerance_days=0)` (a staticmethod,
  so annotations and plain `Record` querysets can use it) and
  `LentRecord.objects.overdue()` on a `LentRecordQuerySet`. Without `today` it is
  `timezone.localdate()`, Django's today in the current time zone (`timezone.now().date()`
  would be the UTC date); the tolerance is subtracted from `today` (the overflow fixed
  before step 10, see *Bugs found on the way*). The parameter was `as_of` first; renamed
  to `today` (user, 2026-10-12). `core/tests/test_lentrecord_overdue.py` pins the meaning,
  including INROOM, tolerance, 9999-12-31 and local time; each of four broken variants of
  the rule fails it.
- Behaviour: the three readers gain `record_type=LENT`. Only an INROOM record carrying a
  desired return date and no return date could drop out, and no current writer creates
  one (the importer and the HR sync write lending dates only on LENT records; a return
  appends a fresh INROOM record).
- Commit: `Core review, step 29: "overdue" is defined once on LentRecord; lending and the
  dashboard use it`

#### 30 — Admin overdue filter and highlighting
- `lentstate_filter.py` and the `LentRecordAdmin` annotation use the shared `Q`.
  Behaviour change: the highlighting gains the not-returned check.
- Done 2026-10-12. The filter calls `queryset.overdue()`, the annotation
  `When(LentRecord.overdue_q(), …)`; both drop their own `datetime.today()`. No test
  covered either; `core/tests/test_lentrecord_admin.py` now checks the filter and the
  highlighting (an active LENT record with a return date set is marked "lent", not
  "overdue"; the old annotation fails that).
- Behaviour: the highlighting gains the not-returned and the LENT check, the filter the
  LENT check. Only an active LENT record that carries a return date, or an INROOM record
  with a desired return date, changes. No current writer leaves either behind: a return
  sets the date and appends an INROOM record in one transaction, and the importer does the
  same for returned loans.
- Commit: `Core review, step 30: the lending admin marks and filters overdue lendings by the
  shared rule`

#### 31 — Overdue notification report
- `get_lent_overdue_records` uses `overdue(tolerance_days=LENT_OVERDUE_TOLERANCE_DAYS)`.
  Behaviour change: AND instead of OR. Say in the commit whether that can change a real
  report.
- Done 2026-10-12. The query is `Record.objects.active_records()` filtered by
  `LentRecord.overdue_q()`, with `today=timezone.localdate(now)` and
  `tolerance_days=LENT_OVERDUE_TOLERANCE_DAYS`. The base stays `Record`, not
  `LentRecord.objects`, which would also require `device__is_lentable` and so change more
  than planned. New test: a lending with a return date is not reported
  (`test_report_flows.py`); the old query fails it.
- Behaviour: the old OR (`desired date set OR not returned`) was always true next to the
  date filter, so returned lendings counted. Now only an active LENT record that carries
  a return date drops out of the overdue report and the reminder mails. No current writer
  leaves one behind (see step 30), so a real report changes only for such old rows.
- After this step the rule is spelled once: `LentRecord.overdue_q` in
  `core/models/prx_lentrecord.py`.
- Commit: `Core review, step 31: overdue reports and reminder mails use the shared overdue
  rule with their 5-day tolerance`

### Phase D2 — Admin-only members leave the models (runs before phase E)

Rule 8. The findings are in *Admin-only members on core models*.

#### 37 — Admin-only scan; unused `Device` getters removed
- Re-run the scan and update the finding. Delete the six `Device` members nobody reads,
  `get_edv_id.short_description` included.
- Done 2026-10-12. The re-run found the same members as the first scan; the finding stays
  as it is. The six getters are deleted. The msgid "IT ID" stays: the `edv_id` field, the
  asset filter and the device detail page use it too.
- Commit: `Core review, step 37: unused Device lending and IT-ID getters removed`

#### 38 — `Device.has_record_notes` → `DeviceAdmin`
- The query moves into `has_record_notes_badge` (or a private admin method). Add a test
  for the badge if none exists.
- Done 2026-10-12: the query sits in `has_record_notes_badge`. No test covered the badge;
  `DeviceAdminRecordNotesBadgeTests` (`core/tests/test_device_admin.py`) now does.
- Commit: `Core review, step 38: the device admin checks for record notes itself`

#### 39 — `get_is_currently_lented`, `get_person` → `InRoomRecordAdmin`
- `render_change_form` adds `current_lending`: the device's active record if it is a
  LENT record without a return date, else None. The template reads
  `current_lending.person` and `current_lending.pk`. Test: the add form for a lent
  device shows the warning naming the lender; for a device in a room it does not.
- Done 2026-10-12. No test covered the warning; `core/tests/test_inroomrecord_admin.py`
  now checks it for a lent device, a returned lending and a device in a room. It passes
  on the old and the new code (no behaviour change), and fails when the not-returned
  check or the context value is dropped. The warning text is German and untranslated, as
  before; the admin is being phased out, so it stays.
- Commit: `Core review, step 39: the room-assignment admin form looks up the current
  lending itself`

#### 40 — `Record.get_admin_action_url` → `core/utils/device_methods.py`
- The admin add-view URL is built where the state buttons need it, and it moves with
  that module if step 18 is ever done. Check that the state-button tests cover the admin
  URLs.
- Done 2026-10-12: `reverse(f"admin:core_{proxy_model._meta.model_name}_add")` in
  `get_device_state_data`. `core/tests/test_device_state_data.py` already checks the admin
  add-view URLs (10 of its tests fail with a wrong URL). `record.py` no longer imports
  `reverse`.
- Scan re-run after steps 37–40: 45 members, no candidate left; the remaining hits are
  helpers read only inside their own model file.
- Commit: `Core review, step 40: state buttons build the admin add-view URL themselves`

### Phase E — Needs design care

#### 32 — One lend dispatch for frontend and admin
- `prx_lentrecord.py`: `apply_lending(record, edited, *, user)` (INROOM →
  `transition_lend`, LENT + end date → `transition_return_lending`, LENT → in-place save)
  and `lending_warnings(person, desired_end)` (the two HR contract warnings, returned as
  messages, not sent). `lending/views.py` (`_apply_state_machine`,
  `_lending_soft_warnings`, the audit stamp) and `LentRecordAdmin.save_model` call them.
- Test: the admin and the view produce the same record chain for lend → edit → return.
- `/verify`: an admin lend/return round trip and a frontend lend/return round trip.
- Done 2026-10-12, as two `LentRecord` methods rather than functions:
  `apply_lending(*, user)` and `contract_warnings()`. Both screens hand over the edited
  record (`form.save(commit=False)`), so the separate `edited` argument was not needed.
  `apply_lending` returns the lending, the new LENT record after a lend, which the admin
  keeps on the request for its redirect. The edit branch stamps the editor
  (`stamp_user`), so `lending/views.py` no longer imports `get_denormalized_user`.
- Behaviour kept as it was:
  - The admin shows the contract warnings on every save, including a return; the
    frontend skips them on a return. Aligning the admin would change what its users see,
    so it would be a commit of its own. With the admin being phased out, it is not
    planned.
  - The admin's return branch also checked `obj.active_device_record`. That reverse
    one-to-one either returns the device or raises, so it never made the check false.
    `transition_return_lending` refuses an inactive record itself.
  - The admin's edit branch no longer goes through `super().save_model()`, which did the
    same thing: it stamped the user and saved. `Record` keeps no history, so
    django-simple-history's history user does not apply.
  - No msgid changes. The admin's untranslated "Lent state unknown" now uses the
    frontend's translated msgid.
- Tests: `core/tests/test_transition_parity.py` adds the lend → edit → return chain, the
  editor stamp on an edit and both contract warnings, each compared across admin and
  frontend. Mutation checks: dropping the stamp, the warnings (in the method or in the
  admin), the admin's new-lending redirect, or the return branch each fails a test.
- `/verify` on a scratch DB: the admin and the frontend each lent, edited and returned
  a device. Both left the same chain (in room → lent, edited and returned →
  auto-return room), stamped with the editing user.
- Commit: `Core review, step 32: the lending frontend and the admin share one lend, return and
  edit dispatch and one set of contract warnings`

#### 33 — "Lost device cannot be lent", once
- Was blocked on the open question. Today two form `clean()` checks give the message.
  Without them the dispatch would answer "Lent state unknown". Keep the view's GET-time
  guard.
- Looked at again on 2026-10-12, at the user's request (what is it for, is it needed,
  isn't there a shared mechanism?). The message stops an operator from lending a device
  marked "not locatable". It was spelled in four places:
  - `LentRecordAdminForm.clean()`, from 2023 (982fbc20), before the lifecycle module
    existed. Reachable: the lending admin lists LOST records of lentable devices, and
    without the check the save would end in a server error.
  - `LendingForm.clean()`, copied from it in 2026-06. Unreachable: the view redirects a
    LOST record before it binds the form.
  - The view's guard in `lend`, with its own msgid. Reachable from the dashboard search
    and the person's lendings list, which link a LOST record.
  - `print_sheet`'s LOST test (a 404).
- The rule itself was never missing: `lend` starts only from INROOM, and
  `transition_lend` enforces it through `lifecycle.check()`. The copies existed because
  `apply_lending` (step 32) never asked the lifecycle about a record that is neither
  INROOM nor LENT. A lentable ORDERED device fell into the same gap: a server error in
  the admin, and in the frontend an edit screen whose save failed with "Lent state
  unknown".
- Done 2026-10-12, in the style of step 32. `LentRecord.check_lending()` raises
  `IllegalTransition` unless the lending screens can act on the record: a lending always,
  anything else only if `lifecycle.check(device, "lend")` passes. Callers:
  - `LentRecordAdminForm.clean()`, the admin's only place to show an error (like
    `RemovedRecordAdminForm`);
  - the `lend` view, which redirects with the message (like
    `assets/views/devices.py`);
  - `print_sheet` (a 404).
- `apply_lending` hands every record that is not a lending to `transition_lend`, so the
  "Lent state unknown" branch is gone. Also removed: `LendingForm.clean()` and its
  `record_type` argument, `LentRecordAdmin.get_form` and `LOST_DEVICE_NOT_LENDABLE`.
- User decision: the screens show the lifecycle's message, "“Lend” is not allowed for a
  device in state “Not locatable”." It is translated already; the "locate it first" hint
  goes.
- What users see now:
  - a lost device: that message in the admin form and on the lending screen;
  - an ordered lentable device: "… in state “Ordered”." in both screens instead of a
    server error or a failing edit screen, and a 404 instead of a lending slip.
- msgids that go: the old lost-device text, the view guard's text and "Lent state
  unknown - please report this issue!". No new msgid.
- Tests: `LostDeviceCannotBeLentTests` in `core/tests/test_transition_parity.py` now
  checks the screens instead of the two form classes:
  - `check_lending` passes INROOM and LENT and refuses LOST and ORDERED;
  - `apply_lending` refuses a LOST record and writes nothing;
  - the admin form shows the refusal (200, no new record);
  - the lending screen redirects with it on GET and POST;
  - only a lendable device gets a slip.
  The old view test accepted a 404 and never reached the guard; its user now joins the
  tenant. Mutation checks: dropping any of the three calls, or `check_lending` passing
  everything, fails a test.
- `/verify` on a scratch DB with a lost and an ordered lentable device: the admin form
  and the lending screen (GET and POST) show the lifecycle's refusal, in English and
  German. The dashboard search's lending link for the lost device does too. No records
  are written and no server error occurs.
- Commit: `Core review, step 33: the lending screens ask the lifecycle whether a device
  can be lent`

#### 34 — `ldap.py` without the circular import
- `apply_ldap(globals())`, or inline the block. A test imports the settings with
  `AUTH_LDAP` on.
- Decision (user, 2026-10-12): no `globals()`; Django settings should be dead simple.
  The LDAP block moves into `base.py`, under `if env("AUTH_LDAP"):`. Its two imports stay
  inside the `if`, because django-auth-ldap and python-ldap come only with the `ldap`
  extra.
- Done 2026-10-12. `dlcdb/settings/ldap.py` is gone, and with it:
  - the circular import of the half-loaded `base`;
  - the star import back, which also copied `logger`, `ldap`, `env` and the imported
    classes into `base`;
  - the logger stanza;
  - a dead `DJANGO_DEBUG` block.

  The stanza attached a second console handler to `django_auth_ldap`, and the root
  logger already prints INFO, so every LDAP log line was printed twice (checked against
  a copy of the old settings). Now it is printed once. The variant choice is a plain
  `if`/`elif`, with the same error message. Setting names and values are unchanged:
  a dump of every `AUTH_LDAP*` setting, `LDAP_VARIANT` and `AUTHENTICATION_BACKENDS` is
  identical before and after, for `msad` and `openldap`.
- Test: `accounts/tests/test_ldap_settings.py` imports the settings in a fresh process
  and checks:
  - with LDAP on: the backend order, the user search, the flags and both group types;
  - an unknown variant stops the start;
  - with LDAP off: only the email login.

  It passed on the old code before the move. `manage.py check` with LDAP on reports no
  issues.
- Noticed along the way: `env.list("AUTH_LDAP_MIRROR_GROUPS")` keeps the spaces after
  the commas, and `env.template` wrote the value as `group1, group2, …`. A `.env` copied
  from it mirrored `" group2"`, which matches no LDAP group. Fixed in the template (user
  decision, 2026-10-12): the example has no spaces, and a comment says that a space after
  a comma becomes part of the next name. The settings still take the value as written.
- Commit: `Core review, step 34: LDAP settings live in base.py, without a second settings
  module`

#### 35 — Search methods on the model querysets
- First take stock of the person live search, room search and device text search copies,
  then split them into steps here. The has-note part is done (`theme/filters.py`).
- Inventory (2026-10-12):

  | Search | Where | Matches |
  |---|---|---|
  | Person pickers | `lending/filters.py` `LendingPersonFilter`, `assets/views/devices.py` `person_search`, `smallstuff/filters.py` `PersonFilter` | first name, last name, email |
  | Person through a relation | `lending` `LentRecordFilter`, `assets` `DeviceFilter` and `RecordFilter`, `dashboard/search.py` `_smallstuff_search` | the same three |
  | Persons list (and the dashboard's persons group) | `persons/filters.py` `PersonFilter` | the same three plus the UDB-mirrored names and business email |
  | Room picker | `assets/views/relocate.py` `room_search` | number, nickname |
  | Rooms list (and the dashboard) | `rooms/filters.py` `RoomFilter` | number, nickname, description, note |
  | Device picker | `core/utils/device_search.py` `search_devices`, through `theme/views.py` | IDs, manufacturer, series, serial; ranked |
  | Device lists | `assets` `DeviceFilter` (also the dashboard's devices and licences), `lending` `LentRecordFilter`, `licenses` `LicenceRecordFilter`, `assets` `RecordFilter` | different per page |
  | Inventory | `inventory/filters.py` `RoomFilter`, `DeviceFilter` | postponed with the inventory refactoring |

- What the inventory shows, against the plan's assumption of "several copies each":
  - Room and device searches are not copies of one rule. Each list page picks the
    columns its search box covers: lending also finds notes and accessories, the records
    trail `removed_info`, licences the supplier. One queryset method per model would
    either change what pages find, or need parameters that read worse than the field
    lists. The device picker search is in core already.
  - The dashboard search reuses each page's FilterSet; it is not a copy.
  - One rule was spelled seven times, identically: a person matches by first name, last
    name or email.
  - The picker convention (an empty term finds nothing, `*` finds everything) is UI, not
    core. It is repeated in the pickers and in `search_devices`; a matter for `theme`,
    not for this review.
- User decision: `Person.search_q(term, *, prefix="")`, a `Q` like
  `LentRecord.overdue_q`. `prefix` reaches the person through a relation, e.g.
  `"person__"`.
  - The seven sites call it.
  - The persons list adds its UDB fields to it.
  - Room and device searches stay per page.
- Done 2026-10-12. No behaviour change: the same fields at every site.
  - **Tests:** `core/tests/test_person_search.py` checks the rule, case-insensitivity,
    that the UDB names are not part of it, and the prefix.
  - **Mutation check:** I made each call site match nothing, one at a time. At first
    only two of the eight noticed. I added a person-search test to the lending list,
    the asset list, the records trail, the smallstuff search and the dashboard's
    smallstuff group. The persons list was already covered by the dashboard test.
    Now each of the eight fails a test.
- Commit: `Core review, step 35: one rule for which persons match a search term,
  Person.search_q`

#### 41 — The dashboard's "Verliehen" bar counts lent devices
- Found on 2026-10-12, while checking the contract against the code for step 36. Rule 3
  says "what is lent" is one rule. The dashboard's record chart counted its "Verliehen"
  bar as every active record of a lentable device that is neither removed nor a licence.
  That includes available and lost devices, and an available one also counted under
  "Lokalisiert". It goes back to a `LentRecord.objects.count()` (see *Pitfalls*); the
  query optimisation in fc48e810 kept that meaning on purpose. Its comment had drifted
  too: `LentRecordManager` no longer excludes licences.
- User decision: fix it before step 36, in its own commit, because the chart changes.
- Done 2026-10-12. `dashboard/stats.py`: the counts move out of the plotly function into
  `active_record_counts(*, tenants)`, like `devices_per_month` for the timeline. Lent
  means `record_type=Record.LENT`, like the other bars count their state. A lent licence
  now counts as lent.
- Test: `dashboard/tests/test_stats.py` counts one available, one lent and one lost
  lentable device as one each. With the old condition the lent count is 3, and the test
  fails.
- Commit: `Core review, step 41: the dashboard's lent bar counts lent devices, not every
  lentable one`

#### 36 — The contract is written down
- `dlcdb/core/__init__.py` gets the contract (section *The contract*) as its module
  docstring, and `AGENTS.md` gets one line pointing at it. The final guard grep is clean,
  and a re-run of the admin-only scan finds nothing on the core models (rule 8).
- Checked against the code on 2026-10-12, before writing it down:
  - **Rule 1** holds.
  - **Rule 2** overstated it. The admin's add views for the state proxies (in room, lost,
    removed, ordered) save the proxy directly. `Record.save()` checks them against the
    transition table, but they do not go through `transition_*`. The docstring says so.
  - **Rule 3**: "what is lent" was not one rule; fixed in step 41. The rules now also
    live as `*_q` methods and as model methods (`overdue_q`, `search_q`,
    `apply_lending`), not only on managers.
  - **Rule 4** holds. `core/utils/helpers.py` also has two helpers with one consumer
    each: `get_user_email` (inventory) and `save_base64img_as_fileimg` (the UDB sync).
    Noted, not moved.
  - **Rule 5**: the guard grep is clean. It lists only `Branding` (accepted),
    `tenants.abstracts` and `inventory.utils` (both postponed). The rest of core imports
    no consumer app either, apart from the admin.
  - **Rule 6**: the admin also imports `tenants.shortcuts`, `tenants.models` and
    `theme.icons`. Also part of the admin: `navigation.py` (the admin-changelist nav
    entries), `urls.py` (the relocate action target) and every form in `core/forms/`.
  - **Rule 7** also covers `views/error_views.py` (the error-mail check),
    `utils/sqlite_snapshot.py` (behind `tasks.py`) and `rename_lifecycle_permissions`
    (see *Open questions*). The only `fix_*` command left in core is
    `fix_record_modified_at_timestamps`.
  - **Rule 8**: the admin-only scan finds 49 members and no candidate. The remaining
    hits are helpers read only inside their own model file, plus
    `Record.get_proxy_model_by_record_type`, which only tests read (as noted under
    *Admin-only members*).
- First draft: the whole corrected contract, about 70 lines, as the module docstring.
  The user questioned it (2026-10-12). It is just prose, and a clear interface would
  rather export the consumable parts through `__init__.py`. Honest answer:
  - A Django app's `__init__.py` cannot re-export models. `"dlcdb.core"` is in
    `INSTALLED_APPS`, so Django imports the package before models can be defined
    (`AppRegistryNotReady`).
  - Core's facades are its modules. Other apps import from `dlcdb.core.models` (51
    imports; its `__init__` re-exports every model), `dlcdb.core.lifecycle` (19) and
    `dlcdb.core.utils.*` (20), plus a few deep imports.
  - The lists of models, helpers, admin files and plumbing duplicate the code and would
    drift.
- User decisions:
  - a short docstring with only the rules that cannot be read off the code, and no
    lists;
  - no import test: rule 5 stays documentation, and the guard grep stays a manual
    check.
- Done 2026-10-12. `dlcdb/core/__init__.py` is 18 lines. It names:
  - where other apps import from, and why nothing is re-exported there;
  - the dependency rule with its three exceptions, and the admin's place;
  - records appended through the lifecycle, with the `Record.save()` check;
  - shared rules living once in core, and lentable versus lent;
  - admin-only methods belonging in the admin.

  A script resolved every name it mentions, and the guard grep lists exactly its three
  exceptions. `AGENTS.md` points at the docstring.
- Commit: `Core review, step 36: core/__init__.py states the contract other apps rely on`

## Alternatives considered and rejected

| Approach | Why not |
|---|---|
| A `services.py` layer in core for every workflow | Adds a layer; the lifecycle functions already are the service API. Workflows (inventory scan, lending dispatch) belong to the app that owns the screen. |
| Moving `Tenant` into core | Migration churn for a model that only core references by string anyway. |
| Signals on `Record` for journaling/notifications | Project rule (journal plan, decision 8): explicit calls, no signals. |
| Moving the model admins to the frontend apps | Asked and rejected (decision 6): one UI over the core models reads better in one place; the admin may import consumer helpers. |
| Retiring the admin UI for lending/licences | Out of scope for this review. The admin is being phased out (decision 10); this review keeps the models free of admin-only code (rule 8). |
| Re-exporting core's interface from `dlcdb/core/__init__.py` (step 36) | Django imports the app package before models can be defined (`AppRegistryNotReady`). Core's facades are its modules: `dlcdb.core.models`, `dlcdb.core.lifecycle`, `dlcdb.core.utils`. |
| An import-boundary test for rule 5 (step 36) | User decision (2026-10-12): the rule stays documentation in `dlcdb/core/__init__.py`, and the guard grep stays a manual check. |
| A pytest guard or a script for the admin-only scan | Grep-based and heuristic (generic names, `list_display` strings, admin templates). A documented procedure, run by hand in steps 37 and 36, is enough (decision 10). |
| `apply_ldap(globals())` for the LDAP settings (step 34) | A function that writes into the module namespace is harder to read than the plain assignments it replaces; settings stay dead simple (user, 2026-10-12). |
| Putting thresholds into settings | Nobody tunes them per deployment; a named constant next to its one definition is easier to find. |
| Large batches per theme (first draft) | Core changes deserve atomic commits that can be reviewed and reverted one by one (decision 7). |
| `tenant_scoped_queryset` everywhere | Takes a request; does not fit querysets that get `tenants`, nor conditions that must stay in one `filter()` (see *Tenant scoping*). |

## Pitfalls

- `tenants/abstracts.py` exists to break an import cycle. Moving `TenantAwareModel` into
  core resolves it the other way round (`tenants.models` imports core, and core references
  `"tenants.Tenant"` only as a string). Check that `makemigrations --check` stays clean.
- `LentRecord.objects` includes INROOM records. Any new "lent" query must filter
  `record_type=LENT` explicitly (the dashboard stat did not; fixed in step 41).
- The lifecycle `transition_*` functions check state, not permissions. Permission checks
  stay in views/admins (`lifecycle.available`).
- Before moving or deleting a template or method, grep `.html`, `.txt` (mail templates)
  and the migrations (DB-stored templates), not only `.py`.
- Template tag libraries are loaded by name. Moving one keeps its module name.
- Multi-valued relations: a tenant condition split into its own `filter()` can match a
  different related row than the other conditions.

## Progress

- [x] Plan written (2026-10-09), reordered into atomic steps (2026-10-10)
- [x] 0 — Inventory scanner token (out of band)
- [x] 1 — Procure page removed
- [x] 2 — Unused files removed
- [x] 3 — Unused model methods removed
- [x] 4 — Stale text
- [x] 5 — Lifecycle docstring lists the bypasses
- [x] 6 — Unread settings
- [x] 7 — Wiring requirements in the docstrings
- [x] 8 — `reporting/fields.py`
- [x] 9 — Lending admin without a process-wide session
- [x] 10 — No upper bound for the desired return date
- [x] 11 — `mark_not_handled_assets_in_csv` → inventory
- [x] 12 — `populate_devicetype_icons` → assets
- [x] 13 — Lending print helpers → lending
- [x] 14 — `uuid2qrcode` → core
- ~~15 — `TenantAwareModel` → core~~ skipped (2026-10-11)
- [x] 16 — Model icons → theme
- [x] 17 — `state_btn_group.html` → theme
- ~~18 — Device state data → theme~~ postponed (2026-10-12)
- ~~19 — Inventory scan workflow → inventory~~ postponed (2026-10-12)
- [x] 20 — `nav` → theme
- [x] 21 — `hints` → theme
- [x] 21b — `django_settings` → theme
- [x] 22 — State keys
- [x] 23 — Licence device-type prefixes
- [x] 24 — Expires-soon notice
- [x] 25 — Subscriber emails → licenses
- ~~26 — `has_any_perm`~~ dropped (decision 9)
- [x] 27 — `stamp_user()`, admin
- [x] 28 — `stamp_user()`, frontend
- [x] 29 — `overdue()`, same-meaning readers
- [x] 30 — Admin overdue
- [x] 31 — Overdue report
- [x] 37 — Admin-only scan; unused `Device` getters removed
- [x] 38 — `has_record_notes` → `DeviceAdmin`
- [x] 39 — `get_is_currently_lented`/`get_person` → `InRoomRecordAdmin`
- [x] 40 — `get_admin_action_url` → state buttons
- [x] 32 — One lend dispatch
- [x] 33 — Lost-device check once
- [x] 34 — `ldap.py`
- [x] 35 — Search methods
- [x] 41 — Dashboard lent bar
- [x] 36 — The contract is written down

## Verification (each step)

- `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- `.venv/bin/python manage.py makemigrations --check --dry-run` (no model moves, so no new
  migration may appear)
- `.venv/bin/pytest .`
- A grep guard, run after steps 14, 15, 19, 21, 25 and 36:
  `grep -rn "from dlcdb\.\(assets\|inventory\|lending\|licenses\|theme\|journal\|organization\|dataexchange\|tenants\|notifications\)\|get_model(\"notifications" dlcdb/core/models dlcdb/core/lifecycle.py dlcdb/core/utils`
  must end up listing only the accepted exception (`Branding` in `get_contact_email`) and
  the postponed ones: `tenants.abstracts` in `models/device.py` (step 15) and
  `inventory.utils` in `models/inventory.py` (step 19). Step 18 does not show up here: it
  names URLs, it imports nothing.
- `/verify` after steps 0 (scanner), 17–21 (device list state buttons, inventory room
  page, navbar, hints band), 30 and 32 (admin and frontend lend/return).
- The admin-only scan (*Admin-only members on core models*) after steps 37–40 and in
  step 36.

## Pre-merge review (2026-10-12)

The branch `core-consolidation` was reviewed as a whole before merging into `main`. The
questions: did the code drift from the plan, did a later step undo an earlier one, and what is
left to clean up in core? The steps and checklist below are this section's own; the sections
above stay as they were.

### How it was reviewed

- **Merge readiness:** `main` has no commits since the branch point (9b0556b3), so the merge
  has no conflicts. 49 commits, 135 files.
- **Gates** on a scratch DB:
  - `ruff check` and `ruff format --check`: clean;
  - `manage.py check`: no issues;
  - `makemigrations --check --dry-run`: no changes;
  - `pytest`: 1077 passed. Its two warnings are the naive licence-notice datetime (see *Bugs
    found on the way*).
- **The diff against the merge base** (`git diff main...core-consolidation`), file by file:
  - core's models, lifecycle, utils, admin, forms and templates;
  - every consumer app;
  - settings and docs.
- **Moves:**
  - `hints`, `nav`, `_app_navigation` and `django_settings` in `theme/context_processors.py`
    are identical to the code deleted from core (compared with `ast`);
  - the other moves are plain renames or changed only their imports.
- **Removed and moved names:** a sweep over `.py`, `.html`, `.txt`, `.js`, `.md`, `.toml` and
  the templates finds no reader left. The only hit outside this file is
  `PLANS/flexible-tenants.md` (step 43).
- **Steps against each other:**
  - overdue and the person search are each spelled once;
  - the `check_transition=False` sites match the lifecycle docstring (3 + 1);
  - the guard grep lists only the three exceptions in `dlcdb/core/__init__.py`;
  - each new model method has a reader outside the admin (rule 8);
  - removed tests covered only deleted methods; no test was weakened;
  - new files carry SPDX headers without a year.

### Verdict

The branch is consistent: no step undid another, the moves are faithful, and the gates are
green. Steps 43–47 are follow-ups; the problems they fix are older than the branch.

### Follow-ups in core (easiest first, one commit each)

#### 43 — Stale text
- `Device.get_timeline`: the docstring has been garbled since 2024-12 ("Returns the license
  timelicense.get_license_state_labelline …").
- `PLANS/flexible-tenants.md` (*Open follow-ups*) names `core/context_processors.py:hints`; it
  is `theme/context_processors.py` now.
- `dashboard/views.py` and `lending/filters.py`: two blank lines left where an import was
  removed.
- `licenses/tests/test_subscriber_emails.py`: the helper is still called `_get_subscribers`,
  after the annotation it no longer reads (step 25).

#### 44 — `Record.get_proxy_model_by_record_type` removed
- An alias of `lifecycle.proxy_for`, read only by two tests in `test_fsm_contract.py`;
  `test_lifecycle.py` covers `proxy_for` already. First noted under *Admin-only members on core
  models*.
- Done: the stamping test in `test_fsm_contract.py` calls `lifecycle.proxy_for`; the other
  was a copy of `test_lifecycle.py::test_every_state_maps_to_a_proxy_model` and is gone.

#### 45 — The `LicenceRecord` manager without leftovers
- `prx_licencerecord.py`, no behaviour change:
  - the 93-day "expiring" window becomes a named constant (decision 5), and the "make threshold
    configurable" TODO goes;
  - `timezone.localdate()` instead of `datetime.today().date()`: the same value, the spelling
    the rest of the branch uses;
  - removed: the "80-warning" TODO (the states are named already), the commented-out `When`
    clauses and the double `Q(Q(...))`.
- Done: the constant is `EXPIRING_WITHIN_DAYS` in `prx_licencerecord.py`, its only reader. No
  test covered the states, so `core/tests/test_licencerecord_state.py` pins the window's edges
  and that removed licences are not listed; it passes on the old manager too.

#### 46 — Dead state checks in the licence admin
- `LicenceRecordAdmin.get_contract_expiration_date` compares `license_state` with `"80-warning"`
  and `"90-danger"`. The manager stopped producing these in 2024-11 (a1fcef4c), so the tooltip
  never shows.
- User decision:
  - drop the two branches (the admin is being phased out), or
  - check `expiring` and `expired` instead, so the tooltip shows again (a visible change).
- Decided (2026-10-12): drop. The row colours were dead too: `licence.js` copied the
  `alert-<state>` class onto the row, and the admin SCSS styled only `alert-80-warning` and
  `alert-90-danger`. Removed: the tooltip, the classes on the date, `licence.js` and its
  `Media`, and the licence selectors in `frontend/admin/scss/_bootstrap_adjustments.scss`
  (including `tr.licence-state-40-lent`, which never matched). The lent-row rules stay. The
  column shows the date only; nothing visible changes.

#### 47 — `DeviceAdmin` keeps no request on the shared admin
- `get_list_display` stores `self.request`, and `get_device_actions` reads it to build the
  state buttons. The `ModelAdmin` instance is shared by all requests, as the `SessionStore` was
  in step 9: two overlapping changelist requests can get state buttons built with the other
  user's permissions.
- Already listed in `PLANS/flexible-tenants.md` under *Open follow-ups*.
- Fix: `get_list_display` builds the actions column per request (a callable that closes over
  the request); nothing is stored on the instance. A test in the style of step 9.

### Noted, not proposed

- After `apply_lending`, both screens work out again what happened, for their messages and the
  redirect: the admin in `save_model` (`record_type == INROOM`) and `response_change`, the
  lending frontend in `_save_lending`. There, `edited` is `record` itself
  (`form.save(commit=False)` returns the form's instance), so
  `record.lent_end_date or form.cleaned_data.get("lent_end_date")` checks the same value twice.
  Presentation only, too small for a step.
- `print_sheet` raises the same 404 in two places.
- Open question: the overdue report and the reminder mails count every active LENT record; the
  dashboard tile and the lending list only those of lentable devices (`LentRecord.objects`).
  Kept on purpose in step 31. Align them?
- `core/utils/helpers.py` keeps two helpers with one consumer each (step 36):
  `get_user_email` and `save_base64img_as_fileimg`.
- Outside core:
  - theme's `nav` carries a nested `_get_is_active` that is never called and only raises
    `NotImplementedError` (moved unchanged in step 20);
  - `mark_not_handled_assets_in_csv` has debug `print`s and commented-out code, for the
    inventory refactoring.
- Docs, optional: the `LentRecord` row in `docs/betrieb/model.md` could say that its manager
  lists lentable devices, not lent ones.

### Merge

- From `main`: `git merge --no-ff core-consolidation`. It keeps the atomic commits, each
  revertable on its own (decision 7), and adds one merge commit that reverts the whole review.
  `--ff-only` works too, for a linear history. A squash would lose the per-step reverts.
- Before merging: the gates again, after each follow-up done on the branch.
- After the merge: `PLANS/` is for work not done yet (AGENTS.md). Trim this file to
  *Postponed*, *Open questions* and this section, or delete it. User decision.

### Progress (pre-merge review)

- [x] 43 — Stale text
- [x] 44 — `get_proxy_model_by_record_type` removed
- [x] 45 — `LicenceRecord` manager without leftovers
- [x] 46 — Dead state checks in the licence admin
- [ ] 47 — `DeviceAdmin` keeps no request on the shared admin
