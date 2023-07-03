"""
Inventory mode.

Goal: Verifiy all devices are "findable". 

Subgoals:
* Room inventory should always be "saveable", even when not all devices are verified
* ...

Procedure:

* Go in room
* Check if expected device is in room
* Cases:
  * [FOUND]     Expected device is in room: confirm device 
  * [NOT FOUND] Expected device is not in room: disprove device
  * [FOUND]     Not expected device is in room: add device to room and confirm device
* Room is finished, when all devices got their inventory stamp
"""

from datetime import date
import json
from collections import namedtuple

from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView, FormView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.base import TemplateView
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError, HttpResponseRedirect
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator

from rest_framework.authtoken.models import Token
from django_filters.views import FilterView

from dlcdb.core.models import Room, Device, Record, Inventory, LostRecord, LentRecord, Note
from dlcdb.core.utils.helpers import get_denormalized_user, get_user_email

from .utils import get_devices_for_room, create_sap_list_comparison
from .filters import RoomFilter
from .forms import InventorizeRoomForm, DeviceAddForm, NoteForm
from .models import SapList


def update_session_qrtoggle(request):
    if request.method == "POST":
        data = json.loads(request.body)
        request.session["qrscanner_enabled"] = data["qrScanner"]
        # print(f"{request.session['qrscanner_enabled']=}")
        return JsonResponse(data)
    else:
        return HttpResponse("")


def get_current_inventory():
    from dlcdb.core.models import Inventory

    try:
        current_inventory = Inventory.objects.get(is_active=True)
    except Inventory.DoesNotExist:
        current_inventory = None

    return current_inventory


class InventorizeRoomFormView(LoginRequiredMixin, SingleObjectMixin, FormView):
    template_name = "inventory/inventorize_room_detail.html"
    form_class = InventorizeRoomForm
    model = Room

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("inventory:inventorize-room", kwargs={"pk": self.object.pk})


class InventorizeRoomDetailView(LoginRequiredMixin, DetailView):
    model = Room
    queryset = Room.inventory_objects.all()
    context_object_name = "room"
    template_name = "inventory/inventorize_room_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_context_data(self, **kwargs):
        # print(f"get_contex_data self.object.pk: {self.object.pk}")
        current_inventory = get_current_inventory

        # Get all devices in this room:
        devices = get_devices_for_room(self.request, self.object.pk)

        form = InventorizeRoomForm(
            initial={
                # 'room': self.object.pk,
                # 'uuids': self.object.get_inventory_status.inventorized_uuids,
            }
        )

        # Allow only adding devices which are not already present in this room:
        valid_add_devices = Device.objects.exclude(active_record__room=self.object.pk)
        device_choices = [("", "Add device")]
        device_choices += [(f"{str(d.uuid)}", f"{d.edv_id} {d.sap_id}") for d in valid_add_devices]

        device_add_form = DeviceAddForm(
            device_choices=device_choices,
            initial={
                "room": self.object.pk,
            },
        )

        context = super().get_context_data(**kwargs)
        context.update(
            {
                "devices": devices,
                "current_inventory": current_inventory,
                "qrcode_prefix": settings.QRCODE_PREFIX,
                "debug": settings.DEBUG,
                "dev_state_unknown": "dev_state_unknown",
                "dev_state_found": "dev_state_found",
                # 'dev_state_found_unexpected': 'dev_state_found_unexpected',
                "dev_state_notfound": "dev_state_notfound",
                "dev_state_added": "dev_state_added",
                "form": form,
                "device_add_form": device_add_form,
                "api_token": Token.objects.first(),
            }
        )
        return context


class InventorizeRoomView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        view = InventorizeRoomDetailView.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = InventorizeRoomFormView.as_view()

        _uuids = request.POST.get("uuids")
        _room_pk = self.kwargs.get("pk")

        try:
            room = Room.objects.get(pk=_room_pk)
        except Room.DoesNotExist:
            return HttpResponseServerError(
                f"<h4>Server Error 500</h4><p>Something went wrong. A room with pk={_room_pk} does not exist. Please contact your it staff.</p>"
            )

        if _uuids:
            current_inventory = Inventory.objects.get(is_active=True)
            user, username = get_denormalized_user(request.user)
            uuids_states_dict = json.loads(_uuids)

            try:
                external_room = Room.objects.get(is_external=True)
            except Room.DoesNotExist:
                return HttpResponseServerError(
                    "<h4>Server Error 500</h4><p>Something went wrong. No room is flagged with 'is_external'. Please contact your it staff.</p>"
                )

            for uuid, state in uuids_states_dict.items():
                device = Device.objects.get(uuid=uuid)
                active_record = device.active_record
                print(f"uuid: {uuid}, state: {state}, device: {device}, active_record: {active_record}")

                new_record = None

                if state == "dev_state_found":
                    print("state == 'dev_state_found'")
                    new_record = active_record
                    new_record.pk = new_record.id = None
                    new_record.room = room
                    new_record.inventory = current_inventory
                    new_record.user = user
                    new_record.username = username

                    if new_record.record_type == Record.LOST:
                        new_record.record_type = Record.INROOM

                    new_record._state.adding = True
                    new_record.save()

                elif state == "dev_state_notfound":
                    """
                    If an expected device is not found in a given room, we need
                    to check if it is currently lended. When lended, we do not
                    set this device as "not found", but instead move it to an
                    "external room".
                    """
                    print("state == 'dev_state_notfound'")

                    if all(
                        [
                            active_record.record_type == Record.LENT,
                            active_record.room != external_room,
                        ]
                    ):
                        active_record.room = external_room
                        active_record.save()

                        # Set inventory note
                        # TODO: Fix multiple injections of same note string
                        lent_not_found_msg = f"Lented asset not found in expected location `{active_record.room}`. Please contact lender."
                        note_obj, note_obj_created = Note.objects.get_or_create(
                            inventory=current_inventory,
                            device=active_record.device,
                            room=external_room,
                        )
                        note_obj.text = f"{note_obj.text} *** {lent_not_found_msg}"
                        note_obj.save()
                    else:
                        new_record = LostRecord(
                            device=device,
                            inventory=current_inventory,
                            user=user,
                            username=username,
                        )

                elif state == "dev_state_unknown":
                    print("state == 'dev_state_unknown'")
                    new_record = active_record
                    new_record.pk = new_record.id = None
                    new_record.room = room
                    new_record.inventory = None
                    new_record.user = user
                    new_record.username = username
                    new_record._state.adding = True
                    new_record.save()

                else:
                    msg = f"This should never happen: given state `{state}` not recognized! Raising 500."
                    print(msg)
                    return HttpResponseServerError(msg)

                if new_record:
                    new_record.save()

        return view(request, *args, **kwargs)


class InventorizeRoomListView(LoginRequiredMixin, FilterView):
    model = Room
    context_object_name = "rooms"
    queryset = Room.inventory_objects.all()
    filterset_class = RoomFilter

    def get_template_names(self):
        if self.request.htmx:
            return ["inventory/partials/room_list.html"]
        else:
            return ["inventory/inventorize_room_list.html"]

    @staticmethod
    def get_inventory_progress():
        inventory_progress = namedtuple(
            "inventory_progress",
            [
                "done_percent",
                "all_devices_count",
                "inventorized_devices_count",
            ],
        )

        done_percent = 0
        current_inventory = Inventory.objects.get(is_active=True)
        all_devices = Record.objects.active_records().exclude(record_type=Record.REMOVED)
        inventorized_devices_count = all_devices.filter(inventory=current_inventory).count()
        all_devices_count = all_devices.count()

        if all(
            [
                current_inventory,
                all_devices,
            ]
        ):
            done_percent = (inventorized_devices_count * 100) / all_devices_count
            done_percent = int(round(done_percent, 0))
            return inventory_progress(done_percent, all_devices_count, inventorized_devices_count)

    def get_context_data(self, **kwargs):
        _request_copy = self.request.GET.copy()
        parameters = _request_copy.pop("page", True) and _request_copy.urlencode()

        try:
            current_inventory = Inventory.objects.get(is_active=True)
        except Inventory.DoesNotExist:
            current_inventory = None

        context = super().get_context_data(**kwargs)
        context.update(
            {
                "current_inventory": current_inventory,
                "parameters": parameters,
                "qrcode_prefix": settings.QRCODE_PREFIX,
                "debug": settings.DEBUG,
                "api_token": Token.objects.first(),
                "inventory_progress": self.get_inventory_progress,
            }
        )
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)

        if self.request.htmx and self.request.META.get("QUERY_STRING"):
            response["HX-Push-Url"] = f"{self.request.path}?{self.request.META.get('QUERY_STRING')}"

        return response


class DevicesSearchView(ListView):
    template_name = "inventory/inventorize_devices_list.html"
    model = Device

    def get_queryset(self):
        name = self.kwargs.get("name", "")
        object_list = self.model.objects.all()
        if name:
            object_list = object_list.filter(name__icontains=name)
        return object_list

    def django_admin_keyword_search(model, keywords, search_fields):
        """Search according to fields defined in Admin's search_fields"""
        all_queries = None

        for keyword in keywords.split(" "):  # breaks query_string into 'Foo' and 'Bar'
            keyword_query = None

            for field in search_fields:
                each_query = Q(**{field + "__icontains": keyword})

                if not keyword_query:
                    keyword_query = each_query
                else:
                    keyword_query = keyword_query | each_query

            if not all_queries:
                all_queries = keyword_query
            else:
                all_queries = all_queries & keyword_query

        result_set = model.objects.filter(all_queries).distinct()

        return result_set


class QrCodesForRoomDetailView(LoginRequiredMixin, DetailView):
    model = Room
    context_object_name = "room"
    template_name = "inventory/room_qrcodes_detail.html"

    def get_context_data(self, **kwargs):
        # Get all devices in given room.
        devices = get_devices_for_room(self.request, self.object.pk)

        context = super().get_context_data(**kwargs)
        context["devices"] = devices
        return context


class InventoryReportView(TemplateView):
    template_name = "inventory/inventorize_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "devices": LentRecord.get_devices(inventory=get_current_inventory()).order_by("sap_id"),
                "now": date.today(),
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class SapCompareListView(DetailView):
    model = SapList

    def get(self, request, *args, **kwargs):
        return render(request, "inventory/compare_sap_list.html", dict(sap_list=self.get_object()))

    def post(self, request, *args, **kwargs):
        sap_list = self.get_object()
        create_sap_list_comparison(sap_list)
        messages.success(request, "Abgleich erzeugt")
        return HttpResponseRedirect(reverse("inventory:compare-sap-list", kwargs=dict(pk=sap_list.pk)))


def get_note_btn(request, obj_type, obj_uuid):
    if obj_type == "device":
        obj = Device.objects.get(uuid=obj_uuid)
    elif obj_type == "room":
        obj = Room.objects.get(uuid=obj_uuid)

    return render(
        request,
        "inventory/includes/note_btn.html",
        {"obj_type": obj_type, "obj_uuid": obj_uuid, "obj": obj}
    )


def update_note_view(request, obj_type, obj_uuid):
    inventory = get_current_inventory()
    request_user_email = get_user_email(request.user)

    if obj_type == "room":
        obj = Room.objects.get(uuid=obj_uuid)
    elif obj_type == "device":
        obj = Device.objects.get(uuid=obj_uuid)

    hx_post_url = reverse("inventory:note-update", args=[obj_type, obj.uuid])

    note = None
    if obj.get_latest_note:
        note = obj.get_latest_note()
    else:
        print(f"No note for obj {obj} found, creating a new one")

    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = NoteForm(
            request.POST,
            instance=note,
            hx_post_url=hx_post_url,
        )

        if form.is_valid():
            instance = form.save(commit=False)
            if not note:
                # Dealing with a new note instance
                instance.created_by = request_user_email
            instance.updated_by = request_user_email
            instance.inventory = inventory

            # instance.room = room
            setattr(instance, obj_type, obj)

            instance.save()
            form.save()

            message = "{obj} note {action}".format(
                obj=obj,
                action="edited" if note else "added",
            )

            headers = {
                "HX-Trigger": json.dumps(
                    {
                        "objectListChanged": None,
                        "showMessage": message,
                    }
                ),
            }

            if request.htmx and request.META.get("QUERY_STRING"):
                headers["HX-Push-Url"] = f"{request.path}?{request.META.get('QUERY_STRING')}"

            return HttpResponse(
                status=204,
                headers=headers,
            )

    # if a GET (or any other method) we'll create a blank form
    else:
        form = NoteForm(
            instance=note if note else None,
            hx_post_url=hx_post_url,
        )

    context = {
        "note_object": obj,
        "hx_post_url": hx_post_url,
        "form": form,
    }
    template = "inventory/includes/note_form.html"

    return render(request, template, context)
