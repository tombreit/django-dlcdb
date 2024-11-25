from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column
from crispy_bootstrap5.bootstrap5 import FloatingField

from django.db.models import Q
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from dlcdb.core.models import Device, DeviceType


class LicenseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit device-type choices to "License-type" choices
        self.fields["device_type"].queryset = DeviceType.objects.filter(
            Q(name__startswith="Lizenz::") | Q(name__startswith="License::") | Q(name__startswith="Licence::")
        )

        # Crispy forms
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column(FloatingField("sap_id"), css_class="col-md-6"),
            ),
            FloatingField("subscribers"),
            Row(
                Column(FloatingField("maintenance_contract_expiration_date"), css_class="col-md-6"),
                Column(FloatingField("device_type"), css_class="col-md-6"),
            ),
            Row(
                Column(FloatingField("manufacturer"), css_class="col-md-6"),
                Column(FloatingField("series"), css_class="col-md-6"),
            ),
            Row(Column("note", css_class="col-md-6")),
        )

    subscribers = forms.CharField(
        required=False,
        help_text="Enter email addresses separated by comma.",
    )

    def clean_subscribers(self):
        subscribers = self.cleaned_data["subscribers"]

        if subscribers:
            subscribers = subscribers.split(",")
            subscribers = [email.strip() for email in subscribers]

            for email in subscribers:
                try:
                    validate_email(email)
                except ValidationError:
                    raise ValidationError(f"Invalid email address: {email}")

        return subscribers

    def clean(self):
        cleaned_data = super().clean()
        if not any(cleaned_data.values()):
            raise ValidationError("At least one field must be filled.")

    class Meta:
        model = Device
        fields = [
            "sap_id",
            "manufacturer",
            "series",
            "maintenance_contract_expiration_date",
            "note",
            "device_type",
            "subscribers",
        ]
        widgets = {
            "maintenance_contract_expiration_date": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 6}),
        }
