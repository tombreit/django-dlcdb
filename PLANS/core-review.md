<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Core review: dlcdb/core as the contract — open work

**Status:** steps 0–47 are done on the branch `core-consolidation`
(`git log --grep "Core review, step"`). The full plan, with its findings and the notes for each
step, is in git: `git show a266e9a4:PLANS/core-review.md`. This file was trimmed on 2026-10-13
to what is left before the merge into `main`: tasks 48–71 below, grouped by component.

## Why

`dlcdb/core` holds the models, the device lifecycle and the rules the other apps rely on. The
review cleaned up core and consolidated rules that were spelled more than once. The tasks below
come from the review itself: postponed moves, open questions, bugs noted on the way, and smells
found in the pre-merge review. All of them were checked against the code on 2026-10-12.

## How we work through it

- One concern per commit. A move never also changes behaviour. A visible change gets its own
  commit that says so.
- Easiest first, one component at a time (the groups below).
- Before a task starts: check its premise in the current code. The plan drifts.
- After each task: the gates (*Verification*), tick the box, suggest a one-line commit message
  (`Core review, step N: …`), stop. The user commits before the next task starts.
- `NEWS.md`: only for significant changes.
- `DATABASE_URL` points at a throwaway sqlite file, never at the dev database.

## Decisions that still apply

The contract is the module docstring of `dlcdb/core/__init__.py`.

1. **No model moves.** Python moves, deletions and one-place rules only.
2. **Dependency rule.** Core's `models/`, `lifecycle.py` and `utils/` import no other app,
   except the exceptions named in the docstring. Tasks 67 and 69 remove two of the three.
3. **`Record.X`** stays the public spelling of the state keys (aliases of `lifecycle.X`).
4. **`check_transition=False`** call sites are listed in the lifecycle docstring. A new one is a
   review item.
5. **Thresholds stay in code**, one named constant each, not in settings.
6. **The admin stays in core**, as one UI over the core models. It may import other apps.
7. **Atomic commits, easiest first.** Refactors that keep behaviour never mix with changes.
8. **The admin is being phased out.** A model member that only the admin reads belongs in the
   admin.
9. **Overdue (2026-10-12).** The importer refuses a LENT row on a device that is not lendable
   (task 59). The two overdue queries keep their differences on purpose:
   - the mails wait a 5-day tolerance and cover every tenant;
   - the dashboard and the lending list count from the desired return date, for the user's
     tenants only.
10. **`DEVICE_HIDE_FIELDS` is removed (2026-10-12)** (task 63).
11. **Untranslated strings in the core admin stay (2026-10-12).** The admin is being phased out.
12. **Warnings fail the test suite (2026-10-12)** (task 51).

## Tasks

### Docs and stale text (no running code)

#### 48 — Stale text and docs
- `lending/pickers.py:9` says a lendable device "is not a licence". Licences can be lent since
  2731fff2 (`lifecycle.py:143-145`).
- `docs/betrieb/model.md`: the `LentRecord` row says that its manager lists the active records of
  lendable devices in every state (INROOM, LENT, LOST, ORDERED), not only lent ones. The
  `LicenceRecord` row already describes its manager.
- The idea "a journal entry for every lifecycle transition" moves to `PLANS/journal.md`
  (*Open follow-ups*), with two facts:
  - `Record` has no tenant, so an entry needs the device's tenant passed explicitly;
  - the journal plan allows explicit calls only, no signals.

### Tests and warnings (merge gate)

The normal run is green with 2 warnings. `pytest -W error` fails: 14 failed and 1 error, because
of files and connections nobody closes, plus the naive licence datetime. A leak is reported in
whichever test runs when the object is collected, so the failing tests vary.

#### 49 — Licence notices are scheduled as aware datetimes
- `licenses/subscribers.py:85-92` writes a plain date into `Subscription.next_scheduled`, a
  `DateTimeField`. Django warns and takes local midnight.
- The scheduler spells the same moment as `_ensure_aware_dt` (`notifications/tasks.py:31-44`).
  It becomes a public helper in `notifications/services.py`, which `subscribers.py` already
  imports, and both use it.
- No behaviour change: the same stored moment, pinned by `licenses/tests/test_subscribers.py`.
- Done: the helper is `local_midnight(date)` in `notifications/services.py`. It takes only a
  date, which is all both callers pass, so the scheduler's `None` checks after it went too.

