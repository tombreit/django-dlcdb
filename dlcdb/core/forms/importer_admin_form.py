from django import forms
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db import IntegrityError

from ..utils.bulk_management import import_data


class ImporterAdminForm(forms.ModelForm):

    def clean_file(self):
        file = self.cleaned_data['file']

        # try:
        #     validate_csv(
        #         self.file,
        #         valid_col_headers=self.VALID_COL_HEADERS,
        #         date_fields=self.DATE_FIELDS,
        #         bulk_mode='import_devices',
        #     )
        # except BaseException as base_exception:
        #     raise base_exception

        try:
            print("Dry-run import_data...")
            result_dryrun = import_data(file, importer_inst_pk=None, valid_col_headers=self.instance.VALID_COL_HEADERS, write=False)
            messages.info(self.request, result_dryrun)
        except IntegrityError as integrity_error:
            msg = integrity_error
            messages.error(self.request, msg)
            raise ValidationError(msg)

        # Always return a value to use as the new cleaned data, even if
        # this method didn't change it.
        return file
