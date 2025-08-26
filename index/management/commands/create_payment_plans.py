"""
Django management command to create default payment plans
Usage: python manage.py create_payment_plans
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from ...models import PaymentPlan


class Command(BaseCommand):
    help = 'Create default payment plans'

    def handle(self, *args, **options):
        with transaction.atomic():
            # Create trial plan
            trial_plan, created = PaymentPlan.objects.get_or_create(
                plan_type='trial',
                duration_months=0,
                defaults={
                    'name': '15 Day Trial',
                    'price': 0.00,
                    'currency': 'INR',
                    'description': '15 days free trial for new service centers',
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created trial plan: {trial_plan.name}')
                )
            else:
                self.stdout.write(f'Trial plan already exists: {trial_plan.name}')

            # Create yearly plan
            yearly_plan, created = PaymentPlan.objects.get_or_create(
                plan_type='yearly',
                duration_months=12,
                defaults={
                    'name': '1 Year Subscription',
                    'price': 1499.00,
                    'currency': 'INR',
                    'description': '1 Year subscription extension for service centers',
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created yearly plan: {yearly_plan.name}')
                )
            else:
                self.stdout.write(f'Yearly plan already exists: {yearly_plan.name}')

            self.stdout.write(
                self.style.SUCCESS('Payment plans setup completed successfully!')
            )
