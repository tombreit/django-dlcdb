from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from django_auth_ldap.backend import LDAPBackend


class EmailLDAPBackend(LDAPBackend):
    def get_or_create_user(self, username, ldap_user):
        UserModel = get_user_model()
        email = ldap_user.attrs.get("mail", [None])[0]
        if not email:
            raise ValueError("LDAP user does not have a 'mail' attribute; cannot authenticate without email.")

        try:
            user = UserModel.objects.get(email__iexact=email)
            return user, False
        except UserModel.DoesNotExist:
            return super().get_or_create_user(username, ldap_user)


class EmailModelBackend(ModelBackend):
    """
    Authenticate normally, but ensure username matches email after successful login
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # First try standard authentication
        user = super().authenticate(request, username, password, **kwargs)

        # If authentication succeeded, ensure username matches email
        if user:
            if user.username != user.email:
                user.username = user.email
                user.save(update_fields=["username"])

        return user
