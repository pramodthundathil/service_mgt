"""
Django management command to check and disable expired subscriptions
Usage: python manage.py check_expired_subscriptions
Run this as a cron job daily
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from ...models import ServiceCenter


class Command(BaseCommand):
    help = 'Check and disable expired service centers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be disabled without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = date.today()
        now = timezone.now()
        
        # Find expired service centers
        expired_centers = ServiceCenter.objects.filter(
            is_active=True
        ).exclude(
            # Exclude centers with active subscriptions
            subscription_valid_until__gte=today
        ).exclude(
            # Exclude centers with active trials
            trial_ends_at__gte=now,
            subscription_valid_until__isnull=True
        )
        
        if not expired_centers.exists():
            self.stdout.write(
                self.style.SUCCESS('No expired service centers found.')
            )
            return
        
        self.stdout.write(f'Found {expired_centers.count()} expired service centers:')
        
        for center in expired_centers:
            if center.subscription_valid_until:
                expiry_info = f'Subscription expired on {center.subscription_valid_until}'
            else:
                expiry_info = f'Trial expired on {center.trial_ends_at.date()}'
            
            self.stdout.write(f'  - {center.name} ({center.email}): {expiry_info}')
            
            if not dry_run:
                center.is_active = False
                center.save()
                self.stdout.write(
                    self.style.WARNING(f'    Disabled: {center.name}')
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    'DRY RUN: No changes made. Run without --dry-run to disable centers.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Disabled {expired_centers.count()} expired service centers.')
            )
