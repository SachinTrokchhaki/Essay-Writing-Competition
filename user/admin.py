# essay_project/user/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'dob', 'is_staff', 'is_active', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username',)
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)

    # Fields for editing a user
    fieldsets = (
        (None, {'fields': ('username', 'password', 'identity_doc', 'dob')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login',)}),  # remove non-editable fields
    )

    # Fields for creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'identity_doc', 'dob', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )