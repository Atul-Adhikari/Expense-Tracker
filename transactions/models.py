
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ValidationError


class Category(models.Model):

    CATEGORY_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories'
    )

    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    icon = models.CharField(max_length=50, default='circle')
    color = models.CharField(max_length=20, default='#64748b')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name', 'category_type'],
                name='unique_category_per_user_and_type'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.category_type})"


class Transaction(models.Model):

    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    ]

    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('BANK', 'Bank Transfer'),
        ('WALLET', 'Digital Wallet'),
        ('OTHER', 'Other'),
    ]

    recurring_schedule = models.ForeignKey(
        'RecurringTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_transactions',
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )

    account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES
    )

    amount = models.DecimalField(max_digits=14, decimal_places=2)

    date = models.DateField(default=timezone.localdate)

    description = models.CharField(max_length=255, blank=True)

    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHODS,
        default='CASH'
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='transaction_amount_must_be_positive'
            ),
            models.UniqueConstraint(
                fields=['recurring_schedule', 'date'],
                condition=Q(recurring_schedule__isnull=False),
                name='unique_recurring_tx_per_date',
            ),
        ]

    def __str__(self):
        return f"{self.transaction_type}: {self.amount}"


class Transfer(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transfers'
    )

    from_account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.PROTECT,
        related_name='outgoing_transfers'
    )

    to_account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.PROTECT,
        related_name='incoming_transfers'
    )

    amount = models.DecimalField(max_digits=14, decimal_places=2)

    date = models.DateField(default=timezone.localdate)

    description = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='transfer_amount_must_be_positive'
            ),
            models.CheckConstraint(
                condition=~Q(from_account=models.F('to_account')),
                name='transfer_accounts_must_be_different'
            )
        ]

    def __str__(self):
        return f"Transfer: {self.amount}"


class RecurringTransaction(models.Model):

    FREQUENCIES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]

    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recurring_transactions'
    )

    account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.PROTECT,
        related_name='recurring_transactions'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='recurring_transactions'
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    description = models.CharField(
        max_length=255,
        blank=True
    )

    payment_method = models.CharField(
        max_length=10,
        choices=Transaction.PAYMENT_METHODS,
        default='CASH'
    )

    notes = models.TextField(blank=True)

    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCIES,
        default='MONTHLY'
    )

    interval = models.PositiveSmallIntegerField(
        default=1,
        help_text='Repeat every specified number of periods.'
    )

    start_date = models.DateField()

    next_due_date = models.DateField()

    end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Leave empty for an ongoing schedule.'
    )

    last_generated_date = models.DateField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_due_date', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='recurring_amount_must_be_positive'
            ),
            models.CheckConstraint(
                condition=Q(interval__gte=1),
                name='recurring_interval_must_be_positive'
            ),
        ]

    def clean(self):
        super().clean()

        if self.account_id and self.user_id:
            if self.account.user_id != self.user_id:
                raise ValidationError({
                    'account': 'Select one of your own accounts.'
                })

        if self.category_id and self.user_id:
            if self.category.user_id != self.user_id:
                raise ValidationError({
                    'category': 'Select one of your own categories.'
                })

        if self.category_id and self.transaction_type:
            if self.category.category_type != self.transaction_type:
                raise ValidationError({
                    'category': 'Category type must match transaction type.'
                })

        if self.start_date and self.next_due_date:
            if self.next_due_date < self.start_date:
                raise ValidationError({
                    'next_due_date': 'Next due date cannot be before the start date.'
                })

        if self.end_date and self.start_date:
            if self.end_date < self.start_date:
                raise ValidationError({
                    'end_date': 'End date cannot be before the start date.'
                })

        if self.is_active and self.end_date and self.next_due_date:
            if self.end_date < self.next_due_date:
                raise ValidationError({
                    'end_date': 'End date cannot be before the next due date.'
                })

    def __str__(self):
        return (
            f"{self.get_transaction_type_display()} - "
            f"{self.amount} ({self.get_frequency_display()})"
        )
