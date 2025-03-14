# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import traceback
from django import forms
from django.contrib import messages

from ..utils.bulk_management import set_removed_record


class RemoverListAdminForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get("file")
        username = self.request.user.username

        try:
            print("Dry-run import_data...")
            result_dryrun = set_removed_record(
                file,
                username=username,
                write=False,
            )
        except Exception:
            print(traceback.format_exc())
            # Re-raise the original exception with its full context
            raise
        else:
            messages.info(self.request, result_dryrun)
