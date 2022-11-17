
from dlcdb.organization.models import Branding


def branding(request):
    """Make branding settings available for all requests."""
    return {"branding": Branding.objects.all().first()}
