# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend


class UnreachableMailServer(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise OSError("mail server unreachable")


def test_failing_admin_mail_does_not_turn_a_disallowed_host_into_a_500(client, settings):
    """A disallowed host is logged as an error, and the admin mail fails: still a 400."""
    settings.MAILERS = {"default": {"BACKEND": f"{__name__}.UnreachableMailServer"}}
    settings.ADMINS = ["admin@example.org"]
    settings.ALLOWED_HOSTS = ["testserver"]

    response = client.get("/accounts/login/", HTTP_HOST="disallowed.example")

    assert response.status_code == 400


def test_test_error_url_mails_the_admins_a_traceback(client, settings, db):
    """/_500/ raises for a superuser: a 500, and the admins get the traceback by mail."""
    settings.ADMINS = ["admin@example.org"]
    superuser = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
    client.force_login(superuser)
    client.raise_request_exception = False

    response = client.get("/_500/")

    assert response.status_code == 500
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["admin@example.org"]
    assert "RuntimeError" in mail.outbox[0].body


def test_test_error_url_is_for_superusers_only(client, settings, db):
    settings.ADMINS = ["admin@example.org"]

    response = client.get("/_500/")

    assert response.status_code == 302
    assert mail.outbox == []
