# Setup

## Prequisites

- (assuming) Debian 11.x
- Python>=3.9
- npm
- for LDAP: libldap2-dev libsasl2-dev

## Installation

*Assuming local development environment in a virtual python environment*



```bash
cd django-dlcdb
python3 -m venv .venv  # Create a virtual env
source .venv/bin/activate  # Activate the virtual env
pip install --upgrade pip setuptools wheel  # Bring your virtual env uptodate
pip install -r requirements.txt  # Install development requirements
```

Set environment for project:

```bash
cp env.template .env
# edit .env
```

:::{note}
**Permissions** should be assigned to Django groups. Only LDAP groups listet in `AUTH_LDAP_MIRROR_GROUPS` in the `.env`-file are mirrored as Django groups.
:::


Build frontend assets:

```bash
npm install
npm run prod
```

Run this project:

```bash
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
# or, runserver+https:
./manage.py runserver_plus --cert /tmp/cert
```

Build (this) Documentation:

```bash
make -C docs html
```

## Branding

:::{tip}
**Branding** is done via two steps: crafting an individual `.env` and 
place your logo files (format: `svg`) at the following paths:

- `dlcdb/static/dlcdb/branding/logo.svg` (white foreground, transparent background)
- `dlcdb/static/dlcdb/branding/logo_bw.svg` (black foreground, transparent or white background)
:::


## Production deployment

:::{warning}
Be sure to use one of the production requirement files:

```bash
> requirements
> -- requirements-prod-ldap.txt
> -- requirements-prod.txt
```
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
pip install -r requirements/requirements-prod-ldap.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
systemctl --user restart dlcdb_huey.service
touch dlcdb/wsgi.py
make -C docs html
```

## Apache

*coming soon*
