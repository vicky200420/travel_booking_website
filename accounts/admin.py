from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone_number', 'role', 'city', 'country', 'is_staff', 'is_active', 'created_at')
    list_filter = ('role', 'is_staff', 'is_active', 'city', 'country')
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name', 'city', 'country')
    ordering = ('-created_at',)

    fieldsets = (
        ('Login Credentials', {'fields': ('username', 'email', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'phone_number', 'profile_image', 'date_of_birth')}),
        ('Location', {'fields': ('address', 'city', 'country')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    readonly_fields = ('created_at', 'updated_at', 'last_login')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'phone_number', 'role'),
        }),
    )
