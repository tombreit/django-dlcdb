# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth.decorators import permission_required
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView

from ..forms.procure_forms import ProcureForm


@method_decorator(
    permission_required("core.transition_can_order_device", raise_exception=True),
    name="dispatch",
)
class ProcureDeviceView(CreateView):
    form_class = ProcureForm
    success_url = reverse_lazy("admin:core_orderedrecord_changelist")
    template_name = "core/orderedrecord/procure.html"
