# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms


class ProxyRecordAdminForm(forms.ModelForm):
    class Media:
        js = ("core/proxyrecord_admin/add_form.js",)
