from django.contrib import admin

from .models import (
    Category,
    Transaction,
    Transfer,
    RecurringTransaction,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'category_type',
        'is_active',
    )

    list_filter = ('category_type', 'is_active')
    search_fields = ('name', 'user__username')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'description',
        'user',
        'transaction_type',
        'amount',
        'account',
        'category',
        'date',
    )

    list_filter = ('transaction_type', 'payment_method', 'date')
    search_fields = ('description', 'user__username')


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'from_account',
        'to_account',
        'amount',
        'date',
    )

    list_filter = ('date',)

@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'description',
        'user',
        'transaction_type',
        'amount',
        'account',
        'category',
        'frequency',
        'next_due_date',
        'is_active',
    )

    list_filter = (
        'transaction_type',
        'frequency',
        'is_active',
    )

    search_fields = (
        'description',
        'user__username',
    )

    date_hierarchy = 'next_due_date'