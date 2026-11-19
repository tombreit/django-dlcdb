<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Settings pages: Branding, lending, licence and HR sync configuration, and lending profiles in the frontend

**Status:** batch 3 done (the Lending configuration page), branch `more-frontend-settings-modules`, 2026-11-19. This is a living document.

## Why

Of the entries in the Settings (gear) menu, Tenants and Journal have frontend pages. Five entries still open the Django admin, which needs the staff flag and looks different:

- Branding
- Lending configuration
- Lending profiles
- Licenses configuration
- HR API sync configuration

Goal: each entry gets a frontend page in the app that owns its model, aligned with Tenants and master data, with as little code as possible. The admin stays registered, as it did for Tenants.

## What they have in common

- **Four singletons.** Branding and the lending, licences and HR sync configurations are `SingletonBaseModel`s (`core/models/abstracts.py`):
  - one row, read everywhere through `load()` (`get_or_create(pk=1)`);
  - global: no tenant;
  - no audit fields and no history.

  So each page is one ModelForm on that row. The view permission shows the page, the change permission saves it. There is no add and no delete.
- **Lending profiles are the exception:**
  - one profile per device type;
  - simple-history;
  - ordered regulations (an admin inline);
  - starter content that is restored when a field is cleared.
- **Instance actions:**
  - The only real one is the HR sync's admin action "Run HR API sync now". It enqueues `dataexchange.tasks.task_import_udb_persons` and checks no permission.
  - The HR config's admin page also links the "HR API Sync Runs" list.
- **Already there and reused:**
  - The page frame: `theme/_detail_base.html`, which provides the header, the `can_change` fork, the form with `_form_action_bar.html`, and the sidebar.
  - The field includes: `_field.html`, `_switch_field.html`, `_non_field_errors.html`, `_readonly_notice.html`.
  - The form helpers: `theme.forms.add_bootstrap_classes`, `theme.widgets.TomSelectMultipleWidget`.
  - Redirects: `theme.navigation.get_redirect_url` and `with_next`.
  - Permissions: `core.utils.htmx.htmx_permission_required` and `missing_permission_message`.
  - Lending profile history: `theme.field_history.build_field_history` with `_field_history.html`.
  - `JournalEntry.objects.log`.
  - The closest precedent: `assets/views/masterdata.py` `_masterdata_detail`, one view that both shows and edits.
- **Missing:** a view helper for singletons, and an `enctype` on `_detail_base.html`'s form (Branding uploads files).

## Decisions taken

1. **One shared view function and one template for the four singletons**: `theme/settings_page.py`. It is a pure function, the same convention as `paginate` and `build_filterbar`. Each app keeps only a ModelForm and a three-line view:

   ```python
   @htmx_permission_required("licenses.view_licensesconfiguration")
   def configuration(request):
       return settings_page(request, LicensesConfigurationForm, icon="bi-bank2")
   ```

   `settings_page(request, form_class, *, icon, template="theme/_settings_base.html", context=None)` does five things:
   - loads `form_class._meta.model.load()`;
   - refuses a POST without the model's change permission (`get_permission_codename`, as the admin does), raising `PermissionDenied(missing_permission_message(...))`;
   - binds `request.POST` and `request.FILES`;
   - on save: writes the journal entry (decision 5), sets the message, and redirects (decision 4);
   - otherwise renders the template with `form`, `title`, `icon`, `can_change`, `next_url` and `form_action`.

   The title is the model's `verbose_name`, so it must read like the menu entry (decision 8). The read-only notice lives in `_settings_base.html`.
2. **Each page lives in the app that owns its model**, under a URL without arguments, because the navbar renders `{% url item.url %}`:

   | Setting | URL name | Path |
   |---|---|---|
   | Branding | `organization:branding` | `/organization/branding/` (new `organization/urls.py`) |
   | Lending configuration | `lending:configuration` | `/lending/configuration/` |
   | Licenses configuration | `licenses:configuration` | `/licenses/configuration/` |
   | HR API sync configuration | `dataexchange:hr_sync` | `/dataexchange/hr-sync/` |
   | Run the HR sync | `dataexchange:hr_sync_run` | `/dataexchange/hr-sync/run/` (POST) |
   | Lending profiles | `lending:profile_index`, `profile_add`, `profile_detail` | `/lending/profiles/…` |

