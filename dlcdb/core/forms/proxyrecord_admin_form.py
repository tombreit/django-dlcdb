# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms


class ProxyRecordAdminForm(forms.ModelForm):
    class Media:
        # css = {'all': ('core/proxyrecord_admin/add_form.css',)}
        js = ("core/proxyrecord_admin/add_form.js",)