#### 50 — Files and connections are closed
- FieldFiles opened implicitly and never closed:
  - `dataexchange/importer.py:414`, reached from `dataexchange/views.py:155` and
    `dataexchange/admin.py:127`;
  - `dataexchange/remover.py:47`, reached from `dataexchange/admin.py:237`;
  - `notifications/channels.py:103` (`report.spreadsheet.read()`).

  Close each with `with … open()`, at the call site or inside, whichever reads simpler. The SAP
  path (`sap_converter.py`) shares the importer's file.
- `core/tests/test_sqlite_snapshot.py:33,44,59`: `with sqlite3.connect()` commits but does not
  close. Use `contextlib.closing`.
- Done: the callers that pass a stored file open it with `with … open("rb")`: the import
  confirm view, the import and decommission admins, the report mail. A form's upload needs
  nothing; Django closes it after the request. `pytest -W error` passed twice in a row.

#### 51 — Warnings fail the suite
- `filterwarnings = ["error"]` in `[tool.pytest]` of `pyproject.toml`.
- A full run shows no warnings. From here on, every task runs with warnings as errors.

### theme

#### 52 — `nav` leftovers
- `theme/context_processors.py`:
  - the nested `_get_is_active` (:57-72) is never called and only raises `NotImplementedError`;
  - a commented `print` (:102);
  - a stale comment (:109-111).
- No behaviour change. Covered by `theme/tests/test_navbar.py`.

#### 53 — The 403 page names the IT address first **Skip**
- `templates/403.html:20` shows only `DEFAULT_FROM_EMAIL`. The login page
  (`templates/registration/login.html:70`) and the mails (`get_contact_email`) use the Branding
  IT address first.
- The 403 page takes the login page's expression:
  `branding.organization_it_dept_email|default:django_settings.DEFAULT_FROM_EMAIL`. The msgid
  stays.
- `theme/tests/test_contact_line.py` only checks the fallback. A new test checks that the
  Branding address wins, on both pages.
- Visible change.

#### 54 — One picker convention
- The pickers' convention is "an empty term finds nothing, `*` finds everything, anything else
  is searched". It is spelled five times:
  - `core/utils/device_search.py` `search_devices` (through theme's `device_search`);
  - `lending/filters.py` `LendingPersonFilter`;
  - `assets/views/devices.py` `person_search`;
  - `assets/views/relocate.py` `room_search`;
  - `smallstuff/filters.py` `PersonFilter`.
- One helper in theme (for example in `theme/pickers.py`) applies it, and every picker uses it.
  Core's `search_devices` keeps only the ranking. The convention leaves core, because core may
  not import theme. Check its other callers first.
- The FilterSets' empty-term branches are dead: django-filter never calls a filter method with an
  empty value (`theme/filters.py` says so too). They go.
- **Behaviour fix:** `smallstuff/views.py:22` builds its FilterSet without a queryset, so an
  empty search lists every person. It gets a queryset that finds nothing for an empty term.
- Tests for the cases not covered yet:
  - `*` in the assets person picker;
  - an empty term and `*` in the room picker;
  - an empty term and `*` in smallstuff.
- Done narrower than planned (54a, 54b): `theme.pickers.picker_filter(queryset, term, condition)`
  takes a `Q`; the person and room pickers call it. The device picker keeps its own lines in
  `search_devices` (a ranking, not a `Q`; core may not import theme), and both FilterSets stay.
  54a fixed the smallstuff view; one unit test covers `picker_filter`.

### Licences

#### 55 — The iCal export survives 9999-12-31
- `licenses/views_calendar.py:56-60` adds one day for `dtend`. For `date.max` that raises
  `OverflowError`, a 500. Contract dates have no upper bound.
- Fix: no `dtend` for `date.max`; RFC 5545 makes an all-day `DTSTART` one day long. Also
  removed: the duplicate branch (:49-54) and the inline import.
- No test covers the calendar view yet. A test for an ordinary licence and one for 9999-12-31.

### Lending

#### 56 — Two pages ignore the tenant boundary

**In short.** Every device belongs to one tenant (*Mandant*), and a user sees only the devices of
their own tenants (`docs/guides/berechtigungen.md`, *Mandanten*). Almost every page checks that.
Two pages don't: they load their record straight from the number or ID in the URL.

1. **Printing the slip of a saved lending** (`/lending/record/<number>/print/`,
   `lending/views.py` `print_lent_sheet`).
   - Only the print button on the old admin's lending form links to it.
   - It needs `core.view_lentrecord`.
   - The number is the record's database ID, a counter. Change it by hand, and the page prints
     the slip of any active lending, also one of another tenant: the borrower's name and
     organizational unit, the reason, the device with serial and inventory number, and the
     dates.
2. **The licence's calendar file** (`/licenses/<uuid>/calendar.ics`,
   `licenses/views_calendar.py` `license_calendar`).
   - It needs `core.view_licencerecord`.
   - The UUID is random, so it can't be guessed, only copied from somewhere the licence was
     visible.
   - The file holds the licence's name and ID and its contract dates. No persons.

