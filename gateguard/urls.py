from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.views.generic import TemplateView
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/dpts/", include("dpts.urls")),
    path("api/devices/", include("devices.urls")),
    path("api/scans/", include("scans.urls")),
    path("guard-scanner/", TemplateView.as_view(template_name="guard_scanner.html"), name="guard-scanner"),
]

if settings.DEBUG:
    urlpatterns += [path(settings.STATIC_URL.lstrip("/"), serve, {"document_root": settings.STATIC_ROOT})]

urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
