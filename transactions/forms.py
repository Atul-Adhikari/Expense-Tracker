from decimal import Decimal

from django import forms

from accounts.models import Account
from .models import Category, Transaction, Transfer, RecurringTransaction


class TransactionForm(forms.ModelForm):

    class Meta:
        model = Transaction

        fields = [
            'transaction_type',
            'account',
            'category',
            'amount',
            'date',
            'description',
            'payment_method',
            'notes',
        ]

        widgets = {
            'transaction_type': forms.Select(attrs={
                'class': 'form-select',
            }),

            'account': forms.Select(attrs={
                'class': 'form-select',
            }),

            'category': forms.Select(attrs={
                'class': 'form-select',
            }),

            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
            }),

            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),

            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Monthly salary or Grocery shopping',
            }),

            'payment_method': forms.Select(attrs={
                'class': 'form-select',
            }),

            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional details (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Only show accounts belonging to this user.
        account_queryset = Account.objects.filter(
            user=self.user,
            is_active=True
        )

        # Allow an existing inactive account to remain selected
        # when editing an older transaction.
        if self.instance and self.instance.pk:
            account_queryset = Account.objects.filter(
                user=self.user
            ).filter(
                models_q_for_account(self.instance.account_id)
            )

        self.fields['account'].queryset = account_queryset

        # Only show this user's categories.
        category_queryset = Category.objects.filter(
            user=self.user,
            is_active=True
        )

        # Keep the current category available when editing.
        if self.instance and self.instance.pk:
            category_queryset = Category.objects.filter(
                user=self.user
            )

        # Show categories matching the selected transaction type.
        selected_type = (
            self.data.get('transaction_type')
            or getattr(self.instance, 'transaction_type', '')
        )

        if selected_type in ['INCOME', 'EXPENSE']:
            category_queryset = category_queryset.filter(
                category_type=selected_type
            )

        self.fields['category'].queryset = category_queryset

        self.fields['description'].required = False
        self.fields['notes'].required = False

    def clean(self):
        cleaned_data = super().clean()

        account = cleaned_data.get('account')
        category = cleaned_data.get('category')
        transaction_type = cleaned_data.get('transaction_type')
        amount = cleaned_data.get('amount')

        if account and account.user_id != self.user.id:
            self.add_error(
                'account',
                'Please select one of your own accounts.'
            )

        if category and category.user_id != self.user.id:
            self.add_error(
                'category',
                'Please select one of your own categories.'
            )

        if category and transaction_type:
            if category.category_type != transaction_type:
                self.add_error(
                    'category',
                    'The category must match the transaction type.'
                )

        if account and not account.is_active:
            if not (
                self.instance
                and self.instance.pk
                and account.pk == self.instance.account_id
            ):
                self.add_error(
                    'account',
                    'You cannot add a transaction to an inactive account.'
                )

        if amount is not None and amount <= Decimal('0'):
            self.add_error(
                'amount',
                'Amount must be greater than zero.'
            )

        return cleaned_data


# Helper used to keep an inactive account available during editing.
from django.db.models import Q


def models_q_for_account(account_id):
    return Q(is_active=True) | Q(pk=account_id)



from .models import Transfer


class TransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        fields = [
            'from_account',
            'to_account',
            'amount',
            'date',
            'description',
        ]

        widgets = {
            'from_account': forms.Select(attrs={
                'class': 'form-select',
            }),
            'to_account': forms.Select(attrs={
                'class': 'form-select',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter transfer amount',
                'step': '0.01',
                'min': '0.01',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Bank to eSewa',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        accounts = Account.objects.filter(user=self.user)

        self.fields['from_account'].queryset = accounts
        self.fields['to_account'].queryset = accounts

        self.fields['amount'].help_text = (
            'Enter the amount to move between your accounts.'
        )

        self.fields['description'].required = False

    def clean(self):
        cleaned_data = super().clean()

        from_account = cleaned_data.get('from_account')
        to_account = cleaned_data.get('to_account')
        amount = cleaned_data.get('amount')

        if from_account and to_account:
            if from_account.pk == to_account.pk:
                self.add_error(
                    'to_account',
                    'Source and destination accounts must be different.'
                )

            if from_account.user_id != self.user.id:
                self.add_error(
                    'from_account',
                    'Please select one of your own accounts.'
                )

            if to_account.user_id != self.user.id:
                self.add_error(
                    'to_account',
                    'Please select one of your own accounts.'
                )

            if from_account.currency != to_account.currency:
                self.add_error(
                    'to_account',
                    'Both accounts must use the same currency.'
                )

            if not from_account.is_active:
                self.add_error(
                    'from_account',
                    'The source account is inactive.'
                )

            if not to_account.is_active:
                self.add_error(
                    'to_account',
                    'The destination account is inactive.'
                )

        if amount is not None and amount <= 0:
            self.add_error('amount', 'Amount must be greater than zero.')

        return cleaned_data



class RecurringTransactionForm(forms.ModelForm):

    class Meta:
        model = RecurringTransaction

        fields = [
            'transaction_type',
            'account',
            'category',
            'amount',
            'description',
            'payment_method',
            'notes',
            'frequency',
            'interval',
            'start_date',
            'next_due_date',
            'end_date',
            'is_active',
        ]

        widgets = {
            'transaction_type': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'account': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'category': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount',
                'step': '0.01',
                'min': '0.01',
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Monthly salary',
            }),
            'payment_method': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional details (optional)',
            }),
            'frequency': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'interval': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '365',
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'next_due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'is_active': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)

        super().__init__(*args, **kwargs)

        accounts = Account.objects.filter(user=self.user)
        active_accounts = accounts.filter(is_active=True)

        # Keep an existing inactive account selectable when editing.
        if self.instance and self.instance.pk:
            account_queryset = (
                active_accounts
                | accounts.filter(pk=self.instance.account_id)
            ).distinct()
        else:
            account_queryset = active_accounts

        self.fields['account'].queryset = account_queryset

        # Determine the selected transaction type.
                # Load all active categories so the dropdown can switch
        # between Income and Expense dynamically.
        categories = Category.objects.filter(
            user=self.user,
            is_active=True
        )

        # Preserve an existing category when editing, even if inactive.
        if self.instance and self.instance.pk:
            categories = (
                categories
                | Category.objects.filter(
                    user=self.user,
                    pk=self.instance.category_id
                )
            ).distinct()

        self.fields['category'].queryset = categories

        self.fields['amount'].help_text = (
            'The amount to record each time this schedule is generated.'
        )

        self.fields['interval'].help_text = (
            'For example, 1 = every month; 2 = every two months.'
        )

        self.fields['start_date'].help_text = (
            'The date on which the schedule begins.'
        )

        self.fields['next_due_date'].help_text = (
            'You can adjust this date if the next payment or income arrives '
            'on a different day.'
        )

        self.fields['end_date'].required = False
        self.fields['description'].required = False
        self.fields['notes'].required = False

    def clean(self):
        cleaned_data = super().clean()

        transaction_type = cleaned_data.get('transaction_type')
        account = cleaned_data.get('account')
        category = cleaned_data.get('category')
        amount = cleaned_data.get('amount')
        interval = cleaned_data.get('interval')
        start_date = cleaned_data.get('start_date')
        next_due_date = cleaned_data.get('next_due_date')
        end_date = cleaned_data.get('end_date')
        is_active = cleaned_data.get('is_active')

        if account and account.user_id != self.user.id:
            self.add_error(
                'account',
                'Please select one of your own accounts.'
            )

        if category:
            if category.user_id != self.user.id:
                self.add_error(
                    'category',
                    'Please select one of your own categories.'
                )

            elif transaction_type and (
                category.category_type != transaction_type
            ):
                self.add_error(
                    'category',
                    'Category must match the transaction type.'
                )

        if account and not account.is_active:
            if not (
                self.instance
                and self.instance.pk
                and account.pk == self.instance.account_id
            ):
                self.add_error(
                    'account',
                    'You cannot create a schedule using an inactive account.'
                )

        if category and not category.is_active:
            if not (
                self.instance
                and self.instance.pk
                and category.pk == self.instance.category_id
            ):
                self.add_error(
                    'category',
                    'You cannot create a schedule using an inactive category.'
                )

        if amount is not None and amount <= Decimal('0'):
            self.add_error(
                'amount',
                'Amount must be greater than zero.'
            )

        if interval is not None and not 1 <= interval <= 365:
            self.add_error(
                'interval',
                'Repeat interval must be between 1 and 365.'
            )

        if start_date and next_due_date:
            if next_due_date < start_date:
                self.add_error(
                    'next_due_date',
                    'Next due date cannot be before the start date.'
                )

        # End date must never precede the schedule start date.
        if end_date and start_date:
            if end_date < start_date:
                self.add_error(
                    'end_date',
                    'End date cannot be before the start date.'
                )

        # An active schedule must have a valid next due date.
        # Inactive completed schedules may have next_due_date beyond end_date.
        if is_active and end_date and next_due_date:
            if end_date < next_due_date:
                self.add_error(
                    'end_date',
                    'End date cannot be before the next due date '
                    'while the schedule is active.'
                )

        return cleaned_data
