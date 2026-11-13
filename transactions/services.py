
import calendar
from datetime import timedelta

from django.db import transaction as db_transaction
from django.utils import timezone

from .models import RecurringTransaction, Transaction


def calculate_next_due_date(
    current_date,
    frequency,
    interval,
    anchor_date=None
):
    """
    Calculate the next occurrence while preserving the original
    schedule date for monthly and yearly repetitions.
    """

    anchor_date = anchor_date or current_date

    if frequency == 'DAILY':
        return current_date + timedelta(days=interval)

    if frequency == 'WEEKLY':
        return current_date + timedelta(weeks=interval)

    if frequency == 'MONTHLY':

        month_index = (
            current_date.year * 12
            + current_date.month - 1
            + interval
        )

        year = month_index // 12
        month = month_index % 12 + 1

        last_day = calendar.monthrange(year, month)[1]

        anchor_is_month_end = (
            anchor_date.day
            == calendar.monthrange(
                anchor_date.year,
                anchor_date.month
            )[1]
        )

        if anchor_is_month_end:
            day = last_day
        else:
            day = min(anchor_date.day, last_day)

        return current_date.replace(
            year=year,
            month=month,
            day=day
        )

    if frequency == 'YEARLY':

        year = current_date.year + interval
        month = anchor_date.month

        last_day = calendar.monthrange(year, month)[1]
        day = min(anchor_date.day, last_day)

        return current_date.replace(
            year=year,
            month=month,
            day=day
        )

    raise ValueError('Unsupported recurring frequency.')


def generate_due_transactions(user=None, today=None):

    today = today or timezone.localdate()

    schedules = RecurringTransaction.objects.filter(
        is_active=True,
        next_due_date__lte=today,
        account__is_active=True,
        category__is_active=True,
    ).select_related(
        'user',
        'account',
        'category'
    ).order_by(
        'next_due_date',
        'id'
    )

    if user is not None:
        schedules = schedules.filter(user=user)

    generated_count = 0

    schedule_ids = schedules.values_list('id', flat=True)

    for schedule_id in schedule_ids:

        with db_transaction.atomic():

            try:
                schedule = (
                    RecurringTransaction.objects
                    .select_for_update()
                    .select_related(
                        'user',
                        'account',
                        'category'
                    )
                    .get(
                        pk=schedule_id,
                        is_active=True,
                        next_due_date__lte=today
                    )
                )

            except RecurringTransaction.DoesNotExist:
                continue

            if (
                not schedule.account.is_active
                or not schedule.category.is_active
            ):
                continue

            while (
                schedule.is_active
                and schedule.next_due_date <= today
            ):

                due_date = schedule.next_due_date

                # Do not generate transactions beyond the end date.
                if schedule.end_date and due_date > schedule.end_date:
                    schedule.is_active = False
                    break

                # Check whether this schedule already generated
                # a transaction for this particular date.
                duplicate_exists = Transaction.objects.filter(
                    recurring_schedule=schedule,
                    date=due_date
                ).exists()

                if not duplicate_exists:

                    Transaction.objects.create(
                        recurring_schedule=schedule,
                        user=schedule.user,
                        account=schedule.account,
                        category=schedule.category,
                        transaction_type=schedule.transaction_type,
                        amount=schedule.amount,
                        date=due_date,
                        description=schedule.description,
                        payment_method=schedule.payment_method,
                        notes=schedule.notes,
                    )

                    generated_count += 1

                schedule.last_generated_date = due_date

                schedule.next_due_date = calculate_next_due_date(
                    current_date=due_date,
                    frequency=schedule.frequency,
                    interval=schedule.interval,
                    anchor_date=schedule.start_date,
                )

                # Automatically complete schedules after
                # their final scheduled occurrence.
                if (
                    schedule.end_date
                    and schedule.next_due_date > schedule.end_date
                ):
                    schedule.is_active = False

            schedule.save(
                update_fields=[
                    'last_generated_date',
                    'next_due_date',
                    'is_active',
                    'updated_at',
                ]
            )

    return generated_count
