# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Pre-populate ``DeviceType.icon`` with a suitable Bootstrap Icons class.

Most device type names are descriptive enough to guess a fitting icon
("Notebook" -> ``bi-laptop``, "Monitor" -> ``bi-display``). This command walks
all device types and fills in an icon based on an ordered keyword -> icon
mapping, saving the manual work of picking icons one by one in the admin.

By default it only fills *empty* icons (a manually chosen icon is never
overwritten). Use ``--force`` to (re)assign every matched type, and
``--dry-run`` to preview without writing.

    python manage.py populate_devicetype_icons --dry-run
    python manage.py populate_devicetype_icons
    python manage.py populate_devicetype_icons --force
"""

from django.core.management.base import BaseCommand

from dlcdb.core.models import DeviceType
from dlcdb.core.utils.bootstrap_icons import get_bootstrap_icons

# Ordered keyword -> icon rules. Matching is case-insensitive substring against
# the device type name; the FIRST matching rule wins, so rules must be ordered
# most-specific -> least-specific (e.g. "notebook" before "book",
# "bücherwagen" before "bücher"). Names are German + English. Every icon here
# is validated against the installed Bootstrap Icons set at startup.
ICON_RULES = [
    (["notebook", "macbook"], "bi-laptop"),
    (["laptop"], "bi-laptop"),
    (["monitor", "display"], "bi-display"),
    (["verwaltungs-pc", "pc sun", "pc", "workstation"], "bi-pc-display"),
    (["raid", "storage"], "bi-hdd-stack"),
    (["server parts", "cpu switch"], "bi-cpu"),
    (["server"], "bi-server"),
    (["tape"], "bi-archive"),
    (["hard disk", "festplatte", "hdd"], "bi-hdd"),
    (["drucker", "printer"], "bi-printer"),
    (["scanner"], "bi-upc-scan"),
    (["beamer", "projector", "presenter"], "bi-projector"),
    (["tv"], "bi-tv"),
    (["videoconference", "conferencecam"], "bi-camera-video"),
    (["webcam"], "bi-webcam"),
    (["camera", "kamera"], "bi-camera"),
    (["smartphone"], "bi-phone"),
    (["feature phone", "phone"], "bi-phone"),
    (["telefonanlage", "telefon"], "bi-telephone"),
    (["freisprech"], "bi-telephone"),
    (["tablet"], "bi-tablet"),
    (["router"], "bi-router"),
    (["firewall"], "bi-shield-lock"),
    (["kvm"], "bi-diagram-3"),
    # Before the network "switch" rule: "Powerswitch" contains "switch".
    (["usv", "powerswitch"], "bi-battery-charging"),
    (["switch", "network", "verteiler"], "bi-hdd-network"),
    (["wifi", "ekahau"], "bi-wifi"),
    (["docking"], "bi-usb-symbol"),
    # Before "headset": a VR headset reads better as goggles than audio headset.
    (["vr"], "bi-eyeglasses"),
    (["headset"], "bi-headset"),
    (["diktier", "mikro", "mic"], "bi-mic"),
    (["mediensteuerung"], "bi-sliders"),
    (["medientechnik", "speaker"], "bi-speaker"),
    (["eye tracker", "eye"], "bi-eye"),
    (["motion tracking"], "bi-camera-video"),
    (["sensor"], "bi-thermometer"),
    (["klima", "luftreiniger"], "bi-fan"),
    (["lizenz", "license"], "bi-key"),
    (["bücherwagen"], "bi-cart"),
    (["bücher", "zeitschrift"], "bi-journals"),
    (["schrank", "regal"], "bi-archive"),
    (["container", "aufbewahr"], "bi-box"),
    (["raummanager"], "bi-door-open"),
    (["cpu"], "bi-cpu"),
    (["sonstiges", "undefined", "unkategorisiert"], "bi-question-circle"),
]


def match_icon(name):
    """Return the icon class for the first matching rule, or None."""
    lowered = name.lower()
    for keywords, icon in ICON_RULES:
        if any(keyword in lowered for keyword in keywords):
            return icon
    return None


class Command(BaseCommand):
    help = "Pre-populate DeviceType icons with a fitting Bootstrap Icons class based on the type name."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Also (re)assign device types that already have an icon.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        self._validate_mapping_icons()

        matched, kept, unmatched = [], [], []

        for device_type in DeviceType.objects.all():
            name = (device_type.name or "").strip()
            if not name:
                continue

            if device_type.icon and not force:
                kept.append(device_type)
                continue

            icon = match_icon(name)
            if not icon:
                unmatched.append(device_type)
                continue

            if device_type.icon == icon:
                kept.append(device_type)
                continue

            self.stdout.write(f"  {name}: {device_type.icon or '∅'} -> {icon}")
            if not dry_run:
                device_type.icon = icon
                device_type.save(update_fields=["icon"])
            matched.append(device_type)

        self._report(matched, kept, unmatched, dry_run)

    def _validate_mapping_icons(self):
        """Warn (don't crash) if a mapped icon is not in the installed set."""
        installed = {icon["name"] for icon in get_bootstrap_icons()}
        if not installed:
            self.stdout.write(
                self.style.WARNING(
                    "Could not read the installed Bootstrap Icons set (theme not built?); skipping icon validation."
                )
            )
            return

        used = {icon for _, icon in ICON_RULES}
        missing = sorted(icon for icon in used if icon.removeprefix("bi-") not in installed)
        if missing:
            self.stdout.write(
                self.style.WARNING(f"These mapped icons are NOT in the installed icon set: {', '.join(missing)}")
            )

    def _report(self, matched, kept, unmatched, dry_run):
        prefix = "[dry-run] would assign" if dry_run else "Assigned"
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"{prefix}: {len(matched)} | kept: {len(kept)} | unmatched: {len(unmatched)}")
        )

        if unmatched:
            self.stdout.write(self.style.WARNING("No icon guessed for (assign manually in the admin if desired):"))
            for device_type in unmatched:
                self.stdout.write(f"  - {device_type.name}")
