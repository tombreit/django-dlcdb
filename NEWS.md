<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# NEWS

*Latest news top*

* Pip installation: each GitHub release carries a wheel with frontend assets, docs and collected static files; `python -m dlcdb dlcdb_init` creates the instance directory's `.env` (with a fresh secret key), `manage.py`, `wsgi.py` and a README, so the instance runs with `./manage.py` like any Django project
* Dashboard: a Journal tile counts the critical, error and warning entries of the last 30 days
* SQLite runs in WAL mode with an immediate write lock, a 20 s busy timeout and larger caches; deployments stop the task runner during `migrate`, and the huey container waits until `serve` has applied all migrations; the task runner writes a compacted, copyable `data/db/db.sqlite3.snapshot` every night at 00:30 UTC for file-based backups
* Journal: a cleanup page (Settings › Journal › Clean up) removes repeated HR sync and error entries, keeping the first and the latest, and entries older than a chosen age
* Journal: every HR sync run that created, changed or failed something gets a journal entry; unchanged runs do not; the stored runs are copied over
* Journal: deactivating and activating persons, devices, rooms and device types, device note changes on licences and deactivated users are journaled; earlier ones are copied from the admin history
* Journal: every sent notification mail and every newly failed one gets a journal entry; existing sent and failed mails are copied over
* Journal: every bulk decommissioning run gets a journal entry naming who ran it; existing decommissioning logs are copied over
* Journal: every stored import outcome (written, failed, dry run with bad rows) gets a journal entry naming who ran it; existing import logs are copied over
* Journal: logged warnings and errors, unhandled exceptions in views and failed background tasks show up in the journal; a repeat at most once per hour
* Journal: new page Settings › Journal, one read-only list of logged events, filterable by source, event, minimum level and text; needs `journal.view_journalentry`
* Person detail page lists the person's lendings, licences and smallstuff, current and past, with links to device, lending and record
* Tenants: new page Settings › Tenants to manage tenants and which groups see them, with history
* Tenants: users see the devices of all tenants their groups belong to, superusers too: give their group access to every tenant
* Every device and import needs a tenant; a hint leads to assigning the existing ones
* Devices can be copied in the frontend via "Save as new" on the detail page
* Import history in the frontend: a read-only list of all device imports with status and log; the device list can be filtered by import file
* Frontend permissions consolidated onto Django's default `view`/`add`/`change` permissions of the model each view touches. The license module now needs `core.view_licencerecord`; assign this permission to the groups that should keep access (likewise `smallstuff.view_assignedthing` and `smallstuff.add_assignedthing` for Kleinkram)
* Device state transitions are gated by dedicated `core.transition_can_*_device` permissions (Core | record); migration 0073 grants them to every group and user that held the corresponding `add_*record`/`change_lentrecord` permission, which no longer control transitions. `transition_can_restore_device` and `transition_can_recover_device` are granted to nobody
* Device search now also matches the device note
* The compiled German catalog (`django.mo`) is committed, so deployments no longer need to run `compilemessages`
* Global search on the dashboard: one term across devices, persons, rooms, lendings, licenses and smallstuff, linking to the frontend detail views; the term lives in the URL, so a search is shareable and bookmarkable
* Lending: "Return" is its own screen now, with the return date prefilled; the lending edit form can no longer end a lending
* New device attribute: "URL", an optional link to e.g. a device's own management web interface
* The device list and the lendings list frontend apps can now be exported as CSV, covering every device the active search and filters match (not just the current page).
* The device CSV export changed shape: the machine and backup encryption keys are no longer exported, nor are the qrcode path, internal ids. Timestamps are rendered in local time instead of UTC.
* All notifications (device events and periodic record reports) are now managed as *Subscriptions* in the `notifications` app; existing notification rules must be re-created in the admin. The `reporting` app only generates the report artifacts (xlsx)
* Renamed `.env` variables: `REPORTING_NOTIFY_OVERDUE_LENDERS` → `NOTIFICATIONS_NOTIFY_OVERDUE_LENDERS`, `REPORTING_NOTIFY_OVERDUE_LENDERS_TO_IT` → `NOTIFICATIONS_NOTIFY_OVERDUE_LENDERS_TO_IT`
* Dedicated `dataexchange` app with a rewritten CSV-based importer that now also supports `LENT` records
* New license management module
* Documentation served via WhiteNoise from `/docs/`, no custom webserver configs necessary for the `/docs/` endpoint
* Lending: TOS or regulations could be added to the lent sheet
* New room attribute: "website", an optional link to external space management systems
* Some tests!
* (WIP) Speed up inventorization mode by more efficient database queries
* Inventorization mode with a sleek htmx-powered interface, device listings, ability to request a room plan (if available, see `Organization > Branding`)
* Bulk relocate admin action for devices could now set new tenant and/or new device type
* Staticfiles now served via whitenoise from the Django app itself. Separate webserver configs (nginx, apache etc.) are not needed anymore for /static
* (WIP) Importer now handles record creation for more than INROOM records and could be triggered by management command `import_csv` or via bulk importer admin interface
* Device types and rooms with notes and has_note badge display in admin listings and dasboard buttons
* DLDB startup now possible without an `.env` file.
* Branding refactored to be handled in Django admin instead of the previous .env file
* Docs now on gitlab pages: https://dlcdb.pages.gwdg.de/django-dlcdb/
* Requirements now build from `setup.cfg`. See `docs/betrieb/setup.rst`
* ⚡ Refactored some parts of DLCDB. Start your instance from a clean checkout!
* ⚡ Defaults to `dev` requirements (`requirements.txt`). Use a dedicated requirements file for production, e.g. `requirements/requirement-prod-ldap.txt`)
* New mandatory `.env` variable: `DJANGO_DEBUG`
* Some setup hints implemented via Django messages framework, warns for:
  * Devices without record
  * No `is_auto_return_room` room
  * No  `is_external` room
* Enable/disable usage of LDAP authentification via new `.env` variable `AUTH_LDAP`
