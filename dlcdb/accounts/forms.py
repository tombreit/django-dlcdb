# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.contrib.auth.forms import AdminUserCreationForm, AuthenticationForm

from .models import CustomUser


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "username"}))

    class Media:
        js = ["accounts/js/password-toggle.js"]


class CustomUserCreationForm(AdminUserCreationForm):
    """
    Users log in with their email address, so the admin asks for it instead of a
    username. The username follows the email, as with LDAP and EmailModelBackend.
    """

    class Meta:
        model = CustomUser
        fields = ("email",)

    def clean_email(self):
        # Like Django's UserCreationForm.clean_username: the LDAP backend looks
        # users up by email__iexact, so emails must not differ only in case.
        email = self.cleaned_data["email"]
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise self.instance.unique_error_message(CustomUser, ["email"])
        return email

    def save(self, commit=True):
        self.instance.username = self.instance.email
        return super().save(commit)


# from django.contrib.auth.forms import UserChangeForm

# class CustomUserChangeForm(UserChangeForm):
#     class Meta:
#         model = CustomUser
#         fields = ("email",)
