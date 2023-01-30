from django.urls import include, path
from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register(r'devices', views.DeviceViewSet)
router.register(r'records', views.RecordViewSet)
router.register(r'persons', views.PersonViewSet)
router.register(r'rooms', views.RoomViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
