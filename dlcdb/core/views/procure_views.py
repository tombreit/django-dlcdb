from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView

from ..forms.procure_forms import ProcureForm


@method_decorator(login_required, name='dispatch')
class ProcureDeviceView(CreateView):
    form_class = ProcureForm
    success_url = reverse_lazy('admin:core_orderedrecord_changelist')
    template_name = 'core/orderedrecord/procure.html'
