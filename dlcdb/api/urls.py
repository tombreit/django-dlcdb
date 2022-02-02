from django.urls import include, path
from rest_framework import routers

from .views import DeviceViewSet, RecordViewSet, PersonViewSet

router = routers.DefaultRouter()
router.register(r'devices', DeviceViewSet)
router.register(r'records', RecordViewSet)
router.register(r'persons', PersonViewSet)

urlpatterns = [
    path('', include(router.urls)),
]