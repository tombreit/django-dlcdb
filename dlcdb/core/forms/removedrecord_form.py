# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.utils.translation import gettext_lazy as _

from .. import lifecycle
from ..models import Record
from .proxyrecord_admin_form import ProxyRecordAdminForm


class RemovedRecordAdminForm(ProxyRecordAdminForm):
    def clean(self):
        # Legality (which states may be removed) comes from the lifecycle table,
        # not a hardcoded state check -- so this guard and the write-time
        # enforcement cannot drift. state_of() treats "no active record" as a
        # state of its own, so a device without any record is rejected gracefully
        # instead of raising AttributeError.
        device = self.cleaned_data.get("device")
        if device is None:
            return self.cleaned_data

        state = lifecycle.state_of(device)
        if state == Record.REMOVED:
            raise forms.ValidationError(_('Record already of type "REMOVED" - can not be removed again!'))
        # The bulk remover may decommission a bare device (None -> REMOVED is a
        # legal initial transition), but the admin add-form should not: a device
        # with no record has no state to remove from -- localize it first.
        if state is None:
            raise forms.ValidationError(_("This device has no record yet and cannot be removed. Localize it first."))
        if not lifecycle.can_transition(state, Record.REMOVED):
            raise forms.ValidationError(_("This device cannot be removed in its current state."))
        return self.cleaned_data
