# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import shutil
import string
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from faker import Faker

from dlcdb.core.models import Device, Person


def unique_name_pair(fake, used_pairs):
    """
    Draws (first_name, last_name) until the pair hasn't been used yet.

    Person's unique constraints are on the (first_name, last_name) pair, not
    on first_name alone. Faker's per-field `.unique` first_name pool is only
    a few hundred entries - far fewer than DLCDB's person count - so forcing
    global uniqueness on first_name alone exhausts it. Deduping the pair
    instead uses the much larger first_name x last_name combination space.
    """
    while True:
        first_name = fake.first_name()
        last_name = fake.last_name()
        key = (first_name.lower(), last_name.lower())
        if key not in used_pairs:
            used_pairs.add(key)
            return first_name, last_name


def unique_value(generate, used_values):
    """
    Draws a value from `generate` until it hasn't been used yet.

    Uses a caller-supplied `used_values` set rather than Faker's own
    `.unique` proxy, so it can be seeded with values that already exist in
    the db (see the seeding of `used_person_names` et al. in `handle()`) -
    otherwise a freshly generated value could collide with a still-untouched
    row further down the loop and trip the db-level unique constraint.
    """
    while True:
        value = generate()
        if value not in used_values:
            used_values.add(value)
            return value


class Command(BaseCommand):
    help = (
        "Anonymizes Person names/emails/photos, Device serial numbers and "
        "user accounts (username/names/email), e.g. before taking "
        "screenshots of the running app."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["dryrun", "write"],
            default="dryrun",
            help="Simulate what to do. Basically a validation run.",
        )

    def backup_sqlite_db(self):
        db_settings = settings.DATABASES["default"]

        if db_settings["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError(
                "Automatic backup is only supported for sqlite databases. "
                "Back up your database manually, then re-run with --mode write."
            )

        db_path = db_settings["NAME"]
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{db_path}.backup-{timestamp}"
        shutil.copy2(db_path, backup_path)

        self.stdout.write(self.style.WARNING(f"Backed up database to: {backup_path}"))

        return db_path, backup_path

    def handle(self, *args, **options):
        write = options["mode"] == "write"
        print(f"mode: {write=}")

        db_path = backup_path = None
        if write:
            db_path, backup_path = self.backup_sqlite_db()

        fake = Faker()

        # Seed with all current name pairs, not just ones already reassigned this
        # run. Rows are saved one at a time, so a freshly drawn fake pair could
        # otherwise collide with the still-untouched original name of a person
        # later in the loop and trip the db-level unique constraint.
        used_person_names = {
            (first_name.lower(), last_name.lower())
            for first_name, last_name in Person.with_softdeleted_objects.values_list("first_name", "last_name")
        }
        used_udb_person_names = {
            (first_name.lower(), last_name.lower())
            for first_name, last_name in Person.with_softdeleted_objects.values_list(
                "udb_person_first_name", "udb_person_last_name"
            )
            if first_name and last_name
        }
        # Same reasoning as the name pairs above, one seeded set per unique email field.
        used_emails = set(filter(None, Person.with_softdeleted_objects.values_list("email", flat=True)))
        used_udb_emails_private = set(
            filter(None, Person.with_softdeleted_objects.values_list("udb_person_email_private", flat=True))
        )
        used_udb_emails_internal_business = set(
            filter(
                None,
                Person.with_softdeleted_objects.values_list("udb_person_email_internal_business", flat=True),
            )
        )

        persons_touched = 0
        with transaction.atomic():
            for person in Person.with_softdeleted_objects.all():
                print(80 * "-")
                print(f"{person=}")

                new_first_name, new_last_name = unique_name_pair(fake, used_person_names)
                new_udb_first_name, new_udb_last_name = unique_name_pair(fake, used_udb_person_names)
                new_email = unique_value(fake.email, used_emails)
                new_udb_email_private = unique_value(fake.email, used_udb_emails_private)
                new_udb_email_internal_business = unique_value(fake.email, used_udb_emails_internal_business)

                print(f"first_name: {person.first_name!r} -> {new_first_name!r}")
                print(f"last_name: {person.last_name!r} -> {new_last_name!r}")
                print(f"udb_person_first_name: {person.udb_person_first_name!r} -> {new_udb_first_name!r}")
                print(f"udb_person_last_name: {person.udb_person_last_name!r} -> {new_udb_last_name!r}")
                print(f"email: {person.email!r} -> {new_email!r}")
                print(f"udb_person_email_private: {person.udb_person_email_private!r} -> {new_udb_email_private!r}")
                print(
                    f"udb_person_email_internal_business: {person.udb_person_email_internal_business!r} -> "
                    f"{new_udb_email_internal_business!r}"
                )
                print(f"udb_person_image: {person.udb_person_image!r} -> ''")

                if write:
                    person.first_name = new_first_name
                    person.last_name = new_last_name
                    person.udb_person_first_name = new_udb_first_name
                    person.udb_person_last_name = new_udb_last_name
                    person.email = new_email
                    person.udb_person_email_private = new_udb_email_private
                    person.udb_person_email_internal_business = new_udb_email_internal_business
                    person.udb_person_image = ""
                    person.save(
                        update_fields=[
                            "first_name",
                            "last_name",
                            "udb_person_first_name",
                            "udb_person_last_name",
                            "email",
                            "udb_person_email_private",
                            "udb_person_email_internal_business",
                            "udb_person_image",
                        ]
                    )

                persons_touched += 1

            devices_touched = 0
            for device in Device.with_softdeleted_objects.exclude(serial_number__isnull=True).exclude(
                serial_number__exact=""
            ):
                print(80 * "-")
                print(f"{device=}")

                new_serial_number = fake.bothify(text="SN-????-#####", letters=string.ascii_uppercase)
                print(f"serial_number: {device.serial_number!r} -> {new_serial_number!r}")

                if write:
                    device.serial_number = new_serial_number
                    device.save(update_fields=["serial_number"])

                devices_touched += 1

            # CustomUser logs in via its unique email (USERNAME_FIELD), so the
            # printed old -> new email mapping is the only way to know the new
            # login credentials. Passwords are left untouched.
            UserModel = get_user_model()
            used_usernames = set(filter(None, UserModel.objects.values_list("username", flat=True)))
            used_user_emails = set(filter(None, UserModel.objects.values_list("email", flat=True)))

            users_touched = 0
            # The udb-sync actor is looked up by this exact email in
            # dataexchange/udb_sync.py and carries no personal data.
            for user in UserModel.objects.exclude(email="udb-sync@dlcdb.invalid"):
                print(80 * "-")
                print(f"{user=}")

                new_username = unique_value(fake.user_name, used_usernames)
                new_first_name = fake.first_name()
                new_last_name = fake.last_name()
                new_email = unique_value(fake.email, used_user_emails)

                print(f"username: {user.username!r} -> {new_username!r}")
                print(f"first_name: {user.first_name!r} -> {new_first_name!r}")
                print(f"last_name: {user.last_name!r} -> {new_last_name!r}")
                print(f"email (login): {user.email!r} -> {new_email!r}")

                if write:
                    user.username = new_username
                    user.first_name = new_first_name
                    user.last_name = new_last_name
                    user.email = new_email
                    user.save(update_fields=["username", "first_name", "last_name", "email"])

                users_touched += 1

            if not write:
                # Dryrun: nothing above actually wrote to the db, but roll back
                # regardless in case any save() call above slipped through.
                transaction.set_rollback(True)

        print(80 * "-")
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Anonymized' if write else '[Dryrun] Would anonymize'}: "
                f"{persons_touched} person(s), {devices_touched} device(s), {users_touched} user(s)."
            )
        )

        if write:
            self.stdout.write(self.style.WARNING(f"Database file: {db_path}"))
            self.stdout.write(self.style.WARNING(f"Backup file: {backup_path}"))
            self.stdout.write(
                self.style.WARNING(
                    "User login emails have changed - see the printed mapping above. Passwords are unchanged."
                )
            )
