from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from ..forms.adminactions_forms import RelocateActionForm
from ..models import Device, InRoomRecord, Room, Record


@method_decorator(login_required, name='dispatch')
class DevicesRelocateView(FormView):
    success_url = reverse_lazy('admin:core_device_changelist')
    template_name = 'core/actions/relocate.html'
    form_class = RelocateActionForm

    def get_initial(self):
        initial = super().get_initial()

        device_ids = self.request.GET.get('ids').split(",")
        devices = Device.objects.filter(pk__in=device_ids)

        initial.update({
            'user': self.request.user,
            'device_ids': device_ids,
            'devices': devices,
            'ct': self.request.GET.get('ct'),
        })

        return initial

    def form_valid(self, form):
        selected_instances = self.get_initial().get('devices')
        user = self.get_initial().get('user')
        new_room = form.cleaned_data.get('new_room')

        if new_room is None:
            self.add_error("new_room", "No new room given!")

        self.relocate_devices(selected_instances, new_room, user)
        return super().form_valid(form)

    def relocate_devices(self, devices, new_room, user):
        for device in devices:
            # print(f"Processing device: {device}...")

            if hasattr(device.active_record, "record_type") and device.active_record.record_type == Record.LENT:
                device.active_record.room = new_room
                device.active_record.save()

                update_msg = f"Device <{device}> has record type <{device.active_record.record_type}> - just updating the room for the current LENT record." 
                messages.add_message(self.request, messages.INFO, update_msg)

            elif hasattr(device.active_record, "record_type") and device.active_record.record_type == Record.REMOVED:
                error_msg = f"Device <{device}> has record type <{device.active_record.record_type}> - this device should not be here anymore. Not relocating this device!"
                messages.add_message(self.request, messages.WARNING, error_msg)
                continue

            elif hasattr(device.active_record, "record_type") and device.active_record.room == new_room:
                error_msg = f"Device <{device}> has record type <{device.active_record.record_type}> and is already in room <{new_room}>. No need to relocate this device!"
                messages.add_message(self.request, messages.WARNING, error_msg)
                continue

            else:
                record_obj, created = InRoomRecord.objects.get_or_create(
                    device=device,
                    room=new_room,
                    user=user,
                    username=user.username,
                )
                
                update_msg = f"Device <{device}> has record type <{device.active_record.record_type}>. Creating a new INROOM record for room <{new_room}>." 
                messages.add_message(self.request, messages.INFO, update_msg)

        return
