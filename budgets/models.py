from datetime import date, timedelta
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q

from nepali_date_library import BStoAD


class Budget(models.Model):

    CURRENCY_CHOICES = [
        ('NPR', 'Nepalese Rupee (NPR)'),
        ('USD', 'US Dollar (USD)'),
        ('INR', 'Indian Rupee (INR)'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budgets'
    )

    # A blank category represents an overall monthly budget.
    category = models.ForeignKey(
        'transactions.Category',
        on_delete=models.CASCADE,
        related_name='budgets',
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='NPR'
    )

    # AD equivalent of the first day of the BS budget month.
    period_start = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_start', 'category__name']

        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='budget_amount_must_be_positive'
            ),

            models.UniqueConstraint(
                fields=['user', 'period_start', 'currency'],
                condition=Q(category__isnull=True),
                name='unique_overall_budget_per_month'
            ),

            models.UniqueConstraint(
                fields=['user', 'period_start', 'category', 'currency'],
                condition=Q(category__isnull=False),
                name='unique_category_budget_per_month'
            ),
        ]

    @property
    def period_end(self):
        """Return the final AD date of this BS budget month."""

        from nepali_date_library import ADtoBS

        bs_start = str(ADtoBS(self.period_start.isoformat()))
        year, month, _ = map(int, bs_start.split('-'))

        if month == 12:
            next_year = year + 1
            next_month = 1
        else:
            next_year = year
            next_month = month + 1

        next_bs_start = f'{next_year}-{next_month:02d}-01'
        next_ad_start = BStoAD(next_bs_start)

        return date.fromisoformat(next_ad_start) - timedelta(days=1)

    def __str__(self):
        from nepali_date_library import ADtoBS

        budget_name = (
            self.category.name
            if self.category
            else 'Overall Budget'
        )

        bs_month = str(ADtoBS(self.period_start.isoformat()))[:7]

        return f'{budget_name} - {bs_month} ({self.currency})'
