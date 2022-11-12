======================
Setup and installation
======================


Prequisites
-----------------------

* (assuming) Debian 11.x
* Python>=3.9
* npm
* for LDAP: libldap2-dev libsasl2-dev


Installation
------------

*Assuming local development environment*

Create a virtual environment:

.. code:: bash

    cd django-dlcdb
    python3 -m venv .venv


Activate the virtualenv and install the requirements:

.. code:: bash

    source .venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt

Set environment for project:

.. code:: bash
    
    cp env.template .env
    # edit .env



.. note:: Permissions

   Permissions should be assigned to Django groups. Only LDAP groups listet in `AUTH_LDAP_MIRROR_GROUPS` in the `.env`-file are mirrored as Django groups.


Place your logo files (format: `svg`) at the following paths:

* `dlcdb/static/dlcdb/branding/logo.svg` (white foreground, transparent background)
* `dlcdb/static/dlcdb/branding/logo_bw.svg` (black foreground, transparent or white background)


.. note:: Branding

   Branding is done via the two steps above: crafting an individual `.env` and saving the two logo files.


Build frontend assets:

.. code:: bash

    npm install
    npm run prod


Run this project:

.. code:: bash

    ./manage.py migrate
    ./manage.py createsuperuser
    ./manage.py runserver
    # or, runserver+https:
    ./manage.py runserver_plus --cert /tmp/cert


Build Dokumentation:

.. code:: bash

    make docs


Task runner
-----------

As a task runner/task schedular this projects uses `huey <https://github.com/coleifer/huey>`_. 

Add a systemd user service unit for huey (modify paths etc.):

.. code:: ini

    # /etc/systemd/user/dlcdb_huey.service

    [Unit]
    Description=DLCDB huey workers

    [Service]
    WorkingDirectory=/home/USERNAME/dlcdb
    ExecStart=/path/to/venv/bin/python3 /path/to/manage.py run_huey

    [Install]
    WantedBy=default.target

Enable the task runner as a systemd service unit for a given system user:

.. code:: bash

   $ sudo loginctl enable-linger USERNAME
   $ sudo systemctl daemon-reload
   $ sudo loginctl user-status USERNAME
   $ *login via USERNAME*
   $ export XDG_RUNTIME_DIR="/run/user/$UID"
   $ export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
   $ systemctl --user enable dlcdb_huey.service
   $ systemctl --user restart dlcdb_huey.service
   $ systemctl --user status dlcdb_huey.service


Production deployment
---------------------

Be sure to use one of the production requirement files:
.. code:: bash

   requirements
   |-- requirements-prod-ldap.txt
   `-- requirements-prod.txt


.. code:: bash

   mkdir -p /path/to/dlcdb/staticfiles
   mkdir -p /path/to/dlcdb/dlcdb/media
   npm install
   npm run prod
   source /path/to/dlcdb/venv/bin/activate
   pip install --upgrade pip setuptools wheel
   pip install -r requirements/requirements-prod-ldap.txt
   python manage.py collectstatic --noinput
   python manage.py migrate --noinput
   export XDG_RUNTIME_DIR="/run/user/$UID"
   export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
   systemctl --user restart dlcdb_huey.service
   touch dlcdb/wsgi.py
   make docs


Apache
------

*coming soon*