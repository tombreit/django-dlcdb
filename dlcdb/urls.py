# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, reverse_lazy
from django.contrib import admin
from django.views.generic.base import RedirectView

from dlcdb.accounts.forms import EmailAuthenticationForm
from dlcdb.organization import views as organization_views

admin.site.site_header = "DLCDB Admin"
admin.site.site_title = "DLCDB Admin"
admin.site.index_title = "DLCDB Administration"
admin.site.enable_nav_sidebar = False
admin.site.login_form = EmailAuthenticationForm
admin.site.logout_template = "accounts/logout.html"


urlpatterns = [
    path("core/", include("dlcdb.core.urls")),
    path("inventory/", include("dlcdb.inventory.urls")),
    path("licenses/", include("dlcdb.licenses.urls")),
    path("smallstuff/", include("dlcdb.smallstuff.urls")),
    path("select2/", include("django_select2.urls")),
    path("api/v2/", include("dlcdb.api.urls")),
    path("favicon.ico", organization_views.favicon),
    path("admin/login/", RedirectView.as_view(url=reverse_lazy("login")), name="login"),
    path("admin/logout/", RedirectView.as_view(url=reverse_lazy("logout")), name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url=reverse_lazy("core:core_dashboard")), name="dashboard"),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
