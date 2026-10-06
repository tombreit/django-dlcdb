# DLCDB instance

This directory holds a DLCDB instance, created with DLCDB {{ version }}:

- `.env`: the configuration, explained by the comments in it; readable only by its owner
- `data/`: the database and the uploaded media files
- `manage.py`: Django's command-line utility for this instance
- `wsgi.py`: the entry point for the web server (e.g. Apache's `WSGIScriptAlias`)

Back up `data/` and `.env`.

First start, after editing `.env`:

    ./manage.py migrate
    ./manage.py createsuperuser

After installing a new release, `./manage.py dlcdb_init` adds files that are new, and
`./manage.py migrate` updates the database.

Documentation: https://tombreit.github.io/django-dlcdb/ and, for the installed
version, `/docs/` of the running DLCDB. Production setup, task runner and
updates: https://tombreit.github.io/django-dlcdb/betrieb/setup.html#pip-installation
