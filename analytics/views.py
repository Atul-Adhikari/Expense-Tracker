
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.cache import never_cache

from accounts.models import Account
from core.security import financial_information_visible
from transactions.models import Transaction, Transfer


def get_total(queryset):
    return (
        queryset.aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )


@login_required
@never_cache
def analytics_dashboard(request):
    today = timezone.localdate()

    # Default range: current month and previous five months.
    default_start = date(today.year, today.month, 1)

    for _ in range(5):
        if default_start.month == 1:
            default_start = date(
                default_start.year - 1, 12, 1
            )
        else:
            default_start = date(
                default_start.year,
                default_start.month - 1,
                1
            )

    start_date = (
        parse_date(request.GET.get('start_date', ''))
        or default_start
    )
    end_date = (
        parse_date(request.GET.get('end_date', ''))
        or today
    )

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # Available currencies belonging to this user.
    available_currencies = list(
        Account.objects.filter(user=request.user)
        .values_list('currency', flat=True)
        .distinct()
        .order_by('currency')
    )

    preferred_currency = request.user.preferred_currency
    requested_currency = request.GET.get(
        'currency', preferred_currency
    )

    if requested_currency not in available_currencies:
        selected_currency = (
            preferred_currency
            if preferred_currency in available_currencies
            else (
                available_currencies[0]
                if available_currencies
                else 'NPR'
            )
        )
    else:
        selected_currency = requested_currency

    balances_visible = financial_information_visible(request)

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'selected_currency': selected_currency,
        'available_currencies': available_currencies,
        'balances_visible': balances_visible,
        'has_accounts': bool(available_currencies),
        'total_income': None,
        'total_expenses': None,
        'net_savings': None,
        'savings_rate': None,
        'monthly_labels': [],
        'monthly_income': [],
        'monthly_expenses': [],
        'category_labels': [],
        'category_values': [],
        'account_summaries': [],
    }

    # Do not calculate or send financial figures while locked.
    if balances_visible and available_currencies:

        transactions = Transaction.objects.filter(
            user=request.user,
            account__currency=selected_currency,
            date__gte=start_date,
            date__lte=end_date,
        )

        income_total = get_total(
            transactions.filter(transaction_type='INCOME')
        )

        expense_total = get_total(
            transactions.filter(transaction_type='EXPENSE')
        )

        net_savings = income_total - expense_total

        savings_rate = (
            (net_savings / income_total) * 100
            if income_total > 0
            else Decimal('0.00')
        )

        # Monthly income and expense chart.
        monthly_data = {}

        current_month = date(
            start_date.year, start_date.month, 1
        )
        last_month = date(
            end_date.year, end_date.month, 1
        )

        while current_month <= last_month:
            month_key = current_month.strftime('%Y-%m')

            monthly_data[month_key] = {
                'label': current_month.strftime('%b %Y'),
                'income': Decimal('0.00'),
                'expenses': Decimal('0.00'),
            }

            if current_month.month == 12:
                current_month = date(
                    current_month.year + 1, 1, 1
                )
            else:
                current_month = date(
                    current_month.year,
                    current_month.month + 1,
                    1
                )

        monthly_transactions = (
            transactions.values('date', 'transaction_type')
            .annotate(total=Sum('amount'))
        )

        for item in monthly_transactions:
            month_key = item['date'].strftime('%Y-%m')

            if month_key in monthly_data:
                if item['transaction_type'] == 'INCOME':
                    monthly_data[month_key]['income'] += item['total']
                else:
                    monthly_data[month_key]['expenses'] += item['total']

        context['monthly_labels'] = [
            item['label'] for item in monthly_data.values()
        ]

        context['monthly_income'] = [
            float(item['income'])
            for item in monthly_data.values()
        ]

        context['monthly_expenses'] = [
            float(item['expenses'])
            for item in monthly_data.values()
        ]

        # Category-wise expense breakdown.
        category_data = (
            transactions.filter(transaction_type='EXPENSE')
            .values('category__name')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

        context['category_labels'] = [
            item['category__name'] or 'Uncategorised'
            for item in category_data
        ]

        context['category_values'] = [
            float(item['total'])
            for item in category_data
        ]

        # Account balances include all-time transfers.
        accounts = Account.objects.filter(
            user=request.user,
            currency=selected_currency,
            is_active=True,
        ).order_by('name')

        account_summaries = []

        for account in accounts:

            account_transactions = Transaction.objects.filter(
                user=request.user,
                account=account,
            )

            account_income = get_total(
                account_transactions.filter(
                    transaction_type='INCOME'
                )
            )

            account_expenses = get_total(
                account_transactions.filter(
                    transaction_type='EXPENSE'
                )
            )

            # Money transferred into this account.
            incoming_transfers = get_total(
                Transfer.objects.filter(
                    user=request.user,
                    to_account=account,
                )
            )

            # Money transferred out of this account.
            outgoing_transfers = get_total(
                Transfer.objects.filter(
                    user=request.user,
                    from_account=account,
                )
            )

            balance = (
                account.opening_balance
                + account_income
                - account_expenses
                + incoming_transfers
                - outgoing_transfers
            )

            account_summaries.append({
                'name': account.name,
                'account_type': account.get_account_type_display(),
                'balance': balance,
            })

        context.update({
            'total_income': income_total,
            'total_expenses': expense_total,
            'net_savings': net_savings,
            'savings_rate': round(savings_rate, 2),
            'account_summaries': account_summaries,
        })

    return render(
        request,
        'analytics/analytics_dashboard.html',
        context
    )
