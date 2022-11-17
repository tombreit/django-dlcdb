# NEWS


## 2022-11b
* Branding refactored to be handled in Django admin instead of the previous .env file
* Docs now on gitlab pages: https://dlcdb.pages.gwdg.de/django-dlcdb/
* Requirements now build from `setup.cfg`. See `docs/betrieb/setup.rst`
* ⚡ Refactored some parts of DLCDB. Start your instance from a clean checkout!
* ⚡ Defaults to `dev` requirements (`requirements.txt`). Use a dedicated requirements file for production, e.g. `requirements/requirement-prod-ldap.txt`)

## 2022-11a

* New mandatory `.env` variable: `DJANGO_DEBUG`
* Some setup hints implemented via Django messages framework, warns for:
  * Devices without record
  * No `is_auto_return_room` room
  * No  `is_external` room
* Enable/disable usage of LDAP authentification via new `.env` variable `AUTH_LDAP`