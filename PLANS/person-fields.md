<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Person fields: photo, positions and organizational unit without an HR system

**Status:** plan, drafted 2026-11-19, not started. Living document: tick *Progress*, log decisions under *Decided on the way*. The last batch moves what still holds into `DECISIONS.md` and deletes this file.

## Why

Some person data exists only as HR mirror fields (`udb_*`) that the HR sync fills. An instance without an HR system cannot set them, although nothing about them is HR-specific: a photo, the positions a person holds, the organizational unit. Goal: person fields that DLCDB owns and a user maintains by hand; when the HR sync is enabled, it fills the same fields. Then the persons list filters by them and the person cards show them.

Hard constraint: no breaking change for production instances (SQLite, pip wheel, `migrate` on update with the task runner stopped).

## Where we start

- `Person` (`dlcdb/core/models/person.py`): DLCDB fields `first_name`, `last_name`, `email`, `organizational_unit` (FK `OrganizationalUnit`), `room`; HR mirror fields `udb_*`.
- `udb_person_image`: ImageField, `upload_to="person_images/"`; the sync writes `{uuid}.jpg` as a 400×300 JPEG (`save_base64img_as_fileimg`) and keeps `udb_person_image_hash` to skip unchanged images.
- `udb_contract_organizational_positions`: CharField, HR's list joined with ", ".
- `udb_contract_organization_unit`: CharField with the name the sync also writes into `organizational_unit` (`OrganizationalUnit.objects.get_or_create(name=…)`). The two hold the same value.
- A person with `udb_person_uuid` is read-only in the frontend (`persons/views.py: person_detail`). The sync overwrites every field it owns on each run, `organizational_unit` and `room` included, and clears them when HR has none; only `email` is backfilled, never overwritten.
- `OrganizationalUnit` has no frontend page (admin only, see `admin-to-frontend.md`): the person form selects a unit but cannot add one.
- Readers of the three fields: `persons/templates/persons/{index,detail}.html`, `theme/includes/_person_list_item.html` (picker card), `smallstuff/includes/person_list_item.html`, `core/admin/person_admin.py`, `dataexchange/udb_sync.py` (`defaults`, `COMPARED_PERSON_FIELDS`), `core/management/commands/anonymize_data.py`.

## Options

### Photo

- **A. Rename in place** (`RenameField udb_person_image → photo`). One migration, a column rename; data and files stay where they are (`upload_to` doesn't change, so `MEDIA_PERMISSIONS` needs nothing). **Recommended.**
- B. A new field plus a copy, keeping `udb_person_image` as the HR mirror with "local beats HR". Two columns that drift apart, more sync logic, a page that must explain which one wins. Worth it only if a synced person's photo should be editable locally.
- C. Keep the column and add a `photo` property. No migration, but no form field either: misses the goal.

### Positions

- **A. Master data and M2M**: `OrganizationalPosition(name)` next to `OrganizationalUnit`, `Person.organizational_positions = ManyToManyField(…)`. A dropdown filter like the unit's, a multi-select in the form, rows that can be renamed or merged. **Recommended**: the filter is the point.
- B. Rename the CharField to `organizational_positions` and keep the joined text. The smallest change, but the list could only search the text; a dropdown would have to split strings.
- C. A FK to one position: HR delivers a list, and joining it would create one row per combination.

### Organizational unit

- Already a DLCDB field. `udb_contract_organization_unit` duplicates it: drop it, after the pre-flight confirms both agree.

## Names

- **`photo` rather than `image`**: it says what it holds (a portrait) and is the common name in directories and HR systems (LDAP `jpegPhoto`, vCard `PHOTO`, Microsoft Graph `photo`, SCIM `photos`); the docs already say "Foto". `image` is just as safe technically (schema.org uses it). Decided: `photo`.
- **`organizational_positions` / `OrganizationalPosition`** pair with `organizational_unit` / `OrganizationalUnit`. A bare `position(s)` reads as a physical location in a device and room database; `title` means the academic title in German (Dr., Prof.); `role` collides with permission roles; `job_title` is the common name for a single value, but HR delivers a list. Related name `persons`, like `Room.persons`.
- Neither name collides with a Django attribute, a manager or a reverse accessor on `Person`.
- `udb_person_image_hash` keeps its name: it is the sync's bookkeeping (a hash of HR's base64), not person data.

## Pitfalls

