from django.urls import path
from .views import (
    GuestPassCheckInView,
    GuestPassLookupView,
    GuestPassCheckOutView,
    GuestPassListView,
)

urlpatterns = [
    path("", GuestPassListView.as_view(), name="guest-pass-list"),
    path("check-in/", GuestPassCheckInView.as_view(), name="guest-check-in"),
    path("lookup/<str:pass_id>/", GuestPassLookupView.as_view(), name="guest-lookup"),
    path("check-out/", GuestPassCheckOutView.as_view(), name="guest-check-out"),
]
