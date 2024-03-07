# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.core.management.base import BaseCommand
from django.conf import settings
from dlcdb.core.models import Device, Room
from dlcdb.inventory.utils import uuid2qrcode


class Command(BaseCommand):
    help = "(Re-)Generates QR codes for every device and every room."

    def handle(self, *args, **options):
        for device in Device.objects.all():
            print("Processing device: ", device)
            qrcode = uuid2qrcode(device.uuid, infix=settings.QRCODE_INFIXES.get("device"))
            print("Qr_filename: ", qrcode.filename)
            device.qrcode.save(qrcode.filename, qrcode.fileobj, save=True)

        for room in Room.objects.all():
            print("Processing room: ", room)
            qrcode = uuid2qrcode(room.uuid, infix=settings.QRCODE_INFIXES.get("room"))
            print("Qr_filename: ", qrcode.filename)
            room.qrcode.save(qrcode.filename, qrcode.fileobj, save=True)
