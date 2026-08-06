from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, UserCreateView, GuardCreateView, UserListView, MeProfileView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeProfileView.as_view(), name="me-profile"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/create/", UserCreateView.as_view(), name="user-create"),
    path("guards/create/", GuardCreateView.as_view(), name="guard-create"),
]
