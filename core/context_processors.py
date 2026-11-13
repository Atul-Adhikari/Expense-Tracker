import time


def financial_visibility(request):
    visible_until = request.session.get(
        'balances_visible_until',
        0
    )

    return {
        'balances_visible': time.time() < visible_until
    }