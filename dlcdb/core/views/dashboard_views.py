import json

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from ..models.inventory import Inventory
from ..models.device import Device

from dlcdb.core import stats


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    template_name = 'admin/dashboard.html'

    def get_context_data(self):
        return dict(
            record_fraction_data=json.dumps(stats.get_record_fraction_data()),
            device_type_data=json.dumps(stats.get_device_type_data()),
            current_inventory=Inventory.objects.filter(is_active=True).order_by('-created_at').first(),
            device_count=Device.objects.all().count(),
        )
