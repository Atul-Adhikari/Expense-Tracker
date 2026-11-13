from django.contrib import admin
from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'category',
        'amount',
        'currency',
        'period_start',
        'created_at',
    )

    list_filter = (
        'currency',
        'period_start',
    )

    search_fields = (
        'user__username',
        'category__name',
    )

    date_hierarchy = 'period_start'