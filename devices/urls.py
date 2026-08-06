from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PCViewSet, MyDevicesView, PCLookupByTokenView, ReportLostDeviceView

router = DefaultRouter()
router.register(r"", PCViewSet, basename="pc")

urlpatterns = [
    path("my-devices/", MyDevicesView.as_view(), name="my-devices"),
    path("lookup/<uuid:qr_token>/", PCLookupByTokenView.as_view(), name="pc-lookup"),
    path("report-lost/<uuid:pk>/", ReportLostDeviceView.as_view(), name="pc-report-lost"),
] + router.urls
