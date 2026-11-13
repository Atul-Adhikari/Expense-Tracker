
from django import template
from core.date_utils import format_date

register = template.Library()


@register.simple_tag(takes_context=True)
def preferred_date(context, value):
    """
    Display a date using the logged-in user's preferred calendar.
    """
    request = context.get('request')

    calendar = 'AD'

    if request and request.user.is_authenticated:
        calendar = request.user.preferred_calendar

    try:
        return format_date(value, calendar)
    except (ValueError, TypeError):
        return value