- **DB-stored lending templates.** `LendingProfile.lent_sheet_template` and `lending_preparation_checklist` are template code in the database. A template using `record.person.udb_person_image` or `…udb_contract_organizational_positions` renders empty after the rename, silently. Pre-flight on every instance, and a NEWS line.
- **UNCHANGED must stay unchanged.** The sync compares `COMPARED_PERSON_FIELDS` through `.values()`; an M2M doesn't fit there (one row per position). Compare the sorted position names separately. A wrong compare journals every person on every run (144 runs a day).
- **M2M writes**: `create(**defaults)` can't take the M2M; `.set()` after the save, inside the per-contract savepoint.
- **The data migration splits on ", "**: a position name containing ", " gets split. The sync rewrites present persons on its next run, so only persons no longer in HR keep a wrong split. The pre-flight lists the distinct strings.
- **Names are the sync's key.** The sync finds units and positions by name. Renaming an HR-named unit or position locally makes the next run create the old name again. Matters once units and positions get frontend pages (batch 9): a help text, or read-only names for rows HR fills.
- **Protected units and positions.** Today deleting a unit clears it on its persons (`on_delete=SET_NULL`), without a word. From batches 3 (positions) and 4 (units) on, `PROTECT` refuses it (`ProtectedError`), in the frontend, the admin and the shell alike. An M2M has no `on_delete`: positions get there only through an explicit through model whose position key is `PROTECT`. Choose the through model in batch 3: switching an auto-created one later needs a `SeparateDatabaseAndState` migration.
- **Deactivated persons protect too.** Django's delete collector uses the base manager, which includes soft-deleted persons, so a unit only deactivated persons hold can't be deleted either, while the card's person count (active persons) shows 0. The refusal counts both.
- **The through model and the duplicate merge.** `_merge_duplicate` (`udb_sync.py`) moves every relation in `Person._meta.related_objects` to the kept person; a through row it moved could break the unique (person, position) pair. The through model's person key gets `related_name="+"`: hidden relations aren't in `related_objects`, so the duplicate's rows go with it, and the sync sets the kept person's positions right after.
- **Claimed persons lose manual values.** A local person the sync claims (by e-mail or name) gets HR's photo, unit and positions, and none where HR has none, as `organizational_unit` does today. A manual photo file stays on disk.
- **Upload size and EXIF.** A phone photo is several MB and may carry GPS EXIF. Uploads go through the sync's Pillow path (thumbnail, RGB, JPEG), which drops EXIF.
- **Files outlive the field.** Django deletes no files: a replaced or cleared photo stays on disk, as do hard-deleted persons' photos. Personal data: see *Further ideas*.
- **New model permissions** (`core.*_organizationalposition`) are in no group after the migration. Choosing positions in the person form needs only `change_person`; managing positions needs the new permissions → `docs/guides/berechtigungen.md`.
- **N+1**: every list that shows positions needs `prefetch_related("organizational_positions")`: persons index, the person pickers (`lending/filters.py`, `assets/views/devices.py`, `smallstuff/filters.py`), dashboard search.
- **Rollback**: every migration reversible (`RenameField` is; the data migration gets a reverse that joins the names again), so the previous wheel runs after `migrate core <previous>`.
- **The admin gets no new code paths** (DECISIONS): rename in the admin only what it reads; photo and positions stay read-only there.

## Not affected (checked)

- REST API: `PersonSerializer` and `PersonViewSet` expose none of the three fields; the generated OpenAPI stays the same.
- Media permissions: keyed by directory, which stays `person_images`.
- Mail templates (`.txt`) and the starter lending template (`lending/migrations/0006`, uses `organizational_unit.name` only).
- The `unique_udb_person_name` constraint and the lending CSV export (`organizational_unit` only).
- SQLite: `RenameField` is a native column rename; the task runner is stopped during `migrate`, so no sync runs against a half-migrated schema.

## Pre-flight (before batch 1, read-only, on every production instance)

```sh
./manage.py shell -c "
from django.db.models import F
from dlcdb.core.models import Person
from dlcdb.lending.models import LendingProfile
for profile in LendingProfile.objects.all():
    for field in ('lent_sheet_template', 'lending_preparation_checklist'):
        if 'udb_' in (getattr(profile, field) or ''):
            print('template uses udb_:', profile.pk, profile, field)
persons = Person.with_softdeleted_objects.exclude(udb_contract_organization_unit='')
print('unit mismatches:', persons.exclude(organizational_unit__name=F('udb_contract_organization_unit')).count())
print(sorted(set(Person.with_softdeleted_objects.values_list('udb_contract_organizational_positions', flat=True))))
"
```

