# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.contrib.auth.forms import AdminUserCreationForm, AuthenticationForm
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from dlcdb.theme.forms import add_bootstrap_classes
from dlcdb.theme.widgets import FilteredSelectMultipleWidget

from .models import CustomUser, is_ldap_mirrored


class GroupForm(forms.ModelForm):
    """
    A group's name, its permissions among DLCDB's own and its active members.
    What the form doesn't show stays as it is: the permissions no page of DLCDB
    checks, and deactivated members.

    ``own`` is ``permissions.own_permissions()``, ``editor`` the user saving.
    Members need ``accounts.view_customuser`` to be shown and
    ``accounts.change_customuser`` to be changed. LDAP sets a mirrored group's
    members and matches it by name: both are read-only.
    """

    permissions = forms.ModelMultipleChoiceField(queryset=Permission.objects.none(), required=False)
    members = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by("email"),
        required=False,
        label=_("Members"),
        widget=FilteredSelectMultipleWidget(available_label=_("Users"), chosen_label=_("Members")),
    )

    class Meta:
        model = Group
        fields = ["name"]

    def __init__(self, *args, own, editor, **kwargs):
        super().__init__(*args, **kwargs)
        self.own, self.editor = own, editor
        ldap = is_ldap_mirrored(self.instance)

        self.fields["permissions"].queryset = Permission.objects.filter(pk__in=[p.permission.pk for p in own])
        self.initial["permissions"] = list(self.instance.permissions.filter(pk__in=self.fields["permissions"].queryset))
        if ldap:
            self.fields["name"].disabled = True
            self.fields["name"].help_text = _("LDAP finds this group by its name, so it keeps it.")

        if not editor.has_perm("accounts.view_customuser"):
            del self.fields["members"]
        else:
            self.initial["members"] = list(self.instance.user_set.filter(is_active=True))
            self.fields["members"].disabled = ldap or not editor.has_perm("accounts.change_customuser")
        add_bootstrap_classes(self)

    def clean(self):
        cleaned_data = super().clean()
        permissions = set(cleaned_data.get("permissions", ()))
        # Add, change and delete need the model's view permission: granted along with them.
        permissions |= {p.requires for p in self.own if p.requires and p.permission in permissions}
        cleaned_data["permissions"] = permissions

        if not self._editor_keeps_change_group(permissions, cleaned_data.get("members")):
            raise ValidationError(
                _(
                    "You would lose the permission to change groups. Keep it in this group, or get it "
                    "through another group first."
                )
            )
        return cleaned_data

    def checked_permissions(self):
        """The permissions ticked on the page: as just submitted, or as saved."""
        if self.is_bound:
            return getattr(self, "cleaned_data", {}).get("permissions", set())
        return set(self.initial["permissions"])

    def save(self):
        group = super().save()
        others = list(group.permissions.exclude(pk__in=self.fields["permissions"].queryset))
        group.permissions.set([*others, *self.cleaned_data["permissions"]])
        if "members" in self.fields and not self.fields["members"].disabled:
            deactivated = list(group.user_set.filter(is_active=False))
            group.user_set.set([*deactivated, *self.cleaned_data["members"]])
        return group

    def _editor_keeps_change_group(self, permissions, members):
        """No locking oneself out: after the save, the editor may still change groups."""
        if self.editor.is_superuser:
            return True
        change_group = Permission.objects.get(content_type__app_label="accounts", codename="change_group")
        stays = self.editor in members if members is not None else self.instance.user_set.contains(self.editor)
        if stays and change_group in permissions:
            return True
        # A permission of the editor's own, or another group of theirs.
        if self.editor.user_permissions.contains(change_group):
            return True
        return self.editor.groups.exclude(pk=self.instance.pk).filter(permissions=change_group).exists()


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
