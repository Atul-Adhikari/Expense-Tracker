from django import forms
from .models import Account


class AccountForm(forms.ModelForm):

    CURRENCY_CHOICES = [
        ('NPR', 'NPR - Nepalese Rupee'),
        ('USD', 'USD - US Dollar'),
        ('INR', 'INR - Indian Rupee'),
    ]

    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    class Meta:
        model = Account
        fields = [
            'name',
            'account_type',
            'currency',
            'opening_balance',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Personal Savings'
            }),
            'account_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'opening_balance': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['name'].help_text = (
            'Choose a name that helps you identify this account.'
        )

        self.fields['opening_balance'].help_text = (
            'Enter the amount already available when you start tracking.'
        )

        # Once an account has transactions or transfers,
        # prevent its currency from being changed.
        if self.instance and self.instance.pk:
            has_transactions = self.instance.transactions.exists()

            has_transfers = (
                self.instance.outgoing_transfers.exists()
                or self.instance.incoming_transfers.exists()
            )

            if has_transactions or has_transfers:
                self.fields['currency'].disabled = True
                self.fields['currency'].help_text = (
                    'Currency cannot be changed because this account '
                    'already has financial activity.'
                )

    def clean_name(self):
        name = self.cleaned_data['name'].strip()

        existing_accounts = Account.objects.filter(
            user=self.user,
            name__iexact=name
        )

        if self.instance and self.instance.pk:
            existing_accounts = existing_accounts.exclude(
                pk=self.instance.pk
            )

        if existing_accounts.exists():
            raise forms.ValidationError(
                'You already have an account with this name.'
            )

        return name