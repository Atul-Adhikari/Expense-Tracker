
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from nepali_date_library import ADtoBS, BStoAD

from core.security import financial_information_visible
from transactions.models import Transaction

from .models import Budget
from .forms import BudgetForm


BS_MONTHS = [
    'Baisakh', 'Jestha', 'Ashadh', 'Shrawan',
    'Bhadra', 'Ashwin', 'Kartik', 'Mangsir',
    'Poush', 'Magh', 'Falgun', 'Chaitra',
]


def require_visible_balances(request):
    if financial_information_visible(request):
        return True

    messages.warning(
        request,
        'Please click the eye icon and verify your password before continuing.'
    )
    return False


def get_bs_month_range(year, month):
    """Return AD boundaries for a selected BS month."""

    start_bs = f'{year}-{month:02d}-01'

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    next_start_bs = f'{next_year}-{next_month:02d}-01'

    start_date = date.fromisoformat(str(BStoAD(start_bs)))
    end_date = date.fromisoformat(str(BStoAD(next_start_bs)))

    return start_date, end_date


def get_bs_month_options(current_bs_year):
    options = []

    for year in range(current_bs_year - 5, current_bs_year + 2):
        for month, month_name in enumerate(BS_MONTHS, start=1):
            options.append({
                'value': f'{year}-{month:02d}',
                'label': f'{month_name} {year}',
            })

    return options


def get_selected_bs_month(request, today):
    """Read and validate the selected BS month."""

    current_bs = str(ADtoBS(today.isoformat()))
    current_year, current_month, _ = map(int, current_bs.split('-'))

    month_value = request.GET.get(
        'month',
        f'{current_year}-{current_month:02d}'
    )

    try:
        year_text, month_text = month_value.split('-')
        year, month = int(year_text), int(month_text)

        if len(year_text) != 4 or len(month_text) != 2:
            raise ValueError

        if not 1976 <= year <= 2100 or not 1 <= month <= 12:
            raise ValueError

        start_date, end_date = get_bs_month_range(year, month)

        return (
            year,
            month,
            f'{year}-{month:02d}',
            f'{BS_MONTHS[month - 1]} {year}',
            start_date,
            end_date,
            current_year,
        )

    except (ValueError, TypeError, OverflowError):
        start_date, end_date = get_bs_month_range(
            current_year,
            current_month
        )

        return (
            current_year,
            current_month,
            f'{current_year}-{current_month:02d}',
            f'{BS_MONTHS[current_month - 1]} {current_year}',
            start_date,
            end_date,
            current_year,
        )


def get_budget_spending(budget, start_date, end_date):
    expenses = Transaction.objects.filter(
        user=budget.user,
        transaction_type='EXPENSE',
        account__currency=budget.currency,
        date__gte=start_date,
        date__lt=end_date
    )

    if budget.category_id:
        expenses = expenses.filter(category=budget.category)

    return (
        expenses.aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )


def get_budget_form_data(request, session_key):
    if not financial_information_visible(request):
        return None

    return request.session.pop(session_key, None)


def preserve_budget_form_data(request, session_key):
    pending_data = request.POST.dict()
    pending_data.pop('csrfmiddlewaretoken', None)
    request.session[session_key] = pending_data