3. **Read-only is the same form with every field disabled and no Save button.** The helper sets `field.disabled`. `_settings_base.html` includes the same fields in `detail_form_fields` and in `detail_readonly`. This way choices, people and files show their names and links, not raw values.
4. **Save returns to the same page, or to `?next=`, with a plain message.** The message stays plain because the redirect lands on the object's own page (DECISIONS.md). Cancel reloads the page. The header's Back link shows only when the page was opened with `?next=`.
5. **A save writes a journal entry naming the changed fields.** The entry lists field labels, never values, because of the HR token. Without it, frontend saves leave no trace: the admin's LogEntry history only sees admin saves.
6. **The admins stay registered**, as for Tenants. Frontend links point to the new pages; admin templates keep their admin links.
7. **Unused fields are dropped, in a batch of their own:**
   - LendingConfiguration's `mandatory_regulations` (with `LendingConfigurationRegulation`) and `lending_preparation_checklist`. Migration 0006 copied both into the profiles, and nothing has read them since.
   - Branding's `licenses_logo` and `organization_logo_white`, which nothing reads.
8. **Labels become translatable on the model.** Branding, LendingConfiguration and UdbSyncConfiguration have English-only, partly German verbose names, help texts and choice labels. In each page's batch they get `gettext_lazy` on the model. That means an AlterField or AlterModelOptions migration, which runs no SQL. The model is the right place because the field history and the admin read the labels from it too. The model's `verbose_name` is the page title, so it takes the menu entry's msgid: `_("Lending configuration")`, `_("HR API sync configuration")`, `_("Branding")`.
9. **The HR token is never sent to the browser.**
   - The field is a `PasswordInput()` without `render_value`.
   - A typed token replaces the stored one; an empty field keeps it (`clean_api_token`).
   - A "Remove token" checkbox below the field clears a stored token.
   - The help text says whether a token is stored.

   The admin's own form, which uses `render_value=True`, stays as it is.
10. **"Run sync now" is a POST view requiring `dataexchange.change_udbsyncconfiguration`.**
    - Its button sits in the page header, outside the settings form, like the journal's "Clean up". It is disabled while the sync is switched off.
    - It enqueues the same huey task as the admin action and returns to the page.
    - The sidebar lists the latest `UdbSyncRun`s (time, status, summary). Each run expands (`<details>`) to its stored notes: changed and failed contracts, and rooms DLCDB lacks. A run with only missing rooms is not journaled, so this is the only place in the frontend that shows them.
    - The card links the HR sync entries in the journal (`journal:index?source=dataexchange.hr_sync`).
    - The admin action "Run HR API sync now" gets `permissions=["change"]`, so the admin and the frontend button need the same permission.
11. **Lending profiles get list, add and edit pages** in `lending/views_profiles.py`, following the `licenses/views_calendar.py` precedent.
    - No delete in the frontend; it stays in the admin.
    - The device type stays editable after creation, as in the admin. The form's uniqueness check refuses a type that already has a profile.
    - The regulation order is the selection order in a TomSelect multi-select. To reorder, remove a regulation and add it again.
    - The "restore the starter content when a field is emptied" logic moves from `LendingProfileAdmin.save_model` into `lending/starter.py`, so both the admin and the frontend call it.
12. **Overdue lendings are always highlighted; the toggle `LendingConfiguration.admin_mark_overdue` is dropped** (user's choice, batch 3).
    - It was a half switch: off, the badge read "Lent" and the sort changed, but the due date stayed red, and the "Overdue" filter, the CSV and the dashboard were unaffected.
    - It fits DECISIONS: business rules are code, not settings, until a deployment needs otherwise.

## Alternatives rejected

- **A `/settings/` app or URL prefix:** it breaks locality of behaviour. The gear menu already is the index.
- **Per-app views without the helper:** that would be four copies of the same ~20 lines: load, `can_change`, POST check, `PermissionDenied`, message, redirect.
- **A spec dataclass like `MasterdataSpec`:** only the form and the change permission differ between the four pages.
- **Read-only as the label/value `<dl>` of Tenants and master data:** it shows raw values for choices, many-to-many fields and files.
- **Form-level `Meta.labels`:** the labels would live in two places, and the field history would keep the old ones.
- **simple-history on the singletons:** four history tables just for "who changed what"; one journal entry per save covers it.
- **A singleton package (django-solo):** `SingletonBaseModel.load()` already does the job.
- **Unregistering the admins:** the user's choice is to keep them, as for Tenants.

## Batch 1: drop the unused configuration fields

- **Lending:**
  - `lending/models.py`: remove `LendingConfiguration.mandatory_regulations`, `lending_preparation_checklist` and the model `LendingConfigurationRegulation`.
  - `lending/admin.py`: remove `RegulationInline` and the `exclude`.
- **Branding:**
  - `organization/models.py`: remove `organization_logo_white` and `licenses_logo`.
  - `organization/admin.py`: remove both from the "Logos" fieldset.
  - `templates/admin/navbar.html:15`: remove the commented-out line that reads the white logo.
- **Lent-record admin:** `core/templates/core/lentrecord/change_list.html:14` reads "Checklist & Lending configuration"; it becomes "Lending configuration".
- **Migrations:** one for `lending` (RemoveField ×2, DeleteModel) and one for `organization` (RemoveField ×2). Migration 0006 uses `apps.get_model`, so it still runs.
- No NEWS line: nothing visible changes.

## Batch 2: the settings frame and the Licences configuration

- **The shared frame:**
  - `theme/settings_page.py`: the helper from decision 1.
  - `theme/templates/theme/_settings_base.html`: extends `_detail_base.html`. The title is the setting's name, the meta line reads "Settings", Back shows only with `?next=`, and it loads `form.media`.
  - `theme/templates/theme/includes/_settings_fields.html`: one `card card-filled` with every visible field. Checkboxes (`field.widget_type == "checkbox"`) render through `_switch_field.html`, all other fields through `_field.html`.
- **The Licences configuration page:**
  - `licenses/forms.py`: `LicensesConfigurationForm` with `default_subscribers` as a `TomSelectMultipleWidget`, listing persons with an email, like `LicenseForm`.
  - `licenses/views.py`: the `configuration` view and its URL.
  - `LicensesConfiguration.default_subscribers` gets `verbose_name=_("Default subscribers")`, with a migration: the label had been derived from the field name, untranslated.
- **Navigation:** the menu entry points to the new page with `active_url_names={"configuration"}`. The "Licenses" main entry gets `active_url_names` for its own pages, otherwise it would light up on the settings page too.
- **Docs:**
  - `docs/guides/lizenzen.md:21`: "Lizenzmodul Konfiguration" becomes *Einstellungen › Lizenzmodul Konfiguration*.
  - `docs/guides/berechtigungen.md`: the row loses *(Admin)*.
- **NEWS:** none. A frontend page for an admin screen is no notable feature (user, 2026-11-19): NEWS gets breaking changes, notable features and settings that are not obvious only.
- **Tests** cover the helper through its first consumer:
  - 403 without the view permission;
  - view-only: the fields are disabled and there is no Save;
  - a POST without the change permission gets 403;
  - saving redirects to the page with a message and writes a journal entry;
  - `?next=` is followed.

## Batch 3: Lending configuration

- **Model** (`LendingConfiguration`), with a migration:
  - `admin_mark_overdue` is dropped (decision 12): the lending list and the admin lent-record list always highlight overdue lendings.
  - The verbose name, the choice labels and the help text become translatable.
- `lending/forms.py`: `LendingConfigurationForm` with the reminder recipients only.
- `lending/views.py`: the `configuration` view and its URL.
- **Navigation:** the entry points to the page; the "Lending" main entry gets `active_url_names`.
- **Docs:** `docs/guides/notifications.md:28` and the row in `berechtigungen.md`.

## Batch 4: Branding

- **The frame:** `_detail_base.html`'s `<form>` gets `{% if form.is_multipart %} enctype="multipart/form-data"{% endif %}`.
- **organization app:**
  - a new `urls.py` with `app_name = "organization"`, included in `dlcdb/urls.py`;
  - `forms.py`: `BrandingForm`;
  - `views.py`: the `branding` view;
  - `organization/branding.html`: extends `_settings_base.html` and groups the fields in cards like the admin's fieldsets: Organization, Address, IT department, Logos and room plan, Documentation.
- **Model:** translatable labels and help texts, with a migration.
- **The sticky hint "No IT department contact email configured in Branding!":** its button links to `organization:branding` instead of the admin (`theme/context_processors.py:321`, `theme/tests/test_hints.py`).
- **Docs:** `docs/guides/erste_schritte.md:11` and the row in `berechtigungen.md`.
- **Tests:** an SVG upload is saved, another extension is refused, and "clear" removes the file.

## Batch 5: HR API sync configuration

- **Model:** translatable labels and help texts, with a migration.
- `dataexchange/forms.py`: `HrSyncConfigurationForm`, with the token and the "Remove token" checkbox as in decision 9.
- `dataexchange/views.py`: the `hr_sync` view and its URL.
- `dataexchange/hr_sync.html`: extends `_settings_base.html` so batch 6 can add the button and the sidebar.
- **Navigation:** the entry points to the page; "Bulk import" gets `active_url_names`.
- **Docs:** the "Konfiguration" section of `docs/betrieb/hr-sync.md:31`.
- **Tests:**
  - an empty token field keeps the stored token, and the token never appears in the HTML;
  - a typed token replaces it, and "Remove token" clears it;
  - a URL with `?` is refused;
  - errors in the room rule show on their field.

## Batch 6: HR sync: run now, latest runs

- **The run view:** `dataexchange/views.py: hr_sync_run`, with `@require_POST` and `htmx_permission_required("dataexchange.change_udbsyncconfiguration")`. It refuses while the sync is off, enqueues `task_import_udb_persons()`, sets a message and redirects to `dataexchange:hr_sync`.
- **`hr_sync.html`:**
  - the button in `object_tools`;
  - a sidebar card "Latest runs" with the last 5 `UdbSyncRun`s, each with its status colour and summary, and its stored notes in a `<details>`;
  - a link to the HR sync entries in the journal.
- **Admin action:** "Run HR API sync now" gets `permissions=["change"]`, because today a user with only the view permission can start it.
- **Docs:** `docs/betrieb/hr-sync.md:55`, starting a sync by hand.
- **Tests:**
  - only the change permission may run it;
  - while the sync is off, nothing is enqueued;
  - the task is enqueued (patched);
  - the runs are listed with their notes;
  - the admin action needs the change permission.

## Batch 7: Lending profiles: list, add, edit

- **`lending/views_profiles.py`:**
  - `profile_index`: a plain table with device type, template ✓, checklist ✓ and the number of regulations, plus an Add button. No filterbar: there are few profiles.
  - `profile_add`: `?device_type=` preselects the type; only device types without a profile are offered.
  - `profile_detail`: like `_masterdata_detail`, with `detail_urls`.
- **`lending/forms.py`: `LendingProfileForm`:**
  - the device type: types without a profile, plus the profile's own;
  - the template and the checklist as monospace textareas;
  - the regulations as a `TomSelectMultipleWidget` over `core.Link`. Its queryset lists the selected ones first, in their stored order.

  Saving writes the `LendingProfileRegulation` rows, with `order` set to each regulation's position in the POST.
- **`lending/starter.py`:** a `restore_empty(profile)` that returns the restored fields. It comes from `LendingProfileAdmin.save_model`; the admin and the views both call it.
- **`lending/lend.html:259`:** "No lending slip template found. Add one?" links to `lending:profile_add?device_type=…&next=…`. If the device type already has a profile with an empty template, it links to that profile's page instead. Update `lending/tests/test_views.py:452`.
- **Navigation:** the entry points to `lending:profile_index`, with `active_url_names`.
- **Docs:** `docs/guides/ausleihe.md:48` and the row in `berechtigungen.md`.
- **NEWS:** extend the line.

## Batch 8: Lending profiles: history

- `profile_detail` shows `build_field_history(profile)` through `_field_history.html`. Long templates show in full (pre-line), as the admin's history helper did.
- This settles half of the DECISIONS follow-up "field history for tenants and lending profiles".

## Batch 9: retire the plan

- Move what still holds into `DECISIONS.md`: decisions 1, 3, 5 and 9, the pitfalls, and "Not tenant-scoped on purpose" for the settings and the lending profiles.
- Tighten the NEWS line, then delete this file.

## Progress

- [x] 0. This plan
- [x] 1. Drop the unused configuration fields
- [x] 2. The settings frame and the Licences configuration
- [x] 3. Lending configuration
- [ ] 4. Branding
- [ ] 5. HR API sync configuration
- [ ] 6. HR sync: run now, latest runs
- [ ] 7. Lending profiles: list, add, edit
- [ ] 8. Lending profiles: history
- [ ] 9. Retire the plan

## Pitfalls

- **Menu highlighting:** a namespace with several menu entries lights up all of them. The "Lending", "Licenses" and "Bulk import" entries need `active_url_names`.
- **Docs link:** pages in the `lending` and `licenses` namespaces get those apps' `nav_focus`, i.e. the Docs link to their guide.
- **`load()` writes:** it creates the row on the first GET.
- **The staff flag no longer gates these settings.**
  - `change_udbsyncconfiguration` lets a user send the HR token to any URL.
  - `change_lendingprofile` lets a user write template code that reads whatever `record` reaches, for example `record.user.password` (the hash).

  `docs/guides/berechtigungen.md` has to say: give these permissions only to administrators.
- **"Run now" only enqueues.**
  - Without the huey consumer, nothing runs.
  - While a periodic run holds the `lock_task` lock, the manual run is dropped; the running one delivers the result.
  - `HUEY["immediate"]` is False, so tests patch the task.
- **Orphaned files:** dropping the two logo fields leaves their files in `media/branding/`.
- **Translations:** label changes need migrations (`makemigrations --check`), and the msgids change; the po files are the maintainer's.
- **Regulations and history:** the lending profile history does not track the regulations; there is no `m2m_fields`.
- **Regulation order:** Django reads a multi-select in the DOM order of its options. TomSelect 2.7 (`updateOriginalInput`) appends the selected `<option>`s in item order, so the POST keeps the selection order. On load, though, TomSelect takes the order of the selected options in the HTML, which Django renders in queryset order. So the form's queryset must list the selected regulations first, in their stored order.
- **Regulation documents:** `core.Link` entries can only be added in the admin, so the regulations select gets no add button.
- **Slip templates:** the DB-stored slip templates load `markdown_extras` by name and include `lent_sheet.html`.

## Questions answered (2026-11-19)

1. **A journal entry on every settings save?** Yes, keep it (decision 5).
2. **Can a stored HR token be removed in the frontend?** Yes, with a "Remove token" checkbox (decision 9).
3. **How do the runs' notes show in the frontend?** Inline: each run in "Latest runs" expands to its stored notes. There is no run page; the `UdbSyncRun` admin stays (decision 10).
4. **Regulation order?** The selection order in the TomSelect multi-select. Not a formset, and not alphabetical (decision 11).
5. **`permissions=["change"]` on the admin action "Run HR API sync now"?** Yes (decision 10, batch 6).
6. **Is a lending profile's device type editable after creation?** Yes, as in the admin (decision 11).

## Open questions

None yet.

## Further ideas

- **HR sync:**
  - try the room number rule on a sample HR room name (`map_room_number`, like the rename preview);
  - show the request URL the sync builds (`build_request_url`);
  - "Test connection" without writing anything.
- **Branding:** preview the uploaded SVGs.
- **Lending profiles:** print a sample slip from the profile page; delete in the frontend.
- **The admins:** unregister them once the pages have proven themselves.

## Verification

- **Each batch:**
  - `ruff check . && ruff format --check .`
  - `DATABASE_URL=sqlite://:memory: .venv/bin/python manage.py check`
  - `DATABASE_URL=sqlite://:memory: .venv/bin/python manage.py makemigrations --check --dry-run`
  - `DATABASE_URL=sqlite://:memory: .venv/bin/pytest .`
- **In the browser** (`/verify` skill):
  - each page as a view-only user and as a user with the change permission, in light and dark mode and at 390px;
  - the Branding upload;
  - the HR "Run sync now" button;
  - the lending profile add flow from the lending page.
