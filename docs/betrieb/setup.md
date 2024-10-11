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

### Install from source

**Prequisites**

- (assuming) Debian 11.x
- Python>=3.9
- npm
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
**Permissions** should be assigned to Django groups. Only LDAP groups listet in `AUTH_LDAP_MIRROR_GROUPS` in the `.env`-file are mirrored as Django groups.
:::

**Build frontend assets**

```bash
npm install
npm run prod
```

**Run this project**

```bash
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
# or, runserver+https:
./manage.py runserver_plus --cert /tmp/cert
```

## Production deployment

:::{warning}
Be sure to use one of the production requirement files:

* `requirements/prod.txt`
* `requirements/prod-ldap.txt`
:::

:::{tip}
Speed up your sqlite, enable [Write Ahead Logging (WAL)](https://www.sqlite.org/wal.html) (one off command):

`sqlite3 run/db/db.sqlite3 'PRAGMA journal_mode=WAL;'`
:::

### Task runner

As a task runner/task schedular this projects uses [huey](https://github.com/coleifer/huey).

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
$ sudo loginctl enable-linger USERNAME
$ sudo systemctl daemon-reload
$ sudo loginctl user-status USERNAME
$ *login via USERNAME*
$ export XDG_RUNTIME_DIR="/run/user/$UID"
$ export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
$ systemctl --user daemon-reload
$ systemctl --user enable dlcdb_huey.service
$ systemctl --user restart dlcdb_huey.service
$ systemctl --user status dlcdb_huey.service
```

### Deployment steps

```bash
npm install
npm run prod
source /path/to/dlcdb/venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements/prod-ldap.txt  # requirements/prod.txt
python manage.py collectstatic --noinput
python manage.py compilemessages -l de
python manage.py migrate --noinput
systemctl --user restart dlcdb_huey.service
touch dlcdb/wsgi.py
make docs
```

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

Get rid of the default DLCDB branding: Set your organization via *> Start > Organization > Branding*

### Backup

Die DLCDB nutzt als Datenbank SQLite. Sämtliche Betriebsdaten der DLCDB inkl. der Datenbankdatei sind im Verzeichnis `data/` gespeichert. Für ein vollständiges Backup sind das Verzeichnis `data/` sowie - falls vorhanden - die Datei `.env` zu sichern.

### Documentation

Build (this) Documentation:

```bash
make docs
```

### Localization

```bash
./manage.py makemessages --locale de --ignore=.venv/* 
poedit dlcdb/locale/de/LC_MESSAGES/django.po
./manage.py compilemessages --ignore=.venv/*
```

### Requirements

(Re-)Build requirements via `make requirements`.