@login_required
@never_cache
def budget_list(request):

    today = timezone.localdate()

    (
        selected_year,
        selected_month_number,
        month_value,
        month_label,
        start_date,
        end_date,
        current_bs_year,
    ) = get_selected_bs_month(request, today)

    budgets = list(
        Budget.objects.filter(
            user=request.user,
            period_start=start_date
        ).select_related('category').order_by(
            'currency', 'category__name'
        )
    )

    balances_visible = financial_information_visible(request)

    budget_items = []
    currency_totals = {}

    for budget in budgets:

        item = {
            'budget': budget,
            'spent': None,
            'remaining': None,
            'percentage': None,
            'status': None,
            'overspent_amount': None,
        }

        if balances_visible:

            spent = get_budget_spending(
                budget,
                start_date,
                end_date
            )

            remaining = budget.amount - spent

            percentage = (spent / budget.amount) * Decimal('100')
            percentage = min(percentage, Decimal('100'))

            if spent > budget.amount:
                status = 'exceeded'
            elif percentage >= Decimal('80'):
                status = 'warning'
            else:
                status = 'healthy'

            item.update({
                'spent': spent,
                'remaining': remaining,
                'percentage': round(percentage, 1),
                'status': status,
                'overspent_amount': max(
                    -remaining,
                    Decimal('0.00')
                ),
            })

            currency_totals.setdefault(
                budget.currency,
                Decimal('0.00')
            )
            currency_totals[budget.currency] += budget.amount

        else:
            # Do not expose actual budget amounts while locked.
            budget.amount = None

        budget_items.append(item)

    currency_summaries = [
        {
            'currency': currency_code,
            'budget': amount,
        }
        for currency_code, amount in sorted(currency_totals.items())
    ]

    context = {
        'budget_items': budget_items,
        'selected_month': month_value,
        'selected_month_label': month_label,
        'bs_month_options': get_bs_month_options(current_bs_year),
        'currency_summaries': currency_summaries,
        'has_budgets': bool(budget_items),
        'balances_visible': balances_visible,
        'budget_count': len(budget_items),
    }

    response = render(
        request,
        'budgets/budget_list.html',
        context
    )
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    return response


@login_required
@never_cache
def budget_create(request):

    balances_visible = financial_information_visible(request)
    session_key = 'pending_budget_create'

    today = timezone.localdate()
    current_bs = str(ADtoBS(today.isoformat()))

    if request.method == 'POST':

        if not require_visible_balances(request):
            preserve_budget_form_data(request, session_key)
            return redirect('budget_create')

        form = BudgetForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()

            request.session.pop(session_key, None)

            messages.success(
                request,
                'Your budget was created successfully.'
            )

            bs_month = str(ADtoBS(budget.period_start.isoformat()))[:7]

            return redirect(
                f"{reverse('budget_list')}?month={bs_month}"
            )

    elif balances_visible:

        pending_data = get_budget_form_data(
            request,
            session_key
        )

        if pending_data:
            form = BudgetForm(
                pending_data,
                user=request.user
            )
        else:
            form = BudgetForm(
                user=request.user,
                initial={
                    'currency': request.user.preferred_currency,
                    'period_start': current_bs[:7],
                }
            )

    else:
        form = None

    return render(
        request,
        'budgets/budget_form.html',
        {
            'form': form,
            'page_title': 'Create Budget',
            'button_text': 'Create Budget',
            'balances_visible': balances_visible,
        }
    )


@login_required
@never_cache
def budget_update(request, pk):

    budget = get_object_or_404(
        Budget,
        pk=pk,
        user=request.user
    )

    balances_visible = financial_information_visible(request)
    session_key = f'pending_budget_update_{pk}'

    if request.method == 'POST':

        if not require_visible_balances(request):
            preserve_budget_form_data(request, session_key)
            return redirect('budget_update', pk=pk)

        form = BudgetForm(
            request.POST,
            instance=budget,
            user=request.user
        )

        if form.is_valid():

            updated_budget = form.save()

            request.session.pop(session_key, None)

            messages.success(
                request,
                'Your budget was updated successfully.'
            )

            bs_month = str(
                ADtoBS(updated_budget.period_start.isoformat())
            )[:7]

            return redirect(
                f"{reverse('budget_list')}?month={bs_month}"
            )

    elif balances_visible:

        pending_data = get_budget_form_data(
            request,
            session_key
        )

        if pending_data:
            form = BudgetForm(
                pending_data,
                instance=budget,
                user=request.user
            )
        else:
            form = BudgetForm(
                instance=budget,
                user=request.user
            )

    else:
        form = None

    return render(
        request,
        'budgets/budget_form.html',
        {
            'form': form,
            'page_title': 'Edit Budget',
            'button_text': 'Save Changes',
            'budget': budget,
            'balances_visible': balances_visible,
        }
    )


@login_required
@require_POST
@never_cache
def budget_delete(request, pk):

    budget = get_object_or_404(
        Budget,
        pk=pk,
        user=request.user
    )

    bs_month = str(ADtoBS(budget.period_start.isoformat()))[:7]

    budget.delete()

    messages.success(
        request,
        'Your budget was deleted successfully.'
    )

    return redirect(
        f"{reverse('budget_list')}?month={bs_month}"
    )
