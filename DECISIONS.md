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
- **Not tenant-scoped on purpose**, besides those the tenant matrix lists (`tenants/index.html`): the device counts on the room pages and the notification reports, the settings pages and the lending profiles (global, like device types).
- **Django serves `/media/`**, not X-Sendfile (needs a server module; the files are few and small). No `max-age` (a shared PC would show cached files after logout), no CSP on PDFs (it breaks the browser's viewer).
- **The journal is no audit-log package**: auditlog, reversion and simple-history record field changes, not events; error tracking (Sentry) is out of scope. `log()` fails loudly, only the logging handler never breaks its caller; not buffering, a second database, a queue thread or `on_commit`.
- **Polish stays in the classic theme and Bootstrap 5.3**; the `redesign` branches are a quarry only. Colour means state, primary is for actions and links.
- **Related objects open in the same tab**, back via `?next=`; no popup or modal (fragment views plus JS).
- **A form page's header band leaves through the back link, its action bar through Cancel**, on add pages as on detail pages (`theme/includes/_back_link.html`): not "Cancel" twice. Both lead to the same place.
- **A named object links to its page where a reader would go next**: templates through `theme/includes/_object_link.html`, messages through `core/utils/links.py`. Plain inside another link or a stretched row, in print and slips, where leaving drops unsaved input (the lending return flow), and for master data in list columns (it classifies the row; the filterbar filters by it). Not a template tag, not `get_absolute_url` on more core models, not `theme.related` for messages (core may not import theme).
- **A message links its object only when the redirect leaves the object's page**: "… was updated", "tenant created", licences, rooms a rename skipped; messages that land on the object's page or on a form stay plain.
- **The device state card's title is the state, on a solid tile in its colour**: a tinted tile vanishes in dark mode, a "Current state" title over a large badge says nothing. The header's state badge shows only below `lg`, where the card sits below the form.
- **All messages share one panel, a row each; the level shows in the row's icon square** (`list-group-messages`), like a section header's. Not an alert per message (two hints filled the top of every page), not rows tinted in their level's colour (picked against from screenshots: louder, a mixed list turns into stripes), not toasts (hints have to stay put).
- **Attachments are added on the record page, the one write on an otherwise read-only page**: one file with a title per upload, on any record, also long after it was saved. The form swaps into the Attachments card (HTMX), and a saved upload shows as the card's new row, without a message. Not in the decommission form (only at the moment of saving, only for one type), not several files at once named after their files (photo names say nothing).
- **The LOST state is labelled "Missing"**; the key stays `LOST`. Not "Not locatable" (a back-translation of "Nicht auffindbar" that clashes with the "locate" transition), not "Lost" (sounds final, while a device an inventory misses is often found again).
- **HR room names map through a configurable regex**, not per-institute code. HR owns `Room.website`; the sync never creates rooms (typos, "Homeoffice").
- **A pure-Python wheel on GitHub Releases**, with the built docs and the collected static files; no sdist (it can't rebuild the frontend). PyPI later, via trusted publishing.
- **Tests use the plain static storage**, not the manifest storage with a `collectstatic` before the run: that needs a fresh `npm run build`, and a stale manifest fails tests that changed nothing. `theme/tests/test_static_references.py` checks the templates' `{% static %}` paths instead (`dist/` only once built); paths in a form's `Media` stay unchecked.
- **The raw `static/**` stays in the wheel**: the favicon view and the icon picker read it, and without it a stray `collectstatic` would break every page.
- **The version lives in `dlcdb.__version__`**, not in git tags via setuptools-scm (a checkout would lose it). The release logic is two shell scripts, not nox, invoke or a bump tool.
- **`dlcdb_init` writes the instance's `wsgi.py`**: Apache's `SetEnv` doesn't reach `os.environ`.
- **The singleton settings pages share one view function, `theme.settings_page`, and `theme/_settings_base.html`**: the title is the model's `verbose_name`, saving needs the model's change permission. Not a spec dataclass like master data (only the form differs), not django-solo.
- **Without the change permission a settings page shows the same form, disabled**, not the label/value list of Tenants (raw values for choices, people and files).
- **A settings save writes one journal entry naming the changed fields, never their values** (the HR token); not simple-history on the singletons.
- **The settings admins stay registered**, like the tenant admin; the frontend links only the frontend pages.
- **Settings is one page that lists every setting by group, with a search box; each entry opens its own page** (GitHub, Stripe, Linear, Snipe-IT). Not one page holding every field (VS Code, Odoo): the settings are forms, record lists, logs and actions, and one page would need one Save button across models.
- **Each app declares its settings entries in its own `navigation.py`**, like its menu entries; not a central settings app. The settings page is a second rendering of the gear's registry.
- **The search also matches hidden search terms, one translatable string per entry**: words from the entry's page that its label and description lack. Not a search over the settings forms' fields (introspection), unless the terms fall short.
- **Modules still only in the Django admin are listed on the settings page, for staff, with a *Staff* badge**, so they can be found while they move (`PLANS/admin-to-frontend.md`); not "Django admin": the framework's name tells users nothing, the flag that opens them does. Every menu entry into the admin needs the Staff flag besides its permission: without it the entry led to the admin login. Admin actions (assigning a tenant) and deleting an import (the same list as the import history, which the import page links) get no entry; Settings › More reaches them, and the admin itself: the account menu has no entry for it.
- **Bulk import, bulk decommissioning, inventories, the SAP comparison and the room reconcile are under Settings › Data and tools**, not in a Processes menu, which only the admin navbar showed. Master data keeps its own menu: daily work, not configuration.
- **The settings page's *Show all* also lists the entries the user may not open, locked and without a link**, as on the django-toolbox dashboard: users see what exists and whom to ask. Labels and descriptions reveal no data; the menus keep listing only what the user may open. The gear shows for every logged-in user, so staff without a settings permission still reach the admin through *More*.
- **Tenants are under Settings › Users and access**, not Organization: they grant no permissions, but their groups decide who sees which devices.
- **The lending profiles live on Settings › Lending configuration**, with no menu entry or index page of their own; the page needs `view_lendingconfiguration`, the card `view_lendingprofile`. Not "either permission opens the page" (`settings_page` would need a form-less mode).
- **Overdue lendings are always highlighted**: the toggle was a half switch (the due date stayed red).
- **A lending slip lists the regulations by link creation date**: the never-read `LendingProfileRegulation.order` is gone; an order of its own would need the slip to sort by it.
- **The HR token never reaches the browser**: a stored token shows as placeholder dots, an empty field keeps it, "Remove token" clears it. Not a fake value in the field (the save would have to tell it from a typed token). A changed URL needs the token typed again, or the stored one would go to any URL typed in.
- **Admin error mails use Django's plain handler**: a 500 while the mail server is down is accepted; a handler that swallowed mail errors was tried and removed.
- **A person's photo, organizational unit and positions are plain person fields that the HR sync fills**, not HR mirror fields with local overrides. For a synced person HR owns them and clears what it doesn't deliver: the person is read-only, so a kept local value could never be changed. Named `photo`, not `image`, and `organizational_positions`: a bare "position" reads as a place here, "title" as the academic one, "role" as a permission.
- **Positions are master data with a many-to-many**, not HR's joined text (no filter) or a foreign key (HR delivers a list). The explicit through model `PersonPosition` exists only for `PROTECT`.
- **A printed lending slip runs no script and loads nothing from another host** (a Content Security Policy on `print_sheet`); saving a profile refuses `<script>`, `on…=` attributes and `javascript:` with a form error. Not an HTML sanitizer (nh3, bleach): it would mangle template code, and template code can assemble a tag while rendering, which no check of the source sees. Not the Staff flag back on these pages.
- **A unit or position that a person holds can't be deleted**, deactivated persons included: `PROTECT`, not a check in the delete view, which the admin and the shell would skip.
- **Units and positions live on Settings › Organization** (formerly Branding) as cards, like the lending profiles: no entries or index pages of their own, so the settings page doesn't grow; every entry listed, no paging. The page's cards start closed, with a table of contents; any form error opens all of them.

- **Users, groups and permissions are managed in the frontend; only DLCDB's own permissions are offered**: those its code checks, collected from the view decorator (which records them), the menu entries, the lifecycle and `accounts.permissions.CHECKED_IN_VIEWS`; a guard test names any other permission the code checks. Not a codename prefix (Django's view/add/change/delete names are fixed), not a hand-written list of about 80 with labels, not all 230 with a search as in the admin.
- **Permission labels are derived, never Django's `Permission.name`**: model and action, the lifecycle's labels for transitions (listed under *Device*, where the moves are made), a custom permission's menu entry; help lines name the menu entries. The models follow the app's menus (*Menu*, *Master data*, *Settings › …*), those no menu entry needs last, under *Other*.
- **Add, change and delete grant the model's view permission along**, when a group is saved: Django derives no view from change.
- ***New group* is the group page without a group**: one `GroupForm`, as Django's create and update views share one form; not a second form with a profile radio. The tenants are ticks saved with Save; the tenant matrix keeps its instant toggles.
- **A group profile's button ticks its permissions in the browser**, and Save keeps them like any tick; the group doesn't remember the profile, so no model, no migration, and ticked again after an update, a profile adds what is new. Named "group profile": "role" is no DLCDB concept, "profile" alone means lending profiles. Not default groups by migration or `post_migrate` (Wagtail): forced onto existing installations; not a management command.
- **Permissions are checkboxes with help lines, members the dual-pane widget** (`theme.widgets.FilteredSelectMultipleWidget`): its panes are native selects, so permissions would get their help only as tooltips.
- **The Staff and Superuser flags and per-user permissions stay out of the frontend**: badges only; the admin, LDAP and `createsuperuser` set the flags. The admin's user and group screens stay registered.
- **A group's members need the user permissions besides the group's**: shown with `view_customuser`, changed with `change_customuser`. Only a superuser deactivates a superuser or sets their password: no one locks out or takes over the operators.
- **Passwords are set by an administrator, without mail**: an initial one on *New user* or none (LDAP), a new one on the user page. Not reset links.
- **User and group changes are journaled**, naming what changed (never a password), not with simple-history; the tenant ticks keep the tenant's history.
- **The docs list no permissions**: the group pages are the reference, so nothing drifts from the code.
- **A fresh instance says what it lacks**: no tenants, no groups and a tenant no group sees get a hint on every page, for whoever may fix them (`theme.context_processors.hints`); the first two also explain the user's own "no tenant" hint, which then stays away. Not "a group without tenant": a group that only grants permissions (*Administration*) rightly has none, its members see devices through their other groups.

## Pitfalls

- Tenant choices come from `request.tenants`, never `Tenant.objects.all()` (leaks names); joins over multi-valued relations need `distinct()`.
- A re-scan appends an INROOM record even in the same room: count devices, not records.
- `Link.display_url` and the SAP result URL build media URLs by hand.
- `request.htmx.current_url_abs_path` is None behind the TLS proxy; `next` must survive a form's POST.
- The DB-stored slip templates include `lent_sheet.html`: a change there reaches every lending profile.
- With warnings as errors, a leaked file or connection fails whichever test runs at garbage collection.
- Splitting a translated sentence around a link changes its msgid: split only where the word order allows (`rooms/includes/_changes.html`).
- A namespace with several menu entries lights up all of them: each needs `active_url_names`.
- The settings pages need no Staff flag: `change_lendingprofile` writes template code that can still read and print what the record reaches, `record.user.password` included (it runs no script). Administrators only, as the docs say.
- `capfirst()` keeps a lazy string lazy: render journal text inside `translation.override(None)`.
- "Sync now" only queues: without the task runner nothing runs, and while a periodic run holds the lock the manual one is dropped.
- `_field.html` escapes help texts: frontend help texts are plain text.
- A translation used inside an HTML attribute (`placeholder="{% translate … %}"`, `_("…")` passed to an include) is not escaped: translated literals count as safe. A straight double quote in the German text ends the attribute; use „…“.
- A link inside a stretched-link area can't be clicked; `_object_link.html` passes the current request as `next`, which is wrong for a fragment with a URL of its own.
- The HR sync finds units and positions by name: a local rename of one it fills brings the old name back with its next run.
- A renamed person or record field empties the DB-stored slip templates that use it, silently: NEWS has to name it.

- `htmx_permission_required` records its permissions only once the views are imported: the collector imports the URLconf first. Look permissions up by app label and codename together: proxy models (`lentrecord`, `accounts.Group` beside `auth.Group`) and the legacy `dlcdb` label repeat codenames.
- A group's form keeps what it doesn't show: the permissions DLCDB doesn't check and the deactivated members. LDAP sets a mirrored group's members and finds it by name, so both are read-only; `AUTH_LDAP_MIRROR_GROUPS` may also be `True`.
- No locking oneself out: no deactivating oneself, no removing `accounts.change_group` from, leaving or deleting one's only group that grants it.
- `get_all_permissions()` is empty for a deactivated user, and `has_perm` caches per user object: fetch the user again after changing a group.
- Django's radio and checkbox lists put the widget's class on their wrapper too: render them through `theme/includes/_choice_field.html`.

## Open follow-ups

- Tenants: `Device.tenant` and `ImporterList.tenant` NOT NULL (then drop the hints and the assign action); `created_by` on `AuditBaseModel`; create the LDAP mirror groups on `post_migrate`.
- Journal: phase out the legacy logs (`UdbSyncRun` still holds the HR sync's missing-room notes; the `ImporterList`/`RemoverList` messages); a per-object journal on detail pages; journal lifecycle transitions, inventory notes and logins; log the silent handlers in `base_admin.get_queryset`, `verify_lendings` and `notifications/tasks.py`.
- The similar-name lists need only `add_*`, so names can be walked by prefix: without `view_*`, list nothing.
- Related links: duplicate check on renames, a merge tool, links on read-only pages, `next` on every detail link (dashboard search, room and person pages, messages).
- Links: the staff-only device admin link on the inventorize room page (`inventorize_room_detail.html`, where leaving drops the scan); named objects on the inventory screens (their rows are duplicated in `inventorize.js`); the device on the notifications list; the import summary's "saved log"; `obj_link` checks no permission (the room in a relocate message can lead to a 403).
- Records: removing an attachment in the frontend (still the admin's attachment list); a link from the device page straight to its current record.
- Lists: the tenant sort is offered to single-tenant users; a tenant column exists only on devices; the lending list runs an extra COUNT.
- UI: HTMX fragments still compute the hints; charts have no table view; German plurals ("Gerät nach Status", "Geräten").
- Re-check the `_cards.scss` Sass 1.77 workaround with the current sass; the `map_room_number` docstring still shows the narrow CSL regex.
- Data: should a re-scan in the same room write nothing; delete `rename_lifecycle_permissions` once migration 0073 has run; check production for open LENT records on non-lentable devices; the main building's Archibus `bl_id` → "G".
- Smaller: `/` focuses the search, a count badge on "More", "Add '<text>'" in TomSelect, + in the person picker, ESLint for `theme.js` and `filterbar.js`.
- Settings: a Bootstrap template for `ClearableFileInput` (Branding's file fields); a run page that retires the `UdbSyncRun` admin; unregister the settings admins; try the HR room rule on a sample.
- Publish on PyPI.
- Persons: a DLCDB field for the contract end, which lending, notifications and smallstuff read from `udb_contract_planned_checkout`; the contract type as master data; a phone number; positions and photo in the bulk import and the lending CSV export, unit and positions in the API; delete the photo files of hard-deleted persons (a merged duplicate's, say); let users set what HR leaves empty on a synced person.
- Users and groups: the admin's user form lets anyone with `change_customuser` tick *Superuser* (make the flags and `user_permissions` read-only there for non-superusers); direct per-user permissions are invisible in the frontend; reset links by mail and a password change page in DLCDB's look for the account menu; hard-deleting a user is still admin-only.
