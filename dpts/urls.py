from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import DepartmentRegisterView, DepartmentViewSet

router = DefaultRouter()
router.register(r"", DepartmentViewSet, basename="department")

urlpatterns = [
    path("register/", DepartmentRegisterView.as_view(), name="department-register"),
    *router.urls,
]
