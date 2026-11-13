
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from core.security import financial_information_visible
from .models import Transaction, Transfer
from .forms import TransactionForm, TransferForm

from django.urls import reverse

from .models import RecurringTransaction
from .forms import RecurringTransactionForm
from core.security import financial_information_visible

import csv
from django.http import HttpResponse

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


@login_required
@never_cache
def transaction_list(request):
    balances_visible = financial_information_visible(request)

    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related('account', 'category')

    # Filter by transaction type.
    selected_type = request.GET.get('type', '')

    if selected_type in ['INCOME', 'EXPENSE']:
        transactions = transactions.filter(
            transaction_type=selected_type
        )
    else:
        selected_type = ''

    # Search transactions.
    search_query = request.GET.get('search', '').strip()

    if search_query:
        transactions = transactions.filter(
            Q(description__icontains=search_query)
            | Q(notes__icontains=search_query)
            | Q(category__name__icontains=search_query)
            | Q(account__name__icontains=search_query)
        )

    # Pagination.
    paginator = Paginator(transactions, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Do not expose actual amounts to the template when locked.
    if not balances_visible:
        for transaction in page_obj.object_list:
            transaction.amount = None

    context = {
        'page_obj': page_obj,
        'selected_type': selected_type,
        'search_query': search_query,
        'balances_visible': balances_visible,
    }

    return render(
        request,
        'transactions/transaction_list.html',
        context
    )



@login_required
@never_cache
def transaction_create(request):
    balances_visible = financial_information_visible(request)

    # Handle form submission.
    if request.method == 'POST':

        # If locked, temporarily preserve the submitted data.
        if not balances_visible:
            request.session['pending_transaction'] = request.POST.dict()

            messages.info(
                request,
                'Your transaction details have been preserved. '
                'Verify your password using the eye icon to continue.'
            )

            return redirect('transaction_create')

        form = TransactionForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()

            # Clear any previously preserved form data.
            request.session.pop('pending_transaction', None)

            messages.success(
                request,
                'Transaction added successfully.'
            )

            return redirect('transaction_list')

    else:
        # Check whether there is a previously submitted transaction.
        pending_data = request.session.pop(
            'pending_transaction', None
        )

        if pending_data and balances_visible:
            form = TransactionForm(
                pending_data,
                user=request.user
            )

        elif balances_visible:
            initial = {}

            transaction_type = request.GET.get('type')

            if transaction_type in ['INCOME', 'EXPENSE']:
                initial['transaction_type'] = transaction_type

            form = TransactionForm(
                user=request.user,
                initial=initial
            )

        else:
            form = None

    return render(
        request,
        'transactions/transaction_form.html',
        {
            'form': form,
            'page_title': 'Add Transaction',
            'button_text': 'Save Transaction',
            'balances_visible': balances_visible,
        }
    )


@login_required
@never_cache
def transaction_update(request, pk):
    transaction = get_object_or_404(
        Transaction,
        pk=pk,
        user=request.user
    )

    balances_visible = financial_information_visible(request)

    if not balances_visible:
        if request.method == 'POST':
            messages.warning(
                request,
                'Your financial information is locked. Verify your password using the eye icon to continue.'
            )
            return redirect('transaction_update', pk=pk)

        return render(
            request,
            'transactions/transaction_form.html',
            {
                'form': None,
                'page_title': 'Edit Transaction',
                'button_text': 'Save Changes',
                'balances_visible': False,
            }
        )

    if request.method == 'POST':
        form = TransactionForm(
            request.POST,
            instance=transaction,
            user=request.user
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Transaction updated successfully.'
            )
            return redirect('transaction_list')

    else:
        form = TransactionForm(
            instance=transaction,
            user=request.user
        )

    return render(
        request,
        'transactions/transaction_form.html',
        {
            'form': form,
            'page_title': 'Edit Transaction',
            'button_text': 'Save Changes',
            'balances_visible': True,
        }
    )


@login_required
@require_POST
@never_cache
def transaction_delete(request, pk):
    transaction = get_object_or_404(
        Transaction,
        pk=pk,
        user=request.user
    )

    transaction.delete()

    messages.success(
        request,
        'Transaction deleted successfully.'
    )

    return redirect('transaction_list')



@login_required
@never_cache
def transfer_list(request):
    transfers = Transfer.objects.filter(
        user=request.user
    ).select_related(
        'from_account',
        'to_account'
    )

    balances_visible = financial_information_visible(request)

    if not balances_visible:
        for transfer in transfers:
            transfer.amount = None

    return render(
        request,
        'transactions/transfer_list.html',
        {
            'transfers': transfers,
            'balances_visible': balances_visible,
        }
    )


@login_required
@never_cache
def transfer_create(request):
    balances_visible = financial_information_visible(request)
    session_key = 'pending_transfer_create'

    if request.method == 'POST' and not balances_visible:
        request.session[session_key] = request.POST.dict()
        messages.warning(
            request,
            'Your transfer details have been preserved. Verify your password using the eye icon to continue.'
        )
        return redirect('transfer_create')

    if request.method == 'POST':
        form = TransferForm(request.POST, user=request.user)

        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.save()

            request.session.pop(session_key, None)

            messages.success(request, 'Transfer recorded successfully.')
            return redirect('transfer_list')

    else:
        pending_data = request.session.pop(session_key, None)

        if balances_visible and pending_data:
            form = TransferForm(pending_data, user=request.user)
        elif balances_visible:
            form = TransferForm(user=request.user)
        else:
            form = None

    return render(
        request,
        'transactions/transfer_form.html',
        {
            'form': form,
            'page_title': 'New Transfer',
            'button_text': 'Save Transfer',
            'balances_visible': balances_visible,
        }
    )


@login_required
@never_cache
def transfer_update(request, pk):
    transfer = get_object_or_404(
        Transfer,
        pk=pk,
        user=request.user
    )

    balances_visible = financial_information_visible(request)
    session_key = f'pending_transfer_update_{pk}'

    if request.method == 'POST' and not balances_visible:
        request.session[session_key] = request.POST.dict()
        messages.warning(
            request,
            'Your changes have been preserved. Verify your password using the eye icon to continue.'
        )
        return redirect('transfer_update', pk=pk)

    if not balances_visible:
        form = None

    elif request.method == 'POST':
        form = TransferForm(
            request.POST,
            instance=transfer,
            user=request.user
        )

        if form.is_valid():
            form.save()
            request.session.pop(session_key, None)

            messages.success(request, 'Transfer updated successfully.')
            return redirect('transfer_list')

    else:
        pending_data = request.session.pop(session_key, None)

        if pending_data:
            form = TransferForm(
                pending_data,
                instance=transfer,
                user=request.user
            )
        else:
            form = TransferForm(
                instance=transfer,
                user=request.user
            )

    return render(
        request,
        'transactions/transfer_form.html',
        {
            'form': form,
            'page_title': 'Edit Transfer',
            'button_text': 'Save Changes',
            'balances_visible': balances_visible,
        }
    )


@login_required
@require_POST
@never_cache
def transfer_delete(request, pk):
    if not financial_information_visible(request):
        messages.warning(
            request,
            'Verify your password using the eye icon before deleting a transfer.'
        )
        return redirect('transfer_list')

    transfer = get_object_or_404(
        Transfer,
        pk=pk,
        user=request.user
    )

    transfer.delete()

    messages.success(request, 'Transfer deleted successfully.')
    return redirect('transfer_list')



@login_required
@never_cache
def recurring_list(request):

    balances_visible = financial_information_visible(request)

    schedules = RecurringTransaction.objects.filter(
        user=request.user
    ).select_related(
        'account',
        'category'
    ).order_by(
        'next_due_date',
        '-created_at'
    )

    # Filter by transaction type.
    transaction_type = request.GET.get('type', '')

    if transaction_type in ('INCOME', 'EXPENSE'):
        schedules = schedules.filter(
            transaction_type=transaction_type
        )

    # Filter by schedule status.
    status = request.GET.get('status', 'all')

    if status == 'active':
        schedules = schedules.filter(is_active=True)
    elif status == 'inactive':
        schedules = schedules.filter(is_active=False)
    else:
        status = 'all'

    # Do not expose monetary amounts while visibility is locked.
    if not balances_visible:
        for schedule in schedules:
            schedule.amount = None

    paginator = Paginator(schedules, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    total_schedules = RecurringTransaction.objects.filter(
        user=request.user
    ).count()

    active_schedules = RecurringTransaction.objects.filter(
        user=request.user,
        is_active=True
    ).count()

    inactive_schedules = total_schedules - active_schedules


    total_schedules = RecurringTransaction.objects.filter(
        user=request.user
    ).count()

    active_schedules = RecurringTransaction.objects.filter(
        user=request.user,
        is_active=True
    ).count()

    inactive_schedules = total_schedules - active_schedules

    context = {
    'page_obj': page_obj,
    'schedules': page_obj.object_list,
    'balances_visible': balances_visible,
    'selected_type': transaction_type,
    'selected_status': status,

    'total_schedules': RecurringTransaction.objects.filter(
        user=request.user
    ).count(),

    'active_schedules': RecurringTransaction.objects.filter(
        user=request.user,
        is_active=True
    ).count(),

    'inactive_schedules': (
        RecurringTransaction.objects.filter(
            user=request.user
        ).count()
        -
        RecurringTransaction.objects.filter(
            user=request.user,
            is_active=True
        ).count()
    ),
}

    response = render(
        request,
        'transactions/recurring_list.html',
        context
    )

    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response


@login_required
@never_cache
def recurring_create(request):

    balances_visible = financial_information_visible(request)

    if not balances_visible:
        messages.warning(
            request,
            'Verify your password before creating a recurring schedule.'
        )

        return render(
            request,
            'transactions/recurring_form.html',
            {
                'form': None,
                'balances_visible': False,
                'page_title': 'Create Recurring Schedule',
            }
        )

    if request.method == 'POST':

        form = RecurringTransactionForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            schedule = form.save(commit=False)
            schedule.user = request.user
            schedule.save()

            messages.success(
                request,
                'Recurring schedule created successfully.'
            )

            return redirect('recurring_list')

    else:
        form = RecurringTransactionForm(
            user=request.user
        )

    return render(
        request,
        'transactions/recurring_form.html',
        {
            'form': form,
            'balances_visible': True,
            'page_title': 'Create Recurring Schedule',
        }
    )


@login_required
@never_cache
def recurring_update(request, pk):

    schedule = get_object_or_404(
        RecurringTransaction,
        pk=pk,
        user=request.user
    )

    balances_visible = financial_information_visible(request)

    if not balances_visible:
        messages.warning(
            request,
            'Verify your password before editing a recurring schedule.'
        )

        return render(
            request,
            'transactions/recurring_form.html',
            {
                'form': None,
                'balances_visible': False,
                'page_title': 'Edit Recurring Schedule',
                'schedule': schedule,
            }
        )

    if request.method == 'POST':

        form = RecurringTransactionForm(
            request.POST,
            instance=schedule,
            user=request.user
        )

        if form.is_valid():

            updated_schedule = form.save(commit=False)
            updated_schedule.user = request.user
            updated_schedule.save()

            messages.success(
                request,
                'Recurring schedule updated successfully.'
            )

            return redirect('recurring_list')

    else:
        form = RecurringTransactionForm(
            instance=schedule,
            user=request.user
        )

    return render(
        request,
        'transactions/recurring_form.html',
        {
            'form': form,
            'balances_visible': True,
            'page_title': 'Edit Recurring Schedule',
            'schedule': schedule,
        }
    )


@login_required
@require_POST
@never_cache
def recurring_toggle_status(request, pk):

    schedule = get_object_or_404(
        RecurringTransaction,
        pk=pk,
        user=request.user
    )

    if not financial_information_visible(request):
        messages.warning(
            request,
            'Verify your password before changing a recurring schedule.'
        )
        return redirect('recurring_list')

    # Resume an existing paused schedule.
    if not schedule.is_active:

        if not schedule.account.is_active:
            messages.error(
                request,
                'This schedule cannot be resumed because its account is inactive.'
            )
            return redirect('recurring_list')

        if not schedule.category.is_active:
            messages.error(
                request,
                'This schedule cannot be resumed because its category is inactive.'
            )
            return redirect('recurring_list')

        if (
            schedule.end_date
            and schedule.next_due_date > schedule.end_date
        ):
            messages.error(
                request,
                'This schedule has already reached its end date. '
                'Edit its dates before resuming it.'
            )
            return redirect('recurring_list')

        schedule.is_active = True

        messages.success(
            request,
            'Recurring schedule resumed successfully.'
        )

    else:
        schedule.is_active = False

        messages.success(
            request,
            'Recurring schedule paused successfully.'
        )

    schedule.save(
        update_fields=['is_active', 'updated_at']
    )

    return redirect('recurring_list')


@login_required
@require_POST
@never_cache
def recurring_delete(request, pk):

    schedule = get_object_or_404(
        RecurringTransaction,
        pk=pk,
        user=request.user
    )

    if not financial_information_visible(request):
        messages.warning(
            request,
            'Verify your password before deleting a recurring schedule.'
        )
        return redirect('recurring_list')

    schedule.delete()

    messages.success(
        request,
        'Recurring schedule deleted. Previously generated transactions '
        'have been preserved.'
    )

    return redirect('recurring_list')


@login_required
@never_cache
def transaction_export_csv(request):

    # Financial information must be unlocked before exporting.
    if not financial_information_visible(request):
        messages.warning(
            request,
            'Please unlock financial information before exporting.'
        )
        return redirect('transaction_list')

    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related(
        'account',
        'category'
    ).order_by('-date', '-created_at')

    response = HttpResponse(
        content_type='text/csv; charset=utf-8'
    )

    response['Content-Disposition'] = (
        'attachment; filename="expenseflow_transactions.csv"'
    )

    # Helps Excel display UTF-8 characters correctly.
    response.write('\ufeff')

    writer = csv.writer(response)

    writer.writerow([
        'Date',
        'Transaction Type',
        'Description',
        'Account',
        'Category',
        'Amount',
        'Currency',
        'Payment Method',
        'Notes',
    ])

    for item in transactions:
        writer.writerow([
            item.date.isoformat(),
            item.transaction_type,
            item.description,
            item.account.name,
            item.category.name,
            str(item.amount),
            item.account.currency,
            item.payment_method,
            item.notes,
        ])

    return response


@login_required
@never_cache
def transaction_export_excel(request):

    if not financial_information_visible(request):
        messages.warning(
            request,
            'Please unlock financial information before exporting.'
        )
        return redirect('transaction_list')

    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related(
        'account',
        'category'
    ).order_by('-date', '-created_at')

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Transactions'

    headers = [
        'Date',
        'Transaction Type',
        'Description',
        'Account',
        'Category',
        'Amount',
        'Currency',
        'Payment Method',
        'Notes',
    ]

    worksheet.append(headers)

    # Style the header row.
    for cell in worksheet[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(
            start_color='343A40',
            end_color='343A40',
            fill_type='solid'
        )
        cell.alignment = Alignment(horizontal='center')

    # Add transaction records.
    for item in transactions:
        worksheet.append([
            item.date.isoformat(),
            item.transaction_type,
            item.description,
            item.account.name,
            item.category.name,
            float(item.amount),
            item.account.currency,
            item.payment_method,
            item.notes,
        ])

    # Adjust column widths automatically.
    for column_cells in worksheet.columns:
        max_length = max(
            len(str(cell.value or ''))
            for cell in column_cells
        )

        column_letter = get_column_letter(
            column_cells[0].column
        )

        worksheet.column_dimensions[column_letter].width = min(
            max_length + 3,
            40
        )

    worksheet.freeze_panes = 'A2'
    worksheet.auto_filter.ref = worksheet.dimensions

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        )
    )

    response['Content-Disposition'] = (
        'attachment; filename="expenseflow_transactions.xlsx"'
    )

    workbook.save(response)

    return response