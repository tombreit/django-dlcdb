# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserQuerySet(models.QuerySet):
    # Available only on QuerySet: delete() makes no sense on manager
    def delete(self):
        for obj in self:
            obj.is_active = False
            obj.save()

    delete.queryset_only = True

    def hard_delete(self):
        super().delete()

    hard_delete.queryset_only = True


class CustomUserManager(BaseUserManager):
    # TODO: makemigrations will refuse to do its work when 'use_in_migrations'
    # is set to True, which is the default value:
    # ValueError: Could not find manager CustomUserManagerFromCustomUserQuerySet in django.db.models.manager.
    # Please note that you need to inherit from managers you dynamically generated with 'from_queryset()'.
    # Others have the same problem, eg:
    # https://github.com/raphaelm/django-scopes/issues/20
    # use_in_migrations = False

    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password=None, **other_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **other_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **other_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        other_fields.setdefault("is_staff", True)
        other_fields.setdefault("is_superuser", True)
        other_fields.setdefault("is_active", True)

        if other_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if other_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **other_fields)


class CustomUser(AbstractUser):
    email = models.EmailField(
        verbose_name=_("email address"),
        blank=False,  # As we use email as username, this must be set to False
        unique=True,
    )

    USERNAME_FIELD = "email"

    # https://docs.djangoproject.com/en/5.1/topics/auth/customizing/#django.contrib.auth.models.CustomUser.EMAIL_FIELD
    # REQUIRED_FIELDS must contain all required fields on your user model, but
    # should not contain the USERNAME_FIELD or password as these fields will
    # always be prompted for.
    # Add 'username' if we still want to collect it
    REQUIRED_FIELDS = []

    objects = CustomUserManager.from_queryset(CustomUserQuerySet)()

    def __str__(self):
        return self.email

    def delete(self):
        self.is_active = False
        self.save()

    def hard_delete(self):
        super().delete()
