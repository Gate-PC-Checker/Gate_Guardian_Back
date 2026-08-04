from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class GateGuardUserAdmin(UserAdmin):
    list_display = ["username", "role", "dpt", "email", "is_active"]
    list_filter = ["role", "dpt"]
    fieldsets = UserAdmin.fieldsets + (
        ("GateGuard", {"fields": ("role", "dpt", "phone")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("GateGuard", {"fields": ("role", "dpt", "phone")}),
    )
