# Setup

The DLCDB runs as a [container image](#container-podman), as a [pip
installation](#pip-installation) or [from a source checkout](#from-source).
Each way keeps all data in `data/` (of a pip installation: inside its instance
directory) and needs a second process next to the web server, the [task
runner](#task-runner).

## Container (podman)

```sh
         .--"--.
       / -     - \
      / (O)   (O) \
   ~~~| -=(,Y,)=- |
    .---. /`  \   |~~
 ~/  o  o \~~~~.----. ~~
  | =(X)= |~  / (O (O) \
   ~~~~~~~  ~| =(Y_)=-  |
  ~~~~    ~~~|   U      |~~
```

### Try it

```bash
podman build \
    --tag dlcdb  \
    --file container/Containerfile .

podman run \
    --name podman-dlcdb \
    --tty --interactive \
    --publish 8000:8000 \
    --volume ./data:/app/data \
    --rm \
    dlcdb dev
```

The image builds the frontend assets, ships the compiled message catalog and
bundles the rendered handbook, so **running it needs neither npm nor gettext
nor Sphinx** — only a container runtime.

The same image serves production (see `container/Containerfile` and
`container/entrypoint.sh`). It understands three commands:

| Command | Does |
|---|---|
| `dev` | `migrate`, `collectstatic`, then Django's development server |
| `serve` | `migrate`, `collectstatic`, then gunicorn (the default `CMD`) |
| `huey` | the background task runner, nothing else; waits until `serve` has applied all migrations |

Anything else is executed verbatim, e.g. `podman run --rm dlcdb python3 manage.py createsuperuser`.

### Production

Mount an `.env` and the data directory, and run the task runner as a second
container against the same volume:

```bash
podman run \
    --name dlcdb \
    --detach \
    --publish 8000:8000 \
    --volume ./data:/app/data \
    --volume ./.env:/app/.env:ro \
    dlcdb serve

podman run \
    --name dlcdb-huey \
    --detach \
    --volume ./data:/app/data \
    --volume ./.env:/app/.env:ro \
    dlcdb huey
```

Without the second container, background tasks silently never run.
`INTERNAL_SERVER_PORT` (default 8000) and `GUNICORN_WORKERS` (default 3) are
honoured as environment variables.

Put a TLS-terminating reverse proxy in front of gunicorn; it is not meant to
face the internet directly.

### Update

Build the new image, then stop and remove the old task runner container before
starting the new `dlcdb serve` container, which runs the migrations. The new
task runner container can be started right away: it waits until all migrations
are applied.

```bash
podman rm --force dlcdb-huey dlcdb
podman run --name dlcdb ... dlcdb serve
podman run --name dlcdb-huey ... dlcdb huey
```

## Pip installation

Each [GitHub release](https://github.com/tombreit/django-dlcdb/releases)
carries a wheel. Like the container image it contains the frontend assets, the
compiled message catalog and the rendered handbook, so **installing it needs
neither npm nor gettext nor Sphinx**, only Python. The static files come
collected, so there is no `collectstatic` step either. For LDAP, pip builds
`python-ldap`, which needs `libldap2-dev libsasl2-dev python3-dev gcc`.

A pip installation keeps its `.env` and `data/` (database, media files) in one
directory, the instance directory. The management command `dlcdb_init` writes a
`manage.py` and a `wsgi.py` there, which run DLCDB for that directory: from then
on you work with `./manage.py` as in any Django project. Only the first
`dlcdb_init` needs the directory in the environment variable `DLCDB_HOME`.

### Install

Run the commands as the user that runs DLCDB (the web server's daemon process,
the task runner): `.env` is readable only by its owner.

```bash
python3 -m venv /srv/dlcdb/venv
/srv/dlcdb/venv/bin/pip install "dlcdb[ldap] @ https://github.com/tombreit/django-dlcdb/releases/download/v0.9.4/dlcdb-0.9.4-py3-none-any.whl"
DLCDB_HOME=/srv/dlcdb /srv/dlcdb/venv/bin/python -m dlcdb dlcdb_init  # writes .env (with a fresh secret key), manage.py, wsgi.py, README.md
# edit /srv/dlcdb/.env
cd /srv/dlcdb
./manage.py migrate
./manage.py createsuperuser
```

Without LDAP, leave out `[ldap]`.

### Production

**Task runner:** the [task runner unit](#task-runner-unit) of the source
installation, with `ExecStart=/srv/dlcdb/manage.py run_huey`.

**Apache and mod_wsgi:** the [Apache configuration](#apache-and-mod_wsgi) of the
source installation, with `/srv/dlcdb/data/media` for `/media`,
`/srv/dlcdb/wsgi.py` (written by `dlcdb_init`) as `WSGIScriptAlias` and in
`<Directory /srv/dlcdb>`, and `python-home=/srv/dlcdb/venv` without
`python-path`.

### Update

```bash
/srv/dlcdb/venv/bin/pip install "dlcdb[ldap] @ https://github.com/tombreit/django-dlcdb/releases/download/vX.Y.Z/dlcdb-X.Y.Z-py3-none-any.whl"
cd /srv/dlcdb
./manage.py dlcdb_init  # adds files that are new in this release
# The task runner writes to the database every minute; stop it while the
# migrations run, so they don't compete for the write lock.
systemctl --user stop dlcdb_huey.service
./manage.py migrate --noinput
systemctl --user start dlcdb_huey.service
touch wsgi.py
```

## From source

### Prerequisites

- (assuming) Debian 13
- Python >= 3.12 (see `pyproject.toml`)
- Django 6.x (installed via the requirements files)
- npm
- for LDAP: libldap2-dev libsasl2-dev

### Development setup

**Python**

*Assuming local development environment in a virtual python environment*

```bash
git clone git@gitlab.gwdg.de:dlcdb/django-dlcdb.git
cd django-dlcdb
python3 -m venv .venv  # Create a virtual environment
source .venv/bin/activate  # Activate the virtual environment
pip install --upgrade pip setuptools wheel  # Update virtual environment
pip install -r requirements/dev.txt  # Install development requirements
```

**Set environment for project**

```bash
./manage.py dlcdb_init  # writes .env with a fresh secret key
# edit .env, for development set DJANGO_DEBUG=true
```

:::{note}
**LDAP.** Set `AUTH_LDAP=true` and the `AUTH_LDAP_*` variables in `.env` (see
the comments there); what the LDAP groups do is described in
[Berechtigungen › LDAP](../guides/berechtigungen.md#ldap). Set `LDAP_VARIANT`
to match your directory: `msad` (default) for Microsoft Active Directory, or
`openldap` for OpenLDAP-based directories (e.g. Univention Corporate Server).
This selects the appropriate group type (`ActiveDirectoryGroupType` vs.
`PosixGroupType`).
:::

**Build frontend assets**

```bash
npm install
npm run build
```

**Run this project**

```bash
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
# or, runserver+https (dev requirements only, django-extensions):
./manage.py runserver_plus --cert /tmp/cert
```

The superuser is the only account after a fresh install. Continue with
[Erste Schritte](../guides/erste_schritte.md). Dependencies, lock files and
releases are described in [Development](development.md).

### Production

:::{warning}
Be sure to use one of the production requirement files:

* `requirements/prod.txt`
* `requirements/prod-ldap.txt`
:::

#### Task runner unit

Add a systemd user service unit for the [task runner](#task-runner) (modify paths etc.):

```ini
# /etc/systemd/user/dlcdb_huey.service

[Unit]
Description=DLCDB huey workers

[Service]
WorkingDirectory=/home/USERNAME/dlcdb
ExecStart=/path/to/venv/bin/python3 /path/to/manage.py run_huey

[Install]
WantedBy=default.target
```

Enable the task runner as a systemd service unit for a given system user:

```bash
sudo loginctl enable-linger USERNAME
sudo systemctl daemon-reload
sudo loginctl user-status USERNAME
# *login via USERNAME*
export XDG_RUNTIME_DIR="/run/user/$UID"
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
systemctl --user daemon-reload
systemctl --user enable dlcdb_huey.service
systemctl --user restart dlcdb_huey.service
systemctl --user status dlcdb_huey.service
```

#### Deployment steps

```bash
npm install
npm run build
source /path/to/dlcdb/venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements/prod-ldap.txt  # requirements/prod.txt
python manage.py collectstatic --noinput
# The task runner writes to the database every minute; stop it while the
# migrations run, so they don't compete for the write lock.
systemctl --user stop dlcdb_huey.service
python manage.py migrate --noinput
systemctl --user start dlcdb_huey.service
touch dlcdb/wsgi.py
make docs
```

#### Apache and mod_wsgi

```apacheconf
<VirtualHost *:443>
    ServerName dlcdb.fqdn

    Alias /media /path/to/data/media
    <Directory /path/to/data/media>
        Require all granted
    </Directory>

    <Directory /path/to/dlcdb>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>

    WSGIPassAuthorization On
    WSGIScriptAlias / /path/to/dlcdb/wsgi.py process-group=dlcdb
    WSGIDaemonProcess dlcdb \
        user=dlcdb \
        group=dlcdb \
        python-path=/path/to/dlcdb \
        python-home=/path/to/venv \
        lang=en_US.UTF-8 \
        locale=en_US.UTF-8
</VirtualHost>
```

## Operations

### Task runner

Background work runs in [huey](https://github.com/coleifer/huey): notifications,
the HR sync and the nightly database snapshot for [backups](#backup). In a
container it is the `dlcdb huey` container, from source the systemd unit above.
Its queue lives in `data/db/huey_task_queue.sqlite3` and holds only transient
data (tasks waiting to run and locks; results are not stored), so the file stays
at a few MB.

### SQLite

The settings tune SQLite for several writers on one file (web server, task
runner, `migrate` during a deploy), see `DATABASES` in `dlcdb/settings/base.py`:

* [Write Ahead Logging (WAL)](https://www.sqlite.org/wal.html), switched on at the
  first connect: readers keep working while a writer holds the lock.
* `transaction_mode=IMMEDIATE` and a 20 s busy timeout: a writer waits for the
  lock instead of failing with "database is locked".
* Larger caches, memory-mapped reads and a capped WAL file.

WAL adds the files `db.sqlite3-wal` and `db.sqlite3-shm` next to the database.
All processes must run on the same host, with the database on a local disk (no
network filesystem).

### Backup

Die DLCDB nutzt als Datenbank SQLite. Sämtliche Betriebsdaten der DLCDB inkl. der Datenbankdatei sind im Verzeichnis `data/` gespeichert. Für ein vollständiges Backup sind das Verzeichnis `data/` sowie - falls vorhanden - die Datei `.env` zu sichern.

Die Datenbank läuft im WAL-Modus: Zuletzt gespeicherte Änderungen stehen zunächst in `db.sqlite3-wal`. Eine einfache Kopie von `db.sqlite3` im laufenden Betrieb kann sie verpassen oder inkonsistent sein.

Deshalb schreibt der Task Runner jede Nacht um 00:30 UTC einen Snapshot der Datenbank: `data/db/db.sqlite3.snapshot`. Er ist vollständig, konsistent und kompakt (`VACUUM INTO`, ohne die freien Seiten der laufenden Datenbank), eine einzelne Datei, und kann jederzeit kopiert werden, denn er wird erst fertig geschrieben und dann ausgetauscht. Ein Backup-Skript sichert also diese Datei und lässt die laufende Datenbank (`db.sqlite3`, `db.sqlite3-wal`, `db.sqlite3-shm`) aus, ebenso die Warteschlange des Task Runners (`huey_task_queue.sqlite3` samt `-wal`/`-shm`), die nur kurzlebige Daten enthält. Ohne laufenden Task Runner entsteht kein neuer Snapshot; das Backup-Skript sollte deshalb das Alter der Datei prüfen. Der Snapshot entsteht nur, wenn die DLCDB mit einer SQLite-Datei läuft. Komprimieren übernimmt das Backup-Skript: Mit `zstd` oder `gzip` schrumpft der Snapshot auf etwa ein Zehntel. Backup-Werkzeuge mit Deduplizierung (z. B. borg, restic) komprimieren selbst und sollten den unkomprimierten Snapshot bekommen.

Für einen aktuelleren Stand als den nächtlichen Snapshot sichert `sqlite3` die Datenbank auch im laufenden Betrieb in eine einzelne Datei:

```bash
sqlite3 data/db/db.sqlite3 ".backup 'data/db/db.sqlite3.backup-$(date +%Y%m%d-%H%M%S)'"
```

Wiederherstellen: DLCDB stoppen (Webserver und Task Runner), den Snapshot nach `data/db/db.sqlite3` kopieren, `db.sqlite3-wal` und `db.sqlite3-shm` löschen, DLCDB starten.

### Documentation

Build (this) Documentation:

```bash
make docs
```

The built documentation lands in `run/docs` and is served by the
application itself at `/docs/` (via WhiteNoise, see
`MoreWhiteNoiseMiddleware`) — that is why `make docs` is part of the
deployment steps above. A pip installation gets them with the wheel.

### Localization

Source strings are English and wrapped in `gettext_lazy`; German is supplied
by the catalog in `dlcdb/locale/de/`. There is deliberately **no `en`
catalog** — an empty `msgstr` falls back to the msgid, and the msgids already
are the English source.

Extract and compile with:

```bash
./manage.py makemessages --locale de --ignore=.venv/*
poedit dlcdb/locale/de/LC_MESSAGES/django.po
./manage.py compilemessages --ignore=.venv/*
```

The compiled catalog `dlcdb/locale/de/LC_MESSAGES/django.mo` is **committed**.
gettext reads only the `.mo`, never the `.po`, so shipping it means a
deployment needs neither `compilemessages` nor gettext on the target machine —
which is why that step is absent from the deployment steps above.
