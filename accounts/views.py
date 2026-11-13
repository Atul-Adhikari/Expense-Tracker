import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .models import Account
from .forms import AccountForm

from core.security import financial_information_visible


@login_required
@never_cache
def account_list(request):

    balances_visible = financial_information_visible(request)

    accounts = Account.objects.filter(
        user=request.user
    ).order_by('-is_active', 'name')

    active_accounts = accounts.filter(is_active=True).count()
    inactive_accounts = accounts.filter(is_active=False).count()

    # Do not pass opening balances to the template while locked.
    if not balances_visible:
        for account in accounts:
            account.opening_balance = None

    context = {
        'accounts': accounts,
        'active_accounts': active_accounts,
        'inactive_accounts': inactive_accounts,
        'balances_visible': balances_visible,
    }

    return render(
        request,
        'accounts/account_list.html',
        context
    )


@login_required
@never_cache
def account_create(request):

    balances_visible = financial_information_visible(request)

    if request.method == 'POST':

        if not balances_visible:
            messages.warning(
                request,
                'Please verify your password using the eye icon before creating an account.'
            )
            return redirect('account_create')

        form = AccountForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()

            messages.success(
                request,
                f'{account.name} was created successfully.'
            )

            return redirect('account_list')

    elif balances_visible:

        form = AccountForm(user=request.user)

    else:
        form = None

    return render(
        request,
        'accounts/account_form.html',
        {
            'form': form,
            'page_title': 'Add New Account',
            'button_text': 'Create Account',
            'balances_visible': balances_visible,
        }
    )


@login_required
@never_cache
def account_update(request, pk):

    account = get_object_or_404(
        Account,
        pk=pk,
        user=request.user
    )

    balances_visible = financial_information_visible(request)

    if request.method == 'POST':

        if not balances_visible:
            messages.warning(
                request,
                'Your financial information is locked. Verify your password using the eye icon to continue.'
            )
            return redirect(
                'account_update',
                pk=pk
            )

        form = AccountForm(
            request.POST,
            instance=account,
            user=request.user
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f'{account.name} was updated successfully.'
            )

            return redirect('account_list')

    elif balances_visible:

        form = AccountForm(
            instance=account,
            user=request.user
        )

    else:
        form = None

    return render(
        request,
        'accounts/account_form.html',
        {
            'form': form,
            'page_title': 'Edit Account',
            'button_text': 'Save Changes',
            'account': account,
            'balances_visible': balances_visible,
        }
    )


@login_required
@require_POST
@never_cache
def account_toggle_status(request, pk):

    account = get_object_or_404(
        Account,
        pk=pk,
        user=request.user
    )

    account.is_active = not account.is_active

    account.save(
        update_fields=['is_active', 'updated_at']
    )

    if account.is_active:
        messages.success(
            request,
            f'{account.name} has been reactivated.'
        )
    else:
        messages.success(
            request,
            f'{account.name} has been deactivated.'
        )

    return redirect('account_list')