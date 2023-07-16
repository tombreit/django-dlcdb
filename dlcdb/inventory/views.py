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

TODO:
* Move domain-specific methods to the Inventory class (eg InventorizeRoomView.post stuff)
* Move queryset getters to Inventory class
* Refactor some CBVs to be FBVs
"""

import json
from datetime import date

from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.base import TemplateView
from django.http import (HttpResponse, HttpResponseForbidden, 
                         HttpResponseServerError, HttpResponseRedirect,
                         JsonResponse)
from django.template.response import TemplateResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.authtoken.models import Token
from django_filters.views import FilterView

from dlcdb.core.models import Room, Device, Inventory
from dlcdb.core.utils.helpers import get_user_email

from .utils import create_sap_list_comparison
from .filters import RoomFilter, DeviceFilter
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
    context_object_name = "room"
    template_name = "inventory/inventorize_room_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_queryset(self):
        return Inventory.objects.tenant_aware_room_objects(self.request.tenant)

    def get_context_data(self, **kwargs):
        # print(f"get_contex_data self.object.pk: {self.object.pk}")
        current_inventory = Inventory.objects.active_inventory()

        # Get all devices in this room:
        devices = Inventory.objects.devices_for_room(self.object.pk, tenant=self.request.tenant, is_superuser=self.request.user.is_superuser)

        form = InventorizeRoomForm(
            initial={
                # 'room': self.object.pk,
                # 'uuids': self.object.get_inventory_status.inventorized_uuids,
            }
        )

        # Allow only adding devices which are not already present in this room:
        valid_add_devices_qs = (
            Device
            .objects
            .exclude(active_record__room=self.object.pk)
        )

        if self.request.tenant:
            valid_add_devices_qs = valid_add_devices_qs.filter(
                tenant=self.request.tenant
            )

        device_choices = [("", "Add device")]
        device_choices += [(f"{str(d.uuid)}", f"{d.edv_id} {d.sap_id}") for d in valid_add_devices_qs]

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

        uuids = request.POST.get("uuids")
        room_pk = self.kwargs.get("pk")

        try:
            if uuids:
                Inventory.inventorize_uuids_for_room(uuids=uuids, room_pk=room_pk, user=request.user)
            else:
                messages.add_message(request, messages.WARNING, "Nothing marked as inventorized.")
        except RuntimeError as runtime_error:
            return HttpResponseServerError(runtime_error)
        except ObjectDoesNotExist as object_does_not_exist:
            return HttpResponseServerError(object_does_not_exist)

        return view(request, *args, **kwargs)


class InventorizeRoomListView(LoginRequiredMixin, FilterView):
    model = Room
    context_object_name = "rooms"
    filterset_class = RoomFilter

    def get_queryset(self):
        return Inventory.objects.tenant_aware_room_objects(self.request.tenant)

    def get_template_names(self):
        if self.request.htmx:
            return ["inventory/partials/room_list.html"]
        else:
            return ["inventory/inventorize_room_list.html"]

    def get_context_data(self, **kwargs):
        # Capture URL query parameters to persist pagination
        _request_copy = self.request.GET.copy()
        parameters = _request_copy.pop("page", True) and _request_copy.urlencode()

        current_inventory = Inventory.objects.active_inventory()

        context = super().get_context_data(**kwargs)
        context.update(
            {
                "current_inventory": current_inventory,
                "parameters": parameters,
                "qrcode_prefix": settings.QRCODE_PREFIX,
                "debug": settings.DEBUG,
                "api_token": Token.objects.first(),
                "inventory_progress": current_inventory.get_inventory_progress(tenant=self.request.tenant),
            }
        )
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)

        if self.request.htmx and self.request.META.get("QUERY_STRING"):
            response["HX-Push-Url"] = f"{self.request.path}?{self.request.META.get('QUERY_STRING')}"

        return response


def search_devices(request):
    if request.htmx:
        template = "inventory/partials/device_search.html"
    else:
        template = 'inventory/device_search.html'

    devices = Inventory.objects.tenant_unaware_device_objects()
    filter_devices = DeviceFilter(request.GET, queryset=devices)

    request_copy = request.GET.copy()
    parameters = request_copy.pop('page', True) and request_copy.urlencode()

    paginator = Paginator(filter_devices.qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "current_inventory": Inventory.objects.active_inventory(),
        'page_obj': page_obj,
        'filter_devices': filter_devices,
        'parameters': parameters,
    }
    return TemplateResponse(request, template, context)


class QrCodesForRoomDetailView(LoginRequiredMixin, DetailView):
    model = Room
    context_object_name = "room"
    template_name = "inventory/room_qrcodes_detail.html"

    def get_context_data(self, **kwargs):
        devices = Inventory.objects.devices_for_room(self.object.pk, tenant=self.request.tenant, is_superuser=self.request.user.is_superuser)
        context = super().get_context_data(**kwargs)
        context["devices"] = devices
        return context


class InventoryReportView(TemplateView):
    template_name = "inventory/inventorize_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "devices": Inventory.objects.lent_devices().order_by("sap_id"),
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
    inventory = Inventory.objects.active_inventory()
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
