from django.views.generic import DetailView

from ..models.prx_lentrecord import LentRecord


class PrintLentSheetView(DetailView):
    """
    Renders the print view for the Ausleihzettel.
    """
    model = LentRecord
    template_name = 'core/lentrecord/lentrecord_lent_sheet.html'
    context_object_name = 'record'
