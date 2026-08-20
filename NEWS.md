<!--
SPDX-FileCopyrightText: 2024 Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# NEWS

*Latest news top*

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
