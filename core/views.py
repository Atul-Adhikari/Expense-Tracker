
import time
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.models import Account
from transactions.models import Transaction, Transfer


BALANCE_VISIBILITY_SECONDS = 60


def get_total(queryset):
    return (
        queryset.aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )


@login_required
@never_cache
def dashboard(request):
    today = timezone.localdate()
    currency = request.user.preferred_currency

    # Check whether password verification is still valid.
    visible_until = request.session.get('balances_visible_until', 0)
    balances_visible = time.time() < visible_until

    if not balances_visible and visible_until:
        request.session.pop('balances_visible_until', None)

    # Get this user's active accounts in their preferred currency.
    accounts = Account.objects.filter(
        user=request.user,
        is_active=True,
        currency=currency
    )

    # Read account filter from the URL.
    selected_filter = request.GET.get('account', 'all')

    if selected_filter == 'all':
        selected_accounts = accounts
        filter_label = 'All Accounts'

    elif selected_filter in ['BANK', 'WALLET', 'CASH', 'OTHER']:
        selected_accounts = accounts.filter(
            account_type=selected_filter
        )
        filter_label = dict(Account.ACCOUNT_TYPES).get(
            selected_filter, 'Selected Accounts'
        )

    elif selected_filter.isdigit():
        selected_accounts = accounts.filter(id=int(selected_filter))

        if selected_accounts.exists():
            filter_label = selected_accounts.first().name
        else:
            selected_filter = 'all'
            selected_accounts = accounts
            filter_label = 'All Accounts'

    else:
        selected_filter = 'all'
        selected_accounts = accounts
        filter_label = 'All Accounts'

    # Transactions across all accounts in the preferred currency.
    all_transactions = Transaction.objects.filter(
        user=request.user,
        account__currency=currency
    )

    # Selected account/group transactions.
    transactions = all_transactions.filter(
        account__in=selected_accounts
    )

    # Calculate financial figures only when the user has verified
    # their password. Hidden figures are not sent to the template.
    financial_data = {
        'total_balance': None,
        'total_income': None,
        'total_expenses': None,
        'overall_expenses': None,
        'month_income': None,
        'month_expenses': None,
    }

    if balances_visible:
        total_income = get_total(
            transactions.filter(transaction_type='INCOME')
        )

        total_expenses = get_total(
            transactions.filter(transaction_type='EXPENSE')
        )

        opening_balance = (
            selected_accounts.aggregate(
                total=Sum('opening_balance')
            )['total'] or Decimal('0.00')
        )

        # Transfers affect account balances, not income or expenses.
        incoming_transfers = get_total(
            Transfer.objects.filter(
                user=request.user,
                to_account__in=selected_accounts,
                to_account__currency=currency,
                from_account__currency=currency
            )
        )

        outgoing_transfers = get_total(
            Transfer.objects.filter(
                user=request.user,
                from_account__in=selected_accounts,
                from_account__currency=currency,
                to_account__currency=currency
            )
        )

        total_balance = (
            opening_balance
            + total_income
            - total_expenses
            + incoming_transfers
            - outgoing_transfers
        )

        # Overall expenses are independent of the account filter.
        overall_expenses = get_total(
            all_transactions.filter(transaction_type='EXPENSE')
        )

        monthly_transactions = transactions.filter(
            date__year=today.year,
            date__month=today.month
        )

        month_income = get_total(
            monthly_transactions.filter(transaction_type='INCOME')
        )

        month_expenses = get_total(
            monthly_transactions.filter(transaction_type='EXPENSE')
        )

        financial_data = {
            'total_balance': total_balance,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'overall_expenses': overall_expenses,
            'month_income': month_income,
            'month_expenses': month_expenses,
        }

    recent_transactions = transactions.select_related(
        'account', 'category'
    ).order_by('-date', '-created_at')[:8]

    context = {
        'currency': currency,
        'accounts': accounts,
        'selected_filter': selected_filter,
        'filter_label': filter_label,
        'balances_visible': balances_visible,
        'recent_transactions': recent_transactions,
        'today': today,
        **financial_data,
    }

    response = render(request, 'core/dashboard.html', context)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    return response


@login_required
@require_POST
@never_cache
def toggle_balance_visibility(request):
    action = request.POST.get('action')

    if action == 'hide':
        request.session.pop('balances_visible_until', None)
        messages.success(request, 'Your financial information is now hidden.')

    elif action == 'reveal':
        password = request.POST.get('password', '')

        if request.user.check_password(password):
            request.session['balances_visible_until'] = (
                int(time.time()) + BALANCE_VISIBILITY_SECONDS
            )
            messages.success(request, 'Your financial information is now visible.')
        else:
            messages.error(
                request,
                'Incorrect password. Your financial information remains hidden.'
            )

    next_url = request.POST.get('next', '/')

    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()}
    ):
        next_url = '/'

    response = redirect(next_url)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    return response
