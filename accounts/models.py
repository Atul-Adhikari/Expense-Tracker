from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):

    CURRENCY_CHOICES = [
        ('NPR', 'Nepalese Rupee'),
        ('USD', 'US Dollar'),
        ('INR', 'Indian Rupee'),
    ]

    CALENDAR_CHOICES = [
        ('BS', 'Bikram Sambat'),
        ('AD', 'Gregorian'),
    ]

    email = models.EmailField(unique=True)

    preferred_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='NPR'
    )

    preferred_calendar = models.CharField(
        max_length=2,
        choices=CALENDAR_CHOICES,
        default='BS'
    )

    def __str__(self):
        return self.username


class Account(models.Model):

    ACCOUNT_TYPES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Account'),
        ('WALLET', 'Digital Wallet'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='accounts'
    )

    name = models.CharField(max_length=100)

    account_type = models.CharField(
        max_length=10,
        choices=ACCOUNT_TYPES,
        default='CASH'
    )

    currency = models.CharField(max_length=3, default='NPR')

    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_account_name_per_user'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"