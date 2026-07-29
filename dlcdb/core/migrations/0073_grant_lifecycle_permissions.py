# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Carry existing lifecycle grants over to the new per-transition permissions.

Offering a lifecycle action used to be gated on the ``add_*`` permission of the
proxy model that writes the target state. Each transition now has its own
permission, so without this migration every group would lose every lifecycle
button on upgrade.

The mapping below reproduces exactly what each group could already do. Where the
old scheme was coarser than the new one it is resolved *downwards*, never
upwards -- a migration must not hand anyone a capability they did not have:

* ``return_lending`` used to be gated on ``add_inroomrecord`` (its target is
  INROOM) but now shares ``can_lend_device`` with ``lend``. It is migrated from
  ``add_lentrecord``, the narrower of the two. Someone who could move devices but
  not lend them therefore loses the Return button rather than gaining the Lend
  one.
* ``restore`` and ``recover`` are migrated from nothing at all. They were never
  surfaced (superuser-only in the admin), so granting them here would newly open
  the way out of REMOVED for ordinary groups. They ship granted to nobody; an
  operator who wants them assigns them deliberately.
"""

from django.conf import settings
from django.db import migrations

# new codename -> the old permission whose holders should receive it
MAPPING = {
    "can_order_device": "add_orderedrecord",
    "can_locate_device": "add_inroomrecord",
    "can_relocate_device": "add_inroomrecord",
    "can_find_device": "add_inroomrecord",
    "can_lend_device": "add_lentrecord",
    "can_lose_device": "add_lostrecord",
    "can_remove_device": "add_removedrecord",
    # can_restore_device and can_recover_device: deliberately nobody, see above.
}

# Must match Record.Meta.permissions.
NEW_PERMISSIONS = [
    ("can_order_device", "Can record a device as ordered"),
    ("can_locate_device", "Can localise a device for the first time"),
    ("can_relocate_device", "Can move a device to another room"),
    ("can_lend_device", "Can lend a device and take it back"),
    ("can_lose_device", "Can mark a device as not locatable"),
    ("can_find_device", "Can mark a lost device as found"),
    ("can_remove_device", "Can remove (decommission) a device"),
    ("can_restore_device", "Can restore a removed device to not-locatable"),
    ("can_recover_device", "Can recover a removed device into a room"),
]


def _new_permissions(apps):
    """Create the Permission rows this migration needs and return them by codename.

    ``create_permissions`` runs in a ``post_migrate`` handler, which ``migrate``
    emits only once every pending migration has been applied. So at this point no
    row exists yet for any codename declared in the preceding
    ``AlterModelOptions`` -- splitting these into two migration files does not
    change that, since both run inside the same ``migrate`` invocation. Create
    them here; ``get_or_create`` makes the later ``post_migrate`` a no-op.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")

    record_ct, _ = ContentType.objects.get_or_create(app_label="core", model="record")
    created = {}
    for codename, label in NEW_PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            codename=codename,
            content_type=record_ct,
            defaults={"name": label},
        )
        created[codename] = permission
    return created


def forwards(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    User = apps.get_model(settings.AUTH_USER_MODEL)

    new_permissions = _new_permissions(apps)

    for new_codename, old_codename in MAPPING.items():
        # Scoped to the core app: the legacy "dlcdb" app label carries dead
        # permissions with colliding codenames that no longer grant anything.
        old = Permission.objects.filter(codename=old_codename, content_type__app_label="core").first()
        if old is None:
            continue
        new = new_permissions[new_codename]
        for group in Group.objects.filter(permissions=old):
            group.permissions.add(new)
        for user in User.objects.filter(user_permissions=old):
            user.user_permissions.add(new)


def backwards(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    User = apps.get_model(settings.AUTH_USER_MODEL)

    codenames = [codename for codename, _ in NEW_PERMISSIONS]
    permissions = list(Permission.objects.filter(codename__in=codenames, content_type__app_label="core"))
    if not permissions:
        return
    for group in Group.objects.filter(permissions__in=permissions).distinct():
        group.permissions.remove(*permissions)
    for user in User.objects.filter(user_permissions__in=permissions).distinct():
        user.user_permissions.remove(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0072_alter_record_options"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
