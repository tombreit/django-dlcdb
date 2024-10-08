# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import csv
from operator import itemgetter

from django.views.generic import TemplateView

from ..models import Room
from ..models.room import RoomReconcile


class ReconcileRoomsView(TemplateView):
    template_name = "core/room/reconcile_rooms.html"

    def cleanup_file(self, file):
        cleaned_data = []
        # cleaned_file = io.StringIO()

        with open(file.path, mode="r", encoding="utf-8-sig") as infile:
            # print(f"{type(infile)=}")
            # print(f"{infile=}")
            # print(f"{dir(infile)=}")

            data = infile.readlines()

            for index, line in enumerate(data):
                # print(f"{index=}, {line=}")

                if index == 0 and line.startswith("#"):
                    line = line.replace("#", "", 1)
                    cleaned_data.append(line)
                elif index == 1 and line.startswith("#"):
                    continue
                else:
                    cleaned_data.append(line)

            # cleaned_file.write('\n'.join(cleaned_data))
            return cleaned_data

    def get_rooms_reconcile(self, room_reconcile_obj):
        # print(f"get_rooms_reconcile room_reconcile_ob: {room_reconcile_obj=}")
        room_reconcile_file = room_reconcile_obj.file

        dlcdb_rooms = Room.objects.all()
        dlcdb_rooms_matched = set()
        room_reconciliation = []

        archibus_building_fue = "STRA-SFU"
        # archibus_building_gue = "STRA-MST"
        # archibus_building_rat = "STRA-M01"

        css_classes_notmatched = "bg-warning"
        css_classes_matched = "bg-success text-white"

        csv_list = self.cleanup_file(room_reconcile_file)  # .read().decode('utf-8')
        # print(f"{file.getvalue()=}")

        csv_dict_reader = csv.DictReader(csv_list, delimiter=",")  # io.StringIO(file)
        # print(f"{csv_dict_reader=}")

        # Search for csv_rooms:
        for row in csv_dict_reader:
            csv_room = dlcdb_room = None

            # print(f'\trm_id: {row["rm_id"]}; name: {row["name"]}')

            csv_building_id = row["rm.bl_id"]
            csv_room = row["rm_id"]
            csv_room_name = row["name"]
            building_prefix = ""

            if csv_building_id == archibus_building_fue:
                building_prefix = "F"

            try:
                dlcdb_room = dlcdb_rooms.get(number=f"{building_prefix}{csv_room}")
                dlcdb_rooms_matched.add(dlcdb_room.pk)
                dlcdb_room_str = f"{dlcdb_room.number} {dlcdb_room.nickname}"
                css_classes = css_classes_matched
            except Room.DoesNotExist:
                dlcdb_room_str = "-"
                css_classes = css_classes_notmatched

            csv_room = f"{csv_room} ({csv_building_id}) {csv_room_name}"

            room_reconciliation.append(
                {
                    "css_classes": css_classes,
                    "dlcdb_room": dlcdb_room_str,
                    "csv_room": csv_room,
                }
            )

        # Search for dlcdb rooms:
        non_matched_dlcdb_rooms = Room.objects.exclude(pk__in=dlcdb_rooms_matched)

        for r in non_matched_dlcdb_rooms:
            room_reconciliation.append(
                {
                    "css_classes": css_classes_notmatched,
                    "dlcdb_room": f"{r.number} {r.nickname}",
                    "csv_room": "-",
                }
            )

        # from pprint import pprint
        # pprint(room_reconciliation)

        room_reconciliation_sorted = sorted(room_reconciliation, key=itemgetter("dlcdb_room"))
        return room_reconciliation_sorted

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        room_reconcile_id = context["reconcile_id"]
        room_reconcile_obj = RoomReconcile.objects.get(id=room_reconcile_id)

        context.update(
            {
                "reconcile_file": room_reconcile_obj,
                "room_reconciliation": self.get_rooms_reconcile(room_reconcile_obj),
            }
        )
        return context
