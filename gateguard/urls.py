from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/dpts/", include("dpts.urls")),
    path("api/devices/", include("devices.urls")),
    path("api/scans/", include("scans.urls")),
    path("guard-scanner/", TemplateView.as_view(template_name="guard_scanner.html"), name="guard-scanner"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL)
