# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The standalone Room frontend: list, add and edit rooms outside the admin."""

import csv
from operator import itemgetter

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from dlcdb.core.models import Room
from dlcdb.core.models.room import RoomReconcile
from dlcdb.core.utils.helpers import get_denormalized_user
from dlcdb.theme.filterbar import build_filterbar
from dlcdb.theme.pagination import paginate

from .filters import RoomFilter
from .forms import RoomForm

ROOMS_PER_PAGE = 25


def _room_queryset():
    """
    Rooms visible in the frontend (the default manager already excludes
    soft-deleted rooms), each annotated with the count of devices currently in
    the room — the same count the admin's DeviceCountMixin shows.
    """
    return Room.objects.annotate(assets_count=Count("record", distinct=True, filter=Q(record__is_active=True)))


@permission_required("core.view_room", raise_exception=True)
def room_index(request):
    """Room overview, with progressive HTMX filtering."""
    template = "rooms/index.html#room-list" if request.htmx else "rooms/index.html"
    base_queryset = _room_queryset()

    data = request.GET.copy()
    data.setdefault("ordering", "number")
    room_filter = RoomFilter(data, queryset=base_queryset, request=request)

    page_obj = paginate(request, room_filter.qs, ROOMS_PER_PAGE)

    context = {
        "filter": room_filter,
        "page_obj": page_obj,
        "filterbar": build_filterbar(
            room_filter,
            request,
            target="#room-list",
            search_placeholder=_("Search number, nickname, description..."),
        ),
        "current_ordering": data["ordering"],
        "room_filtered_count": page_obj.paginator.count,
        "room_total_count": base_queryset.count(),
    }
    return TemplateResponse(request, template, context)


@permission_required("core.add_room", raise_exception=True)
def room_add(request):
    """Create a room and attach its audit information to the current user."""
    form = RoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        room = form.save(commit=False)
        room.user, room.username = get_denormalized_user(request.user)
        # Room.save() generates the QR code and keeps the single
        # auto-return/external room invariants.
        room.save()
        messages.success(request, _("Room “%(room)s” was created.") % {"room": room})
        return redirect("rooms:detail", pk=room.pk)

    return TemplateResponse(
        request,
        "rooms/form.html",
        {"form": form, "title": _("Add room"), "submit_label": _("Create room")},
    )


@permission_required("core.view_room", raise_exception=True)
def room_detail(request, pk):
    """Read and edit one room in the same straightforward page."""
    room = get_object_or_404(_room_queryset(), pk=pk)
    can_change = request.user.has_perm("core.change_room")

    # The index threads its active search/filter/sort here as ?next= so Save,
    # Back and Cancel return to the exact filtered list.
    next_query = request.GET.get("next", "")
    index_url = reverse("rooms:index")
    if next_query:
        index_url = f"{index_url}?{next_query}"
    form_action = reverse("rooms:detail", args=[room.pk])
    if next_query:
        form_action += "?" + urlencode({"next": next_query})

    if request.method == "POST":
        if not can_change:
            raise PermissionDenied
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            saved_room = form.save(commit=False)
            saved_room.user, saved_room.username = get_denormalized_user(request.user)
            saved_room.save()
            messages.success(request, _("Room “%(room)s” was updated.") % {"room": saved_room})
            return redirect(index_url)
    else:
        form = RoomForm(instance=room)

    return TemplateResponse(
        request,
        "rooms/detail.html",
        {
            "room": room,
            "form": form,
            "can_change": can_change,
            "index_url": index_url,
            "form_action": form_action,
        },
    )


class ReconcileRoomsView(PermissionRequiredMixin, TemplateView):
    """
    Compare the DLCDB rooms against an uploaded Archibus CSV export. Reached
    from the RoomReconcile admin changelist (moved unchanged from dlcdb.core,
    now with a permission gate).
    """

    permission_required = "core.view_roomreconcile"
    raise_exception = True
    template_name = "rooms/reconcile_rooms.html"

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
