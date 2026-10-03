# Setup

## Development setup

### Install with podman

Want to try it containerized via `podman`?

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

For production, mount an `.env` and the data directory, and run the task
runner as a second container against the same volume:

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

Without the second container, background tasks (notifications, report
generation) silently never run. `INTERNAL_SERVER_PORT` (default 8000) and
`GUNICORN_WORKERS` (default 3) are honoured as environment variables.

Put a TLS-terminating reverse proxy in front of gunicorn; it is not meant to
face the internet directly.

### Install from source

**Prerequisites**

- (assuming) Debian 13
- Python >= 3.13 (see `pyproject.toml`)
- Django 6.x (installed via the requirements files)
- npm — for development and for building the container image, not for running a built image
- for LDAP: libldap2-dev libsasl2-dev

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
cp env.template .env
# edit .env
```

:::{note}
**Permissions** should be assigned to Django groups. Only LDAP groups listed in `AUTH_LDAP_MIRROR_GROUPS` in the `.env`-file are mirrored as Django groups. Members of `AUTH_LDAP_GROUP_SUPERUSERS` become staff and superuser. See [Berechtigungen](../guides/berechtigungen.md).
:::

:::{note}
**LDAP variant.** Set `LDAP_VARIANT` in `.env` to match your directory:
`msad` (default) for Microsoft Active Directory, or `openldap` for
OpenLDAP-based directories (e.g. Univention Corporate Server). This selects
the appropriate group type (`ActiveDirectoryGroupType` vs. `PosixGroupType`).
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
[Erste Schritte](../guides/erste_schritte.md) to set up branding, groups,
tenant, users and rooms.

## Production deployment

:::{warning}
Be sure to use one of the production requirement files:

* `requirements/prod.txt`
* `requirements/prod-ldap.txt`
:::

:::{note}
The settings tune SQLite for several writers on one file (web server, task
runner, `migrate` during a deploy), see `DATABASES` in `dlcdb/settings/base.py`:

* [Write Ahead Logging (WAL)](https://www.sqlite.org/wal.html), switched on at the
  first connect: readers keep working while a writer holds the lock.
* `transaction_mode=IMMEDIATE` and a 20 s busy timeout: a writer waits for the
  lock instead of failing with "database is locked".
* Larger caches, memory-mapped reads and a capped WAL file.

WAL adds the files `db.sqlite3-wal` and `db.sqlite3-shm` next to the database.
All processes must run on the same host, with the database on a local disk (no
network filesystem). Back up the nightly snapshot, see *Backup* below.
:::

### Task runner

As a task runner/task schedular this projects uses [huey](https://github.com/coleifer/huey).

For a containerized deployment run the task runner as a second container
(`dlcdb huey`, see *Install with podman* above) instead of the systemd unit
below.

Besides notifications and the HR sync, it writes the nightly database snapshot
for backups (see *Backup*).

Its queue lives in `data/db/huey_task_queue.sqlite3`. The file holds only
transient data: tasks waiting to run and locks. Task results are not stored
(`results=False`, nobody reads them), so the file stays at a few MB and needs no
backup.

Add a systemd user service unit for huey (modify paths etc.):

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

### Deployment steps

These are the steps for a **source checkout** deployment, which builds
everything on the target machine. For a containerized deployment build the
image instead and run `dlcdb serve` — see *Install with podman* above.

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

For a containerized deployment, stop and remove the old task runner container
(`dlcdb huey`) before starting the new `dlcdb serve` container, which runs the
migrations. The new task runner container can be started right away: it waits
until all migrations are applied.

```bash
podman rm --force dlcdb-huey dlcdb
podman run --name dlcdb ... dlcdb serve
podman run --name dlcdb-huey ... dlcdb huey
```

### Huey queue file grown large (one-time)

Before October 2026 huey stored every task result, and the SQLite backend never
expires them: the queue file grew by gigabytes (7 GB in production). Since then
no results are stored, but the existing file keeps its size. It holds nothing of
value, so reset it once during the deployment, while the task runner is stopped:

```bash
systemctl --user stop dlcdb_huey.service
# Both counts must be 0: no task is still waiting to run.
sqlite3 data/db/huey_task_queue.sqlite3 "select count(*) from task; select count(*) from schedule;"
rm data/db/huey_task_queue.sqlite3 data/db/huey_task_queue.sqlite3-wal data/db/huey_task_queue.sqlite3-shm
python manage.py migrate --noinput
systemctl --user start dlcdb_huey.service  # creates a new, empty queue file
touch dlcdb/wsgi.py                        # the web workers reconnect to the new file
```

If a count is not 0, start the task runner again until it has worked off the
waiting tasks, then stop it and check once more.

For a containerized deployment: remove both containers, delete the three files
on the data volume, then start `dlcdb serve` and `dlcdb huey` again.

### Apache and mod_wsgi

```
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

## Misc

### Branding

Get rid of the default DLCDB branding: Set your organization via *Start › Organization › Branding*

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
deployment steps above.

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

### Requirements

(Re-)Build requirements via `make requirements` (uses pip-tools to
compile `requirements/{prod,prod-ldap,dev}.txt` from `pyproject.toml`).