## Batches

One commit each; the user commits in between. Re-check each step against the code before starting it. Checks per batch: `ruff check . && ruff format --check .`, `./manage.py check`, `./manage.py makemigrations --check --dry-run`, `pytest .`, all with `DATABASE_URL=sqlite://:memory:`.

1. **Rename `udb_person_image` to `photo`.** `RenameField`, verbose name `_("Photo")`. Update the readers listed above. No visible change.
2. **Photo on the person form.** `PersonForm` gets `photo`; add and detail views pass `request.FILES` (`_detail_base.html` already sets the multipart enctype); uploads are shrunk like HR images (split `save_base64img_as_fileimg` in `core/utils/helpers.py` into the base64 decode and a shared thumbnail step); the read-only card shows the photo. Synced persons stay read-only. File input rendered like Branding's (`organization/forms.py`). Tests: upload, clear, a non-image refused.
3. **Positions as master data.** `OrganizationalPosition` (like `OrganizationalUnit`: `AuditBaseModel`, unique `name`), `Person.organizational_positions` (M2M, `blank=True`, `related_name="persons"`, `through` a small model with the person key `CASCADE` and `related_name="+"`, the position key `PROTECT`, unique together; see *Pitfalls*). One core migration: create, add, copy (`RunPython`, reversible), remove `udb_contract_organizational_positions`. Sync: `get_or_create` per name, `.set()`, compare sorted names, change text for the history. Form: `TomSelectMultipleWidget` (`theme/widgets.py`). Detail page: positions in the person card, out of the HR sidebar. Admin: the person admin shows positions read-only; no admin for the new model (new UI goes into the frontend, batch 9). smallstuff template.
4. **Drop `udb_contract_organization_unit`; protect units.** If the pre-flight found mismatches, decide first. Readers: HR sidebar, smallstuff template, admin, sync. `Person.organizational_unit` becomes `on_delete=PROTECT`: `on_delete` isn't stored in the database, so the migration runs no SQL. Re-check tests that delete a unit.
5. **Persons list filters** (`persons/filters.py`). `organizational_positions` (ModelChoiceFilter, like the unit); `room` (ModelChoiceFilter over `Room.objects`, like `DeviceFilter.active_record__room`); room number in `search_filter`, not in `Person.search_q` (the pickers share it). Search placeholder. Sorting by room exists. The filterbar dropdown has its own search, so a long room list works.
6. **Person cards.** Positions on the persons index rows, the detail header, the picker card (`theme/includes/_person_list_item.html`) and the dashboard search row; prefetch in each queryset.
7. **Settings › Branding becomes Settings › Organization.** A label, nothing else: `Branding.Meta.verbose_name` (the page title, via `settings_page`; one `AlterModelOptions` migration, no table change), the menu entry (`organization/navigation.py`), the missing-IT-contact hint (`theme/context_processors.py`), docs (`erste_schritte.md`, `notifications.md`, the navigation table in `berechtigungen.md`). Model, URL (`organization:branding`) and permission codenames stay: bookmarks, groups and the admin keep working. The stored permission name stays "Can view branding" (Django doesn't rename existing permissions).
8. **Organization page: collapsible cards and a table of contents.** Each card of `organization/includes/_branding_fields.html` becomes `<details class="card card-filled mb-3">`, like the device form's cards (`assets/devices/includes/_form_fields.html`): a card with a field error is always open, or saving would seem to do nothing. The `detail_sidebar` column, empty on settings pages, gets a list of links to the cards, sticky, only from `lg` up (below it the sidebar sits under the cards). Plain markup in `organization/branding.html`; it moves to `theme` only when a second settings page wants it. Every card starts closed, except one with a field error. So a link must open its card: check whether the browsers in use do that for a fragment inside a `<details>`, otherwise a few lines of page-local JS.
9. **Units and positions on the Organization page.** Like the lending profiles on Lending configuration (`lending/configuration.html`, `lending/views_profiles.py`): `organization/branding.html` gets a `detail_related` block with two cards, each listing its rows with a person count that links the filtered persons list, and an add button. A card shows with the model's view permission (`core.view_organizationalunit`, `core.view_organizationalposition`); add and edit need the model's own permissions; the page itself still needs `organization.view_branding`. Add and edit pages in `organization` (one module for both models, since both are a name only), with the similar-name check (`theme.similar`) and a help text that HR names rows by name. `register_related_pages` in `organization/apps.py` gives the person form's selects their buttons. Delete: only a row no person holds, deactivated persons included; a delete page like the lending profile's, which for a used row says why not (count both) instead of offering the button. Both cards join the table of contents. Ticks "Organisational units" in `admin-to-frontend.md`.
10. **Retire the plan.** NEWS line (incl. "check lending slip templates for `udb_` fields"), `docs/betrieb/hr-sync.md` (which person fields the sync fills), `docs/guides/berechtigungen.md` (unit and position permissions), `DECISIONS.md`, delete this file.

## Open questions

(none)

## Further ideas (not in this plan)

- Contract dates without HR: `udb_contract_planned_checkout` prefills the lending end date, drives `sync_lent_end_date`, the smallstuff person list and "Contract until" on the picker card. A DLCDB field ("leaves on") would give that to instances without HR. Same pattern as here, but notifications and lending read it.
- `udb_contract_contract_type` as master data (employee, guest, student) with a filter.
- A phone number: DLCDB-owned, HR could fill it.
- Import and export: positions and photo in the bulk import's person columns, positions in the lending CSV export.
- API: unit and positions on `PersonSerializer` (additive).
- Delete a replaced or cleared photo file and the photos of hard-deleted persons.
- Let users set what HR leaves empty on a synced person (a photo, say), instead of all read-only.

## Progress

- [ ] Pre-flight on the production instances
- [x] 1. Rename `udb_person_image` to `photo`
- [x] 2. Photo on the person form
- [x] 3. Positions as master data
- [x] 4. Drop `udb_contract_organization_unit`
- [ ] 5. Persons list filters
- [ ] 6. Person cards
- [ ] 7. Settings › Branding becomes Settings › Organization
- [ ] 8. Organization page: collapsible cards and a table of contents
- [ ] 9. Units and positions on the Organization page
- [ ] 10. Retire the plan

## Decided on the way

- 2026-11-19: the field is `photo`, not `image`.
- 2026-11-19: positions are master data (`OrganizationalPosition`) with an M2M on `Person`, not text.
- 2026-11-19: HR clears what it doesn't deliver, for photo, unit and positions alike (as for the unit today): a synced person is read-only, so a kept local value could never be changed.
- 2026-11-19: units and positions are managed in this plan, on Settings › Branding relabelled "Organization", as cards like the lending profiles: no menu entries or index pages of their own, so the settings menu doesn't grow.
- 2026-11-19: a unit or position that any person holds (deactivated ones included) can't be deleted: `PROTECT` on the unit key and on the position key of an explicit through model. Not only a check in the delete view: the admin and the shell would still delete.
- 2026-11-19: positions show on the persons index rows, the detail header, the person picker card and the dashboard search row; not on smallstuff's own card.
- 2026-11-19: the positions filter takes one value, like the unit filter.
- 2026-11-19: the Organization page's cards are collapsible (`<details>`), all closed at first (a card with a field error opens), with a table of contents in the sidebar.
- 2026-11-19: the units and positions cards list every row, however many: no paging, no "show all" link, no page of their own.
- 2026-11-20 (batch 2): the read-only person page gets no photo row: the page header shows the photo already.
- 2026-11-20 (batch 2): `shrink_photo` also turns a photo upright by its EXIF orientation before dropping the EXIF data (a phone photo would otherwise lie on its side); HR photos go through it too.
- 2026-11-20 (batch 2): no tests of what Django does itself (refusing a non-image, "Clear"). The form round-trip guard (`core/tests/test_form_round_trip.py`) leaves file inputs out of its payload, as a browser does, and its person has a stored photo.
- 2026-11-20 (batch 3): the through model is `PersonPosition`; both its keys are hidden (`related_name="+"`), the position key too, as nothing reads it. The sync test of the duplicate merge gives both persons the same position: with a visible person key the merge fails on the unique pair (checked).
- 2026-11-20 (batch 3): the data copy drops blank and repeated names and keeps HR's order; going back joins them again. A name containing ", " is split (see *Pitfalls*).
- 2026-11-20 (batch 3): the form round-trip guard compares many-to-many fields too, and its person holds a position.
- 2026-11-20 (batch 4): without the pre-flight's answer the migration keeps what it can: a person with the HR unit name but no unit gets the unit by name; where both are set, the unit stays (the pages show that one). Going back writes the unit names of HR-linked persons into the text again.
