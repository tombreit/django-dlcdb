# ♻ DLCDB

*Device Live Cycle Database*

The DLCDB manages the life cycle of IT assets

⚡ Currently available only in German. ⚡


## 🔥 Features

- Tracking records of devices: a finite number of records/states (*lent*, *removed*, *inroom* etc.) exists, and a device can only have one record at a time. In the life cycle of the device the device collects records.
- Lending management
- Inventory
- REST-API
- UDB integration
- Reporting
- ...

## 👉 Getting started

The DLCD works with [Python 3](https://www.python.org/downloads/) and [nodejs](https://nodejs.org/en/download/), on Debian Linux.

To get started using the DLCDB, run the following in a virtual environment (development setup, not to be used in production):

```bash
npm install
npm run prod
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Detailed setup and installation docs: `docs/chapters/setup.rst`

## 📖 Documentation

`docs/` or https://fqdn/docs/ 


## 📡 REST-API

The DLCDB exposes some data via its REST-API:

https://fqdn/api/v2/

API docs: `docs/chapters/api.rst`


## ⚠️ Tests

```bash
# ⚡ jep, tests are missing
pytest  # or
make tests
```


## 📌 Compatibility

DLCDB supports:

-   Python 3.9+
-   any Django supported database backends, runs fine with Sqlite in production


## ⚖️ License

[EUPL-1.2](https://gitlab.gwdg.de/t.breitner/django-dlcdb/-/blob/main/LICENSE) - The EUPL is a reciprocal (or copyleft) licence, meaning that distributed contributions and improvements (called "derivatives") will be provided back or shared with the licensor and all other users. At the same time (and unlike other copyleft licences like the GPL or AGPL), the EUPL is compatible with most other open reciprocal licences and is interoperable. (Source: https://joinup.ec.europa.eu/collection/eupl/introduction-eupl-licence)
