# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import gettext as _

from .. import lifecycle
from ..forms.adminactions_forms import RelocateActionForm
from ..models import Device
from ..utils.links import linked_message
from ..utils.relocate import relocate_device

# Reassigning a tenant or a device type is a plain device edit, not a lifecycle
# move -- and a tenant change moves a device between organisational scopes -- so
# it is gated separately from the relocation itself.
EDIT_DEVICE_PERM = "core.change_device"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(lifecycle.BY_NAME["relocate"].permission, raise_exception=True),
    name="dispatch",
)
class DevicesRelocateView(FormView):
    success_url = reverse_lazy("admin:core_device_changelist")
    template_name = "core/actions/relocate.html"
    form_class = RelocateActionForm

    def get_form_kwargs(self):
        """Added keyword 'is_superuser' for instantiating and validating the form."""
        kwargs = super().get_form_kwargs()
        kwargs["is_superuser"] = self.request.user.is_superuser
        return kwargs

    def get_initial(self):
        initial = super().get_initial()

        # A bare GET without ?ids= is a 404-shaped mistake, not a 500: treat a
        # missing or blank parameter as "no devices selected".
        device_ids = [pk for pk in (self.request.GET.get("ids") or "").split(",") if pk]
        devices = Device.objects.filter(pk__in=device_ids)

        initial.update(
            {
                "user": self.request.user,
                "device_ids": device_ids,
                "devices": devices,
                "ct": self.request.GET.get("ct"),
            }
        )

        return initial

    def form_valid(self, form):
        selected_instances = self.get_initial().get("devices")
        user = self.get_initial().get("user")
        new_room = form.cleaned_data.get("new_room")
        new_tenant = form.cleaned_data.get("new_tenant")
        new_device_type = form.cleaned_data.get("new_device_type")

        self.relocate_devices(selected_instances, new_room, user, new_tenant, new_device_type)
        return super().form_valid(form)

    def relocate_devices(self, devices, new_room, user, new_tenant, new_device_type):
        may_edit_device = user.has_perm(EDIT_DEVICE_PERM)
        if (new_tenant or new_device_type) and not may_edit_device:
            messages.add_message(
                self.request,
                messages.WARNING,
                _("Tenant and device type were left unchanged: you may move devices but not edit them."),
            )
            new_tenant = new_device_type = None

        for device in devices:
            # print(f"Processing device: {device}...")

            if new_tenant:
                device.tenant = new_tenant
                device.save()

                update_msg = linked_message(
                    "Device {device}: Set new tenant to {tenant}.", device=device, tenant=new_tenant
                )
                messages.add_message(self.request, messages.INFO, update_msg)

            if new_device_type:
                device.device_type = new_device_type
                device.save()

                update_msg = linked_message(
                    "Device {device}: Set device type to {device_type}.",
                    device=device,
                    device_type=new_device_type,
                )
                messages.add_message(self.request, messages.INFO, update_msg)

            if new_room:
                # Delegate the per-device room move to the shared state machine
                # so admin and frontend cannot diverge.
                result = relocate_device(device, new_room, user)
                messages.add_message(self.request, result.level, result.message)

        return
