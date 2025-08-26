"""
Django management command to generate payment reports
Usage: python manage.py payment_report --month 2024-08
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum, Count
from datetime import datetime, date
from ...models import PaymentTransaction, ServiceCenter


class Command(BaseCommand):
    help = 'Generate payment reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            help='Month in YYYY-MM format (default: current month)',
        )

    def handle(self, *args, **options):
        if options['month']:
            try:
                year, month = map(int, options['month'].split('-'))
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year + 1, 1, 1)
                else:
                    end_date = date(year, month + 1, 1)
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid month format. Use YYYY-MM')
                )
                return
        else:
            today = date.today()
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1)
            else:
                end_date = today.replace(month=today.month + 1, day=1)

        # Generate report
        transactions = PaymentTransaction.objects.filter(
            completed_at__date__gte=start_date,
            completed_at__date__lt=end_date,
            status='completed'
        )
        
        total_revenue = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
        transaction_count = transactions.count()
        
        self.stdout.write(f'\n=== Payment Report for {start_date.strftime("%B %Y")} ===')
        self.stdout.write(f'Total Revenue: ₹{total_revenue:,.2f}')
        self.stdout.write(f'Total Transactions: {transaction_count}')
        
        if transaction_count > 0:
            avg_transaction = total_revenue / transaction_count
            self.stdout.write(f'Average Transaction: ₹{avg_transaction:,.2f}')
        
        # Service center statistics
        active_centers = ServiceCenter.objects.filter(
            subscription_valid_until__gte=start_date,
            is_active=True
        ).count()
        
        total_centers = ServiceCenter.objects.filter(is_active=True).count()
        
        self.stdout.write(f'\nService Centers:')
        self.stdout.write(f'Active Subscriptions: {active_centers}')
        self.stdout.write(f'Total Active Centers: {total_centers}')
        
        self.stdout.write(f'\n=== End of Report ===\n')
