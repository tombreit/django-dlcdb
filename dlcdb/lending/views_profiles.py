# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The lending profiles: one per device type, with the lending slip template, the
preparation checklist and the regulations. A ModelViewSet (theme/viewsets.py)
with a field history; Settings › Lending profiles lists them. Profiles are
global, like device types: no tenant scoping.
"""

from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from dlcdb.theme.viewsets import Column, CreateView, EditView, HistoryView, ModelViewSet

from .forms import LendingProfileForm
from .models import LendingProfile
from .starter import restore_empty

PRESENT = "theme/viewsets/cells/_present.html"


def _restore_starter_content(request, form):
    """An emptied slip template or checklist gets the starter content again, and the user is told."""
    for field in restore_empty(form.instance):
        messages.info(request, _("“%(field)s” was empty and holds the starter content again.") % {"field": field})


class ProfileCreateView(CreateView):
    def form_valid(self, form):
        _restore_starter_content(self.request, form)
        return super().form_valid(form)


class ProfileEditView(EditView):
    def form_valid(self, form):
        _restore_starter_content(self.request, form)
        return super().form_valid(form)


class LendingProfileViewSet(ModelViewSet):
    model = LendingProfile
    form_class = LendingProfileForm
    form_fields_template = "lending/includes/_profile_fields.html"
    icon = "bi-card-checklist"
    url_namespace = "profile"
    list_display = [
        Column("device_type", gettext_lazy("Device type"), sort_key="device_type__name"),
        Column(
            "lent_sheet_template", gettext_lazy("Slip template"), classname="text-center", cell_template_name=PRESENT
        ),
        Column(
            "lending_preparation_checklist",
            gettext_lazy("Checklist"),
            classname="text-center",
            cell_template_name=PRESENT,
        ),
    ]
    search_fields = ["device_type__name"]
    ordering = "device_type__name"
    add_view_class = ProfileCreateView
    edit_view_class = ProfileEditView
    history_view_class = HistoryView

    def get_queryset(self):
        return LendingProfile.objects.select_related("device_type")
