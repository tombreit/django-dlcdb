<!--
SPDX-FileCopyrightText: 2024 Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# ♻ DLCDB

*Device Life Cycle Database*

The DLCDB manages the life cycle of IT assets: a device collects append-only records (*inroom*, *lent*, *lost*, *removed*, …), which gives you the current state and a complete audit trail for free. Built with [Django](https://www.djangoproject.com/), served as a plain server-rendered web app.

## 🔥 Features

- Record-based device life cycle: a device has exactly one active record at a time; every state change appends a new record — the full history is always preserved
- Web frontend for devices, rooms, persons and master data (device types, manufacturers, suppliers) — no Django admin needed for daily work
- Lending management with printable lending sheets and overdue email reminders
- Inventory/stocktaking mode with QR code scanning (browser camera)
- License and contract management with expiry notifications and ICS calendar feeds
- CSV bulk import with dry-run validation
- Read-only REST API (`/api/v2/`) with OpenAPI schema and Swagger UI
- Email notifications and periodic xlsx reports (subscription-based)
- Person/contract synchronization from an HR system (HR API sync)
- Multi-tenancy, optional LDAP authentication, customizable branding

## 👉 Getting started

The DLCDB is a Django project and needs [Python 3.12+](https://www.python.org/downloads/) on Debian Linux. Each [GitHub release](https://github.com/tombreit/django-dlcdb/releases) carries a wheel with the frontend assets and the handbook built in, so trying it needs neither npm nor a source checkout:

```bash
mkdir dlcdb && cd dlcdb  # instance directory: .env and data/ live here
python3 -m venv venv
venv/bin/pip install "dlcdb @ https://github.com/tombreit/django-dlcdb/releases/download/vX.Y.Z/dlcdb-X.Y.Z-py3-none-any.whl"
venv/bin/python -m dlcdb dlcdb_init  # writes .env, manage.py and wsgi.py
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
```

Then open <http://127.0.0.1:8000> (the generated `.env` allows `127.0.0.1`, not `localhost`), log in as that superuser and follow [Erste Schritte](https://tombreit.github.io/django-dlcdb/guides/erste_schritte.html) to set up groups, permissions, a tenant and rooms.

[Setup](https://tombreit.github.io/django-dlcdb/betrieb/setup.html) describes every way to run the DLCDB: as a [container image](https://tombreit.github.io/django-dlcdb/betrieb/setup.html#container-podman), as a [pip installation](https://tombreit.github.io/django-dlcdb/betrieb/setup.html#pip-installation) including production, or [from source](https://tombreit.github.io/django-dlcdb/betrieb/setup.html#from-source) for development.

## 📖 Documentation

`docs/` or [https://tombreit.github.io/django-dlcdb/](https://tombreit.github.io/django-dlcdb/)

## 📡 REST-API

The DLCDB exposes some data via its REST-API:

* [API docs](https://tombreit.github.io/django-dlcdb/betrieb/api.html)
* Endpoint: `https://fqdn/api/v2/`

## ✅ Tests

```bash
pytest  # or
make tests
```

## 📌 Compatibility

DLCDB supports:

- Python 3.12+
- any Django supported database backends, runs fine with SQLite in production

## ⚖️ License

[EUPL-1.2](https://github.com/tombreit/django-dlcdb/blob/main/LICENSE) - The EUPL is a reciprocal (or copyleft) licence, meaning that distributed contributions and improvements (called "derivatives") will be provided back or shared with the licensor and all other users. At the same time (and unlike other copyleft licences like the GPL or AGPL), the EUPL is compatible with most other open reciprocal licences and is interoperable. [Source](https://joinup.ec.europa.eu/collection/eupl/introduction-eupl-licence)
