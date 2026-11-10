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
- **Not tenant-scoped on purpose**, besides those in `docs/guides/berechtigungen.md`: the device counts on the room pages and the notification reports.
- **Django serves `/media/`**, not X-Sendfile (needs a server module; the files are few and small). No `max-age` (a shared PC would show cached files after logout), no CSP on PDFs (it breaks the browser's viewer).
- **The journal is no audit-log package**: auditlog, reversion and simple-history record field changes, not events; error tracking (Sentry) is out of scope. `log()` fails loudly, only the logging handler never breaks its caller; not buffering, a second database, a queue thread or `on_commit`.
- **Polish stays in the classic theme and Bootstrap 5.3**; the `redesign` branches are a quarry only. Colour means state, primary is for actions and links.
- **Related objects open in the same tab**, back via `?next=`; no popup or modal (fragment views plus JS).
- **HR room names map through a configurable regex**, not per-institute code. HR owns `Room.website`; the sync never creates rooms (typos, "Homeoffice").
- **A pure-Python wheel on GitHub Releases**, with the built docs and the collected static files; no sdist (it can't rebuild the frontend). PyPI later, via trusted publishing.
- **The raw `static/**` stays in the wheel**: the favicon view and the icon picker read it, and without it a stray `collectstatic` would break every page.
- **The version lives in `dlcdb.__version__`**, not in git tags via setuptools-scm (a checkout would lose it). The release logic is two shell scripts, not nox, invoke or a bump tool.
- **`dlcdb_init` writes the instance's `wsgi.py`**: Apache's `SetEnv` doesn't reach `os.environ`.
- **Admin error mails use Django's plain handler**: a 500 while the mail server is down is accepted; a handler that swallowed mail errors was tried and removed.

## Pitfalls

- Tenant choices come from `request.tenants`, never `Tenant.objects.all()` (leaks names); joins over multi-valued relations need `distinct()`.
- A re-scan appends an INROOM record even in the same room: count devices, not records.
- `Link.display_url` and the SAP result URL build media URLs by hand.
- `request.htmx.current_url_abs_path` is None behind the TLS proxy; `next` must survive a form's POST.
- The DB-stored slip templates include `lent_sheet.html`: a change there reaches every lending profile.
- With warnings as errors, a leaked file or connection fails whichever test runs at garbage collection.

## Open follow-ups

- Tenants: `Device.tenant` and `ImporterList.tenant` NOT NULL (then drop the hints and the assign action); `created_by` on `AuditBaseModel`; create the LDAP mirror groups on `post_migrate`.
- Journal: phase out the legacy logs (`UdbSyncRun` still holds the HR sync's missing-room notes; the `ImporterList`/`RemoverList` messages); a per-object journal on detail pages; journal lifecycle transitions, inventory notes and logins; log the silent handlers in `base_admin.get_queryset`, `verify_lendings` and `notifications/tasks.py`.
- The similar-name lists need only `add_*`, so names can be walked by prefix: without `view_*`, list nothing.
- Related links: duplicate check on renames, a merge tool, links on read-only pages, `next` on every detail link (dashboard search, room and person pages).
- Lists: the tenant sort is offered to single-tenant users; a tenant column exists only on devices; the lending list runs an extra COUNT.
- UI: the state badge appears twice on the device page; HTMX fragments still compute the hints; charts have no table view; German plurals ("Gerät nach Status", "Geräten").
- Re-check the `_cards.scss` Sass 1.77 workaround with the current sass; the `map_room_number` docstring and help text still show the narrow CSL regex.
- Data: should a re-scan in the same room write nothing; delete `rename_lifecycle_permissions` once migration 0073 has run; check production for open LENT records on non-lentable devices; the main building's Archibus `bl_id` → "G".
- Smaller: `/` focuses the search, a count badge on "More", "Add '<text>'" in TomSelect, + in the person picker, field history for tenants and lending profiles, ESLint for `theme.js` and `filterbar.js`.
- Publish on PyPI.
