
from django.core.management.base import BaseCommand

from transactions.services import generate_due_transactions


class Command(BaseCommand):

    help = 'Generate all due recurring transactions.'

    def handle(self, *args, **options):

        generated_count = generate_due_transactions()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated {generated_count} recurring transaction(s).'
            )
        )
