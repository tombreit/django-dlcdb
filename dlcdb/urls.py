# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, reverse_lazy
from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView


admin.site.site_header = "DLCDB Admin"
admin.site.site_title = "DLCDB Admin"
admin.site.index_title = "DLCDB Administration"
admin.site.enable_nav_sidebar = False
admin.site.logout_template = "accounts/logout.html"


urlpatterns = [
    path("", RedirectView.as_view(url=reverse_lazy("core:core_dashboard"))),
    path("core/", include("dlcdb.core.urls")),
    path("inventory/", include("dlcdb.inventory.urls")),
    path("smallstuff/", include("dlcdb.smallstuff.urls")),
    path("select2/", include("django_select2.urls")),
    path("api/v2/", include("dlcdb.api.urls")),
    path("favicon.ico", RedirectView.as_view(url=staticfiles_storage.url("branding/favicon.ico"))),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
