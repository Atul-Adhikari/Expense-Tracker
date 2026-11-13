import time


def financial_information_visible(request):
    """
    Check whether the user's financial information
    is currently unlocked in this session.
    """

    visible_until = request.session.get(
        'balances_visible_until', 0
    )

    if time.time() < visible_until:
        return True

    # Remove expired visibility sessions.
    if visible_until:
        request.session.pop('balances_visible_until', None)

    return False