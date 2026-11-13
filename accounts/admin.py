from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Account


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'email',
        'preferred_currency',
        'preferred_calendar',
        'is_active',
    )

    search_fields = ('username', 'email')

    fieldsets = UserAdmin.fieldsets + (
        ('ExpenseFlow Preferences', {
            'fields': ('preferred_currency', 'preferred_calendar'),
        }),
    )


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'account_type',
        'currency',
        'opening_balance',
        'is_active',
    )

    list_filter = ('account_type', 'currency', 'is_active')
    search_fields = ('name', 'user__username')