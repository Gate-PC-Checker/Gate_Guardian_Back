from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginView,
    UserCreateView,
    GuardCreateView,
    UserListView,
    MeProfileView,
    ChangePasswordView,
    SetupPasswordView,
    ResendSetupEmailView,
    ForgotPasswordResetView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeProfileView.as_view(), name="me-profile"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/create/", UserCreateView.as_view(), name="user-create"),
    path("guards/create/", GuardCreateView.as_view(), name="guard-create"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("setup-password/", SetupPasswordView.as_view(), name="setup-password"),
    path("resend-setup-email/", ResendSetupEmailView.as_view(), name="resend-setup-email"),
    path("forgot-password/", ForgotPasswordResetView.as_view(), name="forgot-password"),
]
