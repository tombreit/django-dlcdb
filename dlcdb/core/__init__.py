# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The core of the DLCDB: the models, the device lifecycle and the rules the other apps
rely on. Other apps import from ``dlcdb.core.models``, ``dlcdb.core.lifecycle`` and
``dlcdb.core.utils``. Nothing is re-exported here: Django imports this package before
models can be defined.

- ``models/``, ``lifecycle.py`` and ``utils/`` import no other app of the project,
  except ``organization.Branding`` (in ``get_contact_email``),
  ``tenants.abstracts.TenantAwareModel`` and ``inventory.utils.update_inventory_note``.
  The admin (``admin/``, ``forms/``, their views and templates) is a UI like any other
  and may import other apps; it is being phased out.
- Code appends records through the lifecycle (``transition_*``, ``localise``).
  ``Record.save()`` checks every new record against the transition table, also those
  the admin's add views save directly.
- A rule several apps need lives here once, on the model or in the lifecycle, for
  example ``LentRecord.overdue_q`` or ``Person.search_q``. ``LentRecord.objects`` means
  lentable, not lent: a device is lent while its active record is ``LENT``.
- A model method that only the admin reads belongs in the admin.
"""
