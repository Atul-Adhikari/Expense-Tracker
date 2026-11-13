
from datetime import date, datetime

from nepali_date_library import ADtoBS, BStoAD


def convert_ad_to_bs(ad_date):
    """
    Convert an AD date into a BS date string.
    Accepts a Python date, datetime, or YYYY-MM-DD string.
    """
    if not ad_date:
        return ''

    if isinstance(ad_date, (date, datetime)):
        ad_date = ad_date.strftime('%Y-%m-%d')

    converted = ADtoBS(str(ad_date))
    return str(converted)


def convert_bs_to_ad(bs_date):
    """
    Convert a BS date into an AD date string.
    Accepts a YYYY-MM-DD string.
    """
    if not bs_date:
        return ''

    converted = BStoAD(str(bs_date))
    return str(converted)


def format_date(date_value, calendar='BS'):
    """
    Format a stored AD date according to the selected calendar.
    """
    if not date_value:
        return ''

    if isinstance(date_value, (date, datetime)):
        ad_date = date_value.strftime('%Y-%m-%d')
    else:
        ad_date = str(date_value)

    if calendar == 'BS':
        return convert_ad_to_bs(ad_date)

    return ad_date
