from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from dlcdb.lending.models import LendingConfiguration
from dlcdb.core.models.prx_lentrecord import LentRecord


def print_lent_sheet(request, pk):
    template_name = 'core/lentrecord/lentrecord_lent_sheet.html'
    context = {
        'record': get_object_or_404(LentRecord, pk=pk),
        'lending_configuration': LendingConfiguration.load(),
    }
    return TemplateResponse(request, template_name, context)
