{% autoescape off %}# DLCDB instance

This directory holds a DLCDB instance, created with DLCDB {{ version }}:

- `.env`: the configuration, explained by the comments in it
- `data/`: the database and the uploaded media files

Back up `data/` and `.env`. Every `dlcdb` command finds this directory through
the environment variable `DLCDB_HOME`:

    export DLCDB_HOME={{ instance_dir }}

First start, after editing `.env`:

    dlcdb migrate
    dlcdb createsuperuser

Documentation: https://dlcdb.pages.gwdg.de/django-dlcdb/ and, for the installed
version, `/docs/` of the running DLCDB. Production setup, task runner and
updates: https://dlcdb.pages.gwdg.de/django-dlcdb/betrieb/setup.html#pip-installation
{% endautoescape %}