**Fix.** Both views load their record through the tenant filter that the views next to them
already use: `_tenant_scoped` in lending, `tenant_scoped_queryset` in licenses. A record of
another tenant then gives "not found" (404), as everywhere else. One test per view: a record of
another tenant gives a 404. Small, its own commit.

**If it is not done.**
- Nothing stops working; this closes a gap, it adds no feature.
- The lending slip is the real risk.
  - An account with `core.view_lentrecord` can read, page by page, who has borrowed which device
    in every other tenant: personal data across the boundary the docs promise. The docs' list of
    known exceptions doesn't mention it.
  - Limits: only active lendings, read only, only by typing URLs by hand.
  - It does not matter if the instance has one tenant, or if everyone with that permission sees
    all tenants anyway.
- The calendar file is a small risk: the UUID can't be guessed, and the file holds no personal
  data.
- If the fix is not wanted, both pages belong in the docs' list of exceptions
  (`berechtigungen.md`, "Nicht auf die eigenen Mandanten eingeschränkt sind").

**Alternative for the slip.** The lending screen already prints the same slip, tenant-scoped,
also for an active lending (`print_sheet`). `print_lent_sheet` could be deleted together with its
button in the old admin, which is being phased out. Then admin users print from the lending
screen instead.

**Decided (2026-10-13):** the admin's print action goes, with no replacement link, and with it
`print_lent_sheet` and its URL. The calendar file gets the tenant filter.
- Done (56a): the admin's lending form template (`core/lentrecord/change_form.html`, which only
  held the print button) and its `change_form_template` line are gone, and so are
  `print_lent_sheet` and its URL. Slips print from the lending screen, which needs the lending
  permission, not only `core.view_lentrecord`. A test checks that the admin form has no print
  link; it failed before the removal.
- Done (56b): `license_calendar` loads the licence through `tenant_scoped_queryset`, like the
  licence history page. A licence of another tenant gives a 404 (the test got 200 before).

#### 57 — `print_sheet` raises its 404 once
- `print_sheet` raises the same 404 in two places (`lending/views.py`, after the record lookup and
  after `check_lending`). Check once.
- The duplicated profile lookup is gone with `print_lent_sheet` (task 56).
- No behaviour change.
- Dropped (2026-10-13, user decision): there is no yes/no variant of `check_lending`, so raising
  once needs a flag and a nested `try`. That is longer than today and hides that there are two
  separate reasons (no record, record not lendable). The code stays as it is.

#### 58 — The lending screens ask the record what a save does

**In short.** Saving a lending, on the lending screen or in the admin, does one of three things:
lend the device, acknowledge its return, or save edits to a running lending.
`LentRecord.apply_lending` decides which. Afterwards each screen needs to know what happened,
for its message ("lent to …", "return acknowledged", "saved") and, in the admin, for the page it
goes to next. `apply_lending` doesn't tell them, so each screen guesses again from the record's
fields, in its own way:
- the lending screen (`lending/views.py` `_save_lending`) asks "was it in a room?", then "is there
  a return date?";
- the admin (`core/admin/lentrecord_admin.py` `response_change`) asks "is there a return date?"
  first.

**Change.** The rule is written once, as a small method on the record: `lending_action()` returns
"lent", "returned" or "edited". `apply_lending` uses it to decide, and both screens use it to pick
their message and redirect.
- Clean-ups in `_save_lending`: `edited` is the same object as `record`
  (`form.save(commit=False)` returns the form's instance). So two checks there read one value
  twice: `record.lent_end_date or form.cleaned_data.get("lent_end_date")` and
  `form.cleaned_data.get("person") or record.person`. They become `record.…`.
- Kept: the admin also shows the contract warnings on a return (step 32).

**The admin's wrong message (suspected, not yet run).** The admin form shows the *Return* field
(`lent_end_date`) on every lending, also on an available device. Nothing refuses a return date
on a lend. If someone fills it in while lending:
- the device is lent, correctly, and the return date is ignored;
- but the admin answers "Return of … acknowledged" and goes back to the list instead of to the
  new lending, because it checks the return date first.

With the shared rule the admin says "lent" and opens the new lending.

**Steps.**
- 58a, no behaviour change: `lending_action()` on `LentRecord`, used by `apply_lending` and by the
  lending screen. Its tests cover the three cases.
- 58b, the admin: first a test that lends an available device with a return date filled in. If
  it fails, the bug is real, and the admin switches to `lending_action()`, which fixes it. If it
  passes, the admin switches anyway; then there is no behaviour change.

**If it is not done.**
- The lending screen: nothing changes for users; the double checks stay as noise.
- The admin: someone who fills in a return date while lending gets a wrong message and lands on
  the list. The device is still lent correctly. Rare, and the admin is being phased out.
- The rule "which of the three" stays spelled three times. A change to it, for example a new
  case, has to find all three.

- Done (2026-10-13), 58a and 58b in one commit (user decision): `LentRecord.lending_action()`;
  `apply_lending`, `_save_lending` and the admin's `save_model`/`response_change` use it.
  `_save_lending` no longer calls `form.save(commit=False)`: validating the form already filled
  in `record`. The admin bug was real: the test's lend with a return date went back to the list;
  now it opens the new lending and says "lent". Tests in `core/tests/test_transition_parity.py`.

### dataexchange

#### 59 — The importer refuses a LENT row on a device that is not lendable
- The CSV importer takes `is_lentable` from the row (`dataexchange/importer.py:280,307`) and
  saves the lending with `check_transition=False` (:203). `LentRecord.clean()`, which requires
  a lendable device, never runs.
- Such a lending is mailed as overdue, but the dashboard and the lending list don't show it, and
  the lending screens cannot return it.
- The row becomes an import error, reported like the other row errors (decision 9). Test in
  `dataexchange/tests/`.
- `docs/guides/notifications.md:35` implies that the mails and the dashboard count alike. It
  names the 5-day tolerance.
- Records already in a database: a shell snippet for the user to run on production. Do not run
  it against the dev database.
- NEWS line, because operators see new import errors.
- Done (2026-10-13): `dataexchange/records.py` `create_record` refuses only an *open* lending
  (no `LENT_END_DATE`) of a device without `IS_LENTABLE`. A returned loan ends in an INROOM record
  and stays importable, so a device's lending history can still be imported after it stopped
  being lendable. Four older import tests now mark their open lendings `IS_LENTABLE: yes`.
  Records already in a database, to check on production:
  `./manage.py shell -c "from dlcdb.core.models import Record; print(list(Record.objects.filter(is_active=True, record_type=Record.LENT, lent_end_date__isnull=True, device__is_lentable=False).values_list('device__edv_id', 'device__sap_id', 'person__email')))"`.
  Each hit is a device to mark lendable, so the lending screens list it and can return it.

### Core models and utils

#### 60 — `Device.get_timeline` without dead colours
- `TimelineEvent.bg` and the colour literals (`core/models/device.py`) are never read.
  `licenses/timeline.html` styles the events itself.
- The event descriptions ("Added", "Start date", "Today", "Expiry date", "Termination date") are
  shown untranslated. They become translatable.
- The rule `.timeline …` in `licenses/timeline.html:16` never matches (the wrapper is
  `timeline-row`). Delete it.
- Visible only as translated labels.

#### 61 — `Room.get_inventory_status` returns a status, not CSS
- `core/models/room.py:106-146` returns a status string, a Bootstrap class and the counts. Its
  only reader is `inventory/includes/inventory_status_badge.html`.
- The method returns the status key and the counts. The template picks the badge class and a
  translated label.
- The "FIXME"/danger branch can't be reached with integer counts. It goes.
- No test covers it yet; add one.
- Visible only as translated labels.

#### 62 — Helpers with one consumer leave core - DROPPED

### Core admin and settings

#### 63 — `DEVICE_HIDE_FIELDS` removed
- The setting (`settings/base.py:531`) hides device fields in the admin list and form, and in the
  CSV export. In the admin form it hides only names followed by a comma in the JSON dump of the
  fieldsets, so most configured fields stay visible. The env template calls it unsupported.
- Remove:
  - the setting;
  - its handling in `DeviceAdmin.get_list_display` and `get_fieldsets`, with the `json` import;
  - `visible_columns` in `dataexchange/csv_export.py`;
  - the entry in `core/templates/core/init/env.template` (spelled `DEVIC_HIDE_FIELDS` there).
- NEWS line: the setting is gone.

### Notifications and rooms: named constants (decision 5)

#### 64 — Literals become constants
- The `pc`/`ntb` report prefixes are plain literals in `notifications/reports.py:98-108`.
- The Archibus building code is a local variable in `rooms/views.py:221`, with two commented-out
  alternatives.
- Both become named constants next to their one reader. No behaviour change.
- `UDB_SYNC_FILTERS` stays as it is: its code says on purpose that it is not configurable.

### Inventory

#### 65 — `mark_not_handled_assets_in_csv` tidied
- `inventory/management/commands/mark_not_handled_assets_in_csv.py`:
  - four debug `print`s (:48, :49, :58, :61);
  - commented-out code, one block naming an undefined `_match_msg`;
  - `sys.exit(...)` instead of `CommandError`;
  - a help text with a backslash continuation that embeds spaces.
- The commented `print`s in `inventory/sap.py:41-44`.
- Only change: less output on stdout.

#### 66 — `sap.py` uses `SapList.get_file_name`
- `inventory/sap.py:66` repeats the expression of `SapList.get_file_name`, whose only reader is
  the admin. It calls the method.

#### 67 — The inventory scan workflow moves to `inventory/services.py`
- Was postponed as step 19. `Inventory.inventorize_uuids_for_room`
  (`core/models/inventory.py:268-359`) and its helper `_found_inventory_note` move verbatim to
  `inventory/services.py`, as a plain function.
- Keep `@transaction.atomic` (a rollback test depends on it) and the exceptions the view catches
  (`IllegalTransition`, `RuntimeError`, `ObjectDoesNotExist`).
- Name: not `inventorize_room`, a view in `inventory/views.py` has that name.
- Callers:
  - `inventory/views.py:146` and its comment at :150;
  - `inventory/tests/test_inventory.py`;
  - `core/tests/test_state_write_paths.py` (helper and docstring).
- Afterwards every caller of `update_inventory_note` is in inventory. `core/__init__.py` drops the
  `inventory.utils` exception.
- The "not found" branch writes its note with `" *** "`, while `update_inventory_note` uses
  `"; "`. Moved as it is; aligning them would change stored text.

#### 68 — Fixes found on the move
- The message at the old `inventory.py:283` lacks its `f` prefix and prints `{room_pk}`
  literally.
- A leftover `# print(...)` (old :277).

### Core contract

#### 69 — `TenantAwareModel` moves into core
- Was skipped as step 15. `tenants/abstracts.py` (25 lines) moves into
  `core/models/abstracts.py`, next to `AuditBaseModel`. `core/models/device.py` imports it from
  there, and `tenants/abstracts.py` is deleted.
- The import cycle the file was made for goes away: core then refers to tenants only by the
  string `"tenants.Tenant"`.
- `core/__init__.py` drops the `tenants.abstracts` exception.
- `ImporterList.tenant` and `JournalEntry.tenant` stay as they are. Their fields differ
  (help text, `blank`, verbose name), and the abstract model would add migrations.
- `makemigrations --check` must stay clean. No migration names the module.

#### 70 — The device state buttons move to theme
- Was postponed as step 18. `core/utils/device_methods.py` builds the badge and the action
  buttons, with per-app URLs (`assets:`, `lending:`, `inventory:`, admin). It moves to
  `theme/device_state.py`, next to `theme/lifecycle_display.py`, whose template is already in
  theme.
- `Device.get_state_data` goes. The callers call `get_device_state_data` directly:
  - `core/admin/device_admin.py`: `change_view` and the per-request actions column;
  - `assets/views/devices.py:180`;
  - `inventory/views.py:230`.
- `core/tests/test_device_state_data.py` (487 lines) moves to `theme/tests/`.
- Text references: `core/lifecycle.py:282` and `assets/.../includes/_set_state.html:3`.
- Core then names no frontend URL outside `get_absolute_url` and `obj_link`. No behaviour change.

#### 71 — Contract check before the merge
- The guard grep (*Verification*) lists only `organization.Branding` in `get_contact_email`.
- The docstring of `dlcdb/core/__init__.py` names that one exception.
- The admin-only scan (`git show a266e9a4:PLANS/core-review.md`, *Admin-only members on core
  models*) finds nothing on the core models.
- All gates green, with no warnings.

## Not in this plan

- **`rename_lifecycle_permissions`:** never committed; it is listed in `.git/info/exclude`. A
  local tool for the deployment that ran the old migration 0073. The user deletes the local copy
  once that deployment has run it. Nothing to do on the branch.
- **About 70 untranslated strings in the core admin** (display descriptions, messages, filter and
  fieldset titles): left as they are (decision 11).
- **Contract warnings on a return:** the admin shows them, the frontend doesn't. Left as it is
  (step 32): the admin is being phased out.
- **An admin-managed singleton** for deployment-specific values (report prefixes, building code):
  only if a second deployment needs other values.

## Pitfalls

- `LentRecord.objects` includes INROOM records. A "lent" query must filter `record_type=LENT`.
- The lifecycle `transition_*` functions check state, not permissions.
- Before moving or deleting a template or method: grep `.html`, `.txt` (mail templates) and the
  migrations (DB-stored templates), not only `.py`.
- Template tag libraries are loaded by name.
- Multi-valued relations: a tenant condition split into its own `filter()` can match a different
  related row.
- django-filter never calls a filter method with an empty value.
- Core may not import theme (task 54).
- With warnings as errors, a leak shows up in whichever test runs when it is collected, not in
  the test that caused it.

## Progress

- [x] 0–47 — done (see `a266e9a4` for the full plan)
- [x] 48 — Stale text and docs
- [x] 49 — Licence notices as aware datetimes
- [x] 50 — Files and connections closed
- [x] 51 — Warnings fail the suite
- [x] 52 — `nav` leftovers
- [ ] 53 — The 403 page names the IT address first
- [x] 54 — One picker convention
- [x] 55 — iCal export survives 9999-12-31
- [x] 56 — Two pages ignore the tenant boundary
- ~~57 — `print_sheet` raises its 404 once~~ dropped (2026-10-13)
- [x] 58 — The lending screens ask the record what a save does
- [x] 59 — Importer refuses LENT rows on non-lendable devices
- [x] 60 — `Device.get_timeline` without dead colours
- [ ] 61 — `Room.get_inventory_status` returns a status
- [ ] 62 — Single-consumer helpers leave core
- [ ] 63 — `DEVICE_HIDE_FIELDS` removed
- [ ] 64 — Literals become constants
- [ ] 65 — `mark_not_handled_assets_in_csv` tidied
- [ ] 66 — `sap.py` uses `SapList.get_file_name`
- [ ] 67 — Inventory scan workflow → `inventory/services.py`
- [ ] 68 — Fixes found on the move
- [ ] 69 — `TenantAwareModel` → core
- [ ] 70 — Device state buttons → theme
- [ ] 71 — Contract check before the merge

## Verification (each task)

- `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- `.venv/bin/python manage.py check`
- `.venv/bin/python manage.py makemigrations --check --dry-run`
- `.venv/bin/pytest .`: warnings fail it from task 51 on. Until then, `-W error` shows them.
- The guard grep, after tasks 67, 69 and 71:
  `grep -rn "from dlcdb\.\(assets\|inventory\|lending\|licenses\|theme\|journal\|organization\|dataexchange\|tenants\|notifications\)\|get_model(\"notifications" dlcdb/core/models dlcdb/core/lifecycle.py dlcdb/core/utils`
- `/verify` for visible changes:
  - 53: the 403 page;
  - 54: the pickers;
  - 58: the lend and return messages, in the admin and in the frontend;
  - 61: the inventory badge;
  - 70: the state buttons.

## Merge

- After task 71, from `main`: `git merge --no-ff core-consolidation`. It keeps the atomic
  commits, each revertable on its own, and adds one merge commit that reverts the whole review.
- After the merge this file has no open work left. Delete it.
