from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView

from dlcdb.core.views import (
    dashboard_views,
    procure_views,
    lent_management_views,
    relocate_views,
)


admin.site.site_header = "DLCDB Admin"
admin.site.site_title = "DLCDB Admin"
admin.site.index_title = "DLCDB Administration"
admin.site.enable_nav_sidebar = False


urlpatterns = [
    path('', dashboard_views.DashboardView.as_view(), name='core_dashboard'),

    # Commented out for having a functional listing of installed admin apps:
    # path('admin/', dashboard_views.DashboardView.as_view(), name='core_dashboard'),

    path('admin/core/orderedrecord/procure/', procure_views.ProcureDeviceView.as_view(), name='core_procure_device'),
    path('admin/core/lentrecord/print/<int:pk>/', lent_management_views.PrintLentSheetView.as_view(), name='core_print_lent_sheet'),
    path('admin/core/devices/relocate/', relocate_views.DevicesRelocateView.as_view(), name='core_devices_relocate'),

    path('core/', include('dlcdb.core.urls')),
    path('inventory/', include('dlcdb.inventory.urls')),
    path('lending/', include('dlcdb.lending.urls')),

    path('admin/', admin.site.urls),

    path("select2/", include("django_select2.urls")),
    path('api/v2/', include('dlcdb.api.urls')),

    path("favicon.ico", RedirectView.as_view(url=staticfiles_storage.url("dlcdb/favicon.ico")),
    ),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
