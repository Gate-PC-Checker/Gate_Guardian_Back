from django.urls import path
from .views import ScanCreateView, ScanLogListView

urlpatterns = [
    path("", ScanCreateView.as_view(), name="scan-create"),
    path("logs/", ScanLogListView.as_view(), name="scan-logs"),
]
