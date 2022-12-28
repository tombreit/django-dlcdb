import csv
import os
import re
import pathlib
import timeit

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from dlcdb.core.models import Device, Record


class Command(BaseCommand):

    help = 'Fixes Records "modified_at" timestamp'

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode", 
            choices=["dryrun", "write"], default="dryrun",
            help='Simulate what to do. Basically a validation run.',
        )

    def handle(self, *args, **options):
        write = True if options['mode'] == "write" else False
        print(f"mode: {write=}")

        for device in Device.with_softdeleted_objects.all():
            print(80 * "-")
            print(f"{device=}")

            device_records = Record.objects.filter(device=device).order_by("-pk")

            former_created_at_ts = None
            for record in device_records:

                if not record.effective_until:
                    if write:
                        print("Mode is write, updating record...")
                        record.effective_until = former_created_at_ts
                        record.save(update_fields=['effective_until'])
                    else:
                        print(f"[Simulate] {record.id=}: created: {record.created_at:%Y-%m-%d %H:%M} mod: {record.modified_at:%Y-%m-%d %H:%M} -> former: {former_created_at_ts}")

                former_created_at_ts = record.created_at
