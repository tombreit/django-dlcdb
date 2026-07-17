<!--
SPDX-FileCopyrightText: 2024 Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# ♻ DLCDB

*Device Live Cycle Database*

The DLCDB manages the life cycle of IT assets: a device collects append-only records (*inroom*, *lent*, *lost*, *removed*, …), which gives you the current state and a complete audit trail for free. Built with [Django](https://www.djangoproject.com/), served as a plain server-rendered web app.

⚡Not yet fully translated.⚡

## 🔥 Features

- Record-based device life cycle: a device has exactly one active record at a time; every state change appends a new record — the full history is always preserved
- Web frontend for devices, rooms, persons and master data (device types, manufacturers, suppliers) — no Django admin needed for daily work
- Lending management with printable lending sheets and overdue email reminders
- Inventory/stocktaking mode with QR code scanning (browser camera)
- License and contract management with expiry notifications and ICS calendar feeds
- CSV bulk import with dry-run validation
- Read-only REST API (`/api/v2/`) with OpenAPI schema and Swagger UI
- Email notifications and periodic xlsx reports (subscription-based)
- UDB person/contract synchronization
- Multi-tenancy, optional LDAP authentication, customizable branding

## 👉 Getting started

The DLCDB is a Django project, works with [Python 3.13+](https://www.python.org/downloads/) and [nodejs](https://nodejs.org/en/download/) on Debian Linux.

To get started using the DLCDB, run the following in a virtual python environment (development setup, not to be used in production):

```bash
npm install
npm run build
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

[Detailed setup and installation docs](https://dlcdb.pages.gwdg.de/django-dlcdb/betrieb/setup.html)

## 📖 Documentation

`docs/` or [https://dlcdb.pages.gwdg.de/django-dlcdb/](https://dlcdb.pages.gwdg.de/django-dlcdb/)

## 📡 REST-API

The DLCDB exposes some data via its REST-API:

* [API docs](https://dlcdb.pages.gwdg.de/django-dlcdb/betrieb/api.html)
* Endpoint: `https://fqdn/api/v2/`

## ✅ Tests

```bash
pytest  # or
make tests
```

## 📌 Compatibility

DLCDB supports:

- Python 3.13+
- any Django supported database backends, runs fine with SQLite in production

## ⚖️ License

[EUPL-1.2](https://gitlab.gwdg.de/dlcdb/django-dlcdb/-/blob/main/LICENSE) - The EUPL is a reciprocal (or copyleft) licence, meaning that distributed contributions and improvements (called "derivatives") will be provided back or shared with the licensor and all other users. At the same time (and unlike other copyleft licences like the GPL or AGPL), the EUPL is compatible with most other open reciprocal licences and is interoperable. [Source](https://joinup.ec.europa.eu/collection/eupl/introduction-eupl-licence)
