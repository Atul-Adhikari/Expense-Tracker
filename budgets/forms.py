
from datetime import date

from django import forms
from django.db.models import Q

from nepali_date_library import ADtoBS, BStoAD

from transactions.models import Category
from .models import Budget


class BudgetForm(forms.ModelForm):

    # The user enters a BS year and month, e.g. 2083-07.
    period_start = forms.CharField(
        label='Budget Month (Bikram Sambat)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'YYYY-MM (e.g. 2083-07)',
            'autocomplete': 'off',
        }),
        help_text='Enter the BS year and month in YYYY-MM format.'
    )

    class Meta:
        model = Budget

        fields = [
            'category',
            'amount',
            'currency',
            'period_start',
        ]

        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),

            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter budget amount',
                'step': '0.01',
                'min': '0.01',
            }),

            'currency': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        category_queryset = Category.objects.filter(
            user=self.user,
            category_type='EXPENSE',
            is_active=True
        )

        if self.instance and self.instance.pk:
            category_queryset = Category.objects.filter(
                user=self.user,
                category_type='EXPENSE'
            ).filter(
                Q(is_active=True) |
                Q(pk=self.instance.category_id)
            )

            self.fields['period_start'].initial = str(
                ADtoBS(self.instance.period_start.isoformat())
            )[:7]

        self.fields['category'].queryset = category_queryset
        self.fields['category'].required = False
        self.fields['category'].empty_label = 'Overall Monthly Budget'

        self.fields['amount'].help_text = (
            'Enter the maximum amount you want to spend.'
        )

        self.fields['category'].help_text = (
            'Leave this blank to create an overall monthly budget.'
        )

    def clean_period_start(self):
        value = self.cleaned_data['period_start'].strip()

        try:
            year_text, month_text = value.split('-')
            year = int(year_text)
            month = int(month_text)

            if len(year_text) != 4 or len(month_text) != 2:
                raise ValueError

            if not 1 <= month <= 12:
                raise ValueError

            ad_date = BStoAD(f'{year}-{month:02d}-01')

            return date.fromisoformat(str(ad_date))

        except (ValueError, TypeError, OverflowError):
            raise forms.ValidationError(
                'Enter a valid BS month in YYYY-MM format, '
                'for example 2083-07.'
            )

    def clean(self):
        cleaned_data = super().clean()

        category = cleaned_data.get('category')
        period_start = cleaned_data.get('period_start')
        currency = cleaned_data.get('currency')

        if category and category.user_id != self.user.id:
            self.add_error(
                'category',
                'Please select one of your own expense categories.'
            )

        if category and category.category_type != 'EXPENSE':
            self.add_error(
                'category',
                'Budgets can only be created for expense categories.'
            )

        if category and not category.is_active:
            if not (
                self.instance
                and self.instance.pk
                and category.pk == self.instance.category_id
            ):
                self.add_error(
                    'category',
                    'You cannot create a budget for an inactive category.'
                )

        if period_start and currency:
            duplicate_budgets = Budget.objects.filter(
                user=self.user,
                period_start=period_start,
                currency=currency,
                category=category
            )

            if self.instance and self.instance.pk:
                duplicate_budgets = duplicate_budgets.exclude(
                    pk=self.instance.pk
                )

            if duplicate_budgets.exists():
                self.add_error(
                    'category',
                    'A budget already exists for this category and month.'
                )

        return cleaned_data
