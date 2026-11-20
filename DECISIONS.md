<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Decisions

Decisions someone might otherwise revisit, with the alternatives turned down; pitfalls the code doesn't show; open follow-ups. Nothing the code, a comment or the docs already show. A decision that reverses a bullet replaces it.

## Decisions

- **Business thresholds are constants next to their one reader**, not settings: no deployment tunes them. An admin-managed singleton only once a second deployment needs other values.
- **The admin gets no new code paths.** Lending slips print only from the tenant-scoped lending screen, and the record admins offer no "Add": the old admin paths let a user print other tenants' slips, or recover a removed device with just `add_*record`.
- **Tenants grant no permissions; visibility comes only from `Tenant.groups`, with no superuser exception.** Not django-guardian/rules, django-organizations or django-tenants, not a bypass permission, a super-tenant flag or a session "current tenant". Should "all tenants" be needed: one line in `get_user_tenants`.
- **Empty tenants are hard-deleted**, not soft-deleted: an UPDATE bypasses PROTECT, so a "deleted" tenant would hide its devices.
- **Not tenant-scoped on purpose**, besides those in `docs/guides/berechtigungen.md`: the device counts on the room pages and the notification reports, the settings pages and the lending profiles (global, like device types).
- **Django serves `/media/`**, not X-Sendfile (needs a server module; the files are few and small). No `max-age` (a shared PC would show cached files after logout), no CSP on PDFs (it breaks the browser's viewer).
- **The journal is no audit-log package**: auditlog, reversion and simple-history record field changes, not events; error tracking (Sentry) is out of scope. `log()` fails loudly, only the logging handler never breaks its caller; not buffering, a second database, a queue thread or `on_commit`.
- **Polish stays in the classic theme and Bootstrap 5.3**; the `redesign` branches are a quarry only. Colour means state, primary is for actions and links.
- **Related objects open in the same tab**, back via `?next=`; no popup or modal (fragment views plus JS).
- **A named object links to its page where a reader would go next**: templates through `theme/includes/_object_link.html`, messages through `core/utils/links.py`. Plain inside another link or a stretched row, in print and slips, where leaving drops unsaved input (the lending return flow), and for master data in list columns (it classifies the row; the filterbar filters by it). Not a template tag, not `get_absolute_url` on more core models, not `theme.related` for messages (core may not import theme).
- **A message links its object only when the redirect leaves the object's page**: "… was updated", "tenant created", licences, rooms a rename skipped; messages that land on the object's page or on a form stay plain.
- **The device state card's title is the state, on a solid tile in its colour**: a tinted tile vanishes in dark mode, a "Current state" title over a large badge says nothing. The header's state badge shows only below `lg`, where the card sits below the form.
- **The LOST state is labelled "Missing"**; the key stays `LOST`. Not "Not locatable" (a back-translation of "Nicht auffindbar" that clashes with the "locate" transition), not "Lost" (sounds final, while a device an inventory misses is often found again).
- **HR room names map through a configurable regex**, not per-institute code. HR owns `Room.website`; the sync never creates rooms (typos, "Homeoffice").
- **A pure-Python wheel on GitHub Releases**, with the built docs and the collected static files; no sdist (it can't rebuild the frontend). PyPI later, via trusted publishing.
- **The raw `static/**` stays in the wheel**: the favicon view and the icon picker read it, and without it a stray `collectstatic` would break every page.
- **The version lives in `dlcdb.__version__`**, not in git tags via setuptools-scm (a checkout would lose it). The release logic is two shell scripts, not nox, invoke or a bump tool.
- **`dlcdb_init` writes the instance's `wsgi.py`**: Apache's `SetEnv` doesn't reach `os.environ`.
- **The singleton settings pages share one view function, `theme.settings_page`, and `theme/_settings_base.html`**: the title is the model's `verbose_name`, saving needs the model's change permission. Not a spec dataclass like master data (only the form differs), not django-solo.
- **Without the change permission a settings page shows the same form, disabled**, not the label/value list of Tenants (raw values for choices, people and files).
- **A settings save writes one journal entry naming the changed fields, never their values** (the HR token); not simple-history on the singletons.
- **The settings admins stay registered**, like the tenant admin; the frontend links only the frontend pages.
- **The lending profiles live on Settings › Lending configuration**, with no menu entry or index page of their own; the page needs `view_lendingconfiguration`, the card `view_lendingprofile`. Not "either permission opens the page" (`settings_page` would need a form-less mode).
- **Overdue lendings are always highlighted**: the toggle was a half switch (the due date stayed red).
- **A lending slip lists the regulations by link creation date**: the never-read `LendingProfileRegulation.order` is gone; an order of its own would need the slip to sort by it.
- **The HR token never reaches the browser**: a stored token shows as placeholder dots, an empty field keeps it, "Remove token" clears it. Not a fake value in the field (the save would have to tell it from a typed token).
- **Admin error mails use Django's plain handler**: a 500 while the mail server is down is accepted; a handler that swallowed mail errors was tried and removed.
- **A person's photo, organizational unit and positions are plain person fields that the HR sync fills**, not HR mirror fields with local overrides. For a synced person HR owns them and clears what it doesn't deliver: the person is read-only, so a kept local value could never be changed. Named `photo`, not `image`, and `organizational_positions`: a bare "position" reads as a place here, "title" as the academic one, "role" as a permission.
- **Positions are master data with a many-to-many**, not HR's joined text (no filter) or a foreign key (HR delivers a list). The explicit through model `PersonPosition` exists only for `PROTECT`.
- **A printed lending slip runs no script and loads nothing from another host** (a Content Security Policy on `print_sheet`); saving a profile refuses `<script>`, `on…=` attributes and `javascript:` with a form error. Not an HTML sanitizer (nh3, bleach): it would mangle template code, and template code can assemble a tag while rendering, which no check of the source sees. Not the Staff flag back on these pages.
- **A unit or position that a person holds can't be deleted**, deactivated persons included: `PROTECT`, not a check in the delete view, which the admin and the shell would skip.
- **Units and positions live on Settings › Organization** (formerly Branding) as cards, like the lending profiles: no menu entries or index pages, so the settings menu doesn't grow; every entry listed, no paging. The page's cards start closed, with a table of contents; any form error opens all of them.

## Pitfalls

- Tenant choices come from `request.tenants`, never `Tenant.objects.all()` (leaks names); joins over multi-valued relations need `distinct()`.
- A re-scan appends an INROOM record even in the same room: count devices, not records.
- `Link.display_url` and the SAP result URL build media URLs by hand.
- `request.htmx.current_url_abs_path` is None behind the TLS proxy; `next` must survive a form's POST.
- The DB-stored slip templates include `lent_sheet.html`: a change there reaches every lending profile.
- With warnings as errors, a leaked file or connection fails whichever test runs at garbage collection.
- Splitting a translated sentence around a link changes its msgid: split only where the word order allows (`rooms/includes/_changes.html`).
- A namespace with several menu entries lights up all of them: each needs `active_url_names`.
- The settings pages need no Staff flag: `change_lendingprofile` writes template code that can still read and print what the record reaches, `record.user.password` included (it runs no script), `change_udbsyncconfiguration` sends the HR token to any URL. Administrators only, as the docs say.
- `capfirst()` keeps a lazy string lazy: render journal text inside `translation.override(None)`.
- "Sync now" only queues: without the task runner nothing runs, and while a periodic run holds the lock the manual one is dropped.
- `_field.html` escapes help texts: frontend help texts are plain text.
- A link inside a stretched-link area can't be clicked; `_object_link.html` passes the current request as `next`, which is wrong for a fragment with a URL of its own.
- The HR sync finds units and positions by name: a local rename of one it fills brings the old name back with its next run.
- A renamed person or record field empties the DB-stored slip templates that use it, silently: NEWS has to name it.

## Open follow-ups

- Tenants: `Device.tenant` and `ImporterList.tenant` NOT NULL (then drop the hints and the assign action); `created_by` on `AuditBaseModel`; create the LDAP mirror groups on `post_migrate`.
- Journal: phase out the legacy logs (`UdbSyncRun` still holds the HR sync's missing-room notes; the `ImporterList`/`RemoverList` messages); a per-object journal on detail pages; journal lifecycle transitions, inventory notes and logins; log the silent handlers in `base_admin.get_queryset`, `verify_lendings` and `notifications/tasks.py`.
- The similar-name lists need only `add_*`, so names can be walked by prefix: without `view_*`, list nothing.
- Related links: duplicate check on renames, a merge tool, links on read-only pages, `next` on every detail link (dashboard search, room and person pages, messages).
- Links: the staff-only device admin link on the inventorize room page (`inventorize_room_detail.html`, where leaving drops the scan); named objects on the inventory screens (their rows are duplicated in `inventorize.js`); the device on the notifications list; the import summary's "saved log"; `obj_link` checks no permission (the room in a relocate message can lead to a 403).
- Lists: the tenant sort is offered to single-tenant users; a tenant column exists only on devices; the lending list runs an extra COUNT.
- UI: HTMX fragments still compute the hints; charts have no table view; German plurals ("Gerät nach Status", "Geräten").
- Re-check the `_cards.scss` Sass 1.77 workaround with the current sass; the `map_room_number` docstring still shows the narrow CSL regex.
- Data: should a re-scan in the same room write nothing; delete `rename_lifecycle_permissions` once migration 0073 has run; check production for open LENT records on non-lentable devices; the main building's Archibus `bl_id` → "G".
- Smaller: `/` focuses the search, a count badge on "More", "Add '<text>'" in TomSelect, + in the person picker, field history for tenants, ESLint for `theme.js` and `filterbar.js`.
- Settings: a Bootstrap template for `ClearableFileInput` (Branding's file fields); a run page that retires the `UdbSyncRun` admin; unregister the settings admins; try the HR room rule on a sample.
- Publish on PyPI.
- Persons: a DLCDB field for the contract end, which lending, notifications and smallstuff read from `udb_contract_planned_checkout`; the contract type as master data; a phone number; positions and photo in the bulk import and the lending CSV export, unit and positions in the API; delete replaced or cleared photo files and those of hard-deleted persons; let users set what HR leaves empty on a synced person.
