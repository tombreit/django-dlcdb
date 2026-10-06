# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

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
