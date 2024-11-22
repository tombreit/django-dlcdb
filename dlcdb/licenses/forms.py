from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_bootstrap5.bootstrap5 import FloatingField

from dlcdb.core.models import Device
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class LicenseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            FloatingField("subscribers"),
            FloatingField("sap_id"),
            FloatingField("manufacturer"),
            FloatingField("series"),
            FloatingField("maintenance_contract_expiration_date"),
            FloatingField("note"),
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

    class Meta:
        model = Device
        fields = ["sap_id", "manufacturer", "series", "maintenance_contract_expiration_date", "note", "subscribers"]
        widgets = {"maintenance_contract_expiration_date": forms.DateInput(attrs={"type": "date"})}
