from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ...models import ServiceEntry
from ...sms_service import SMSService   # replace with your actual SMS function/provider


class Command(BaseCommand):
    help = "Send SMS reminders for vehicle service due dates"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        # 2 days before due
        two_days_before = today + timedelta(days=2)
        entries_due_soon = ServiceEntry.objects.filter(next_service_due_date=two_days_before)

        for entry in entries_due_soon:
            customer = entry.customer
            message = (
                f"Dear {customer.name}, your {entry.vehicle.vehicle_number} "
                f"is due for {entry.get_service_type_display()} on {entry.next_service_due_date}. "
                "Please book your service in advance."
            )
            # SMSService(customer.phone, message)   # your SMS API
            # self.stdout.write(self.style.SUCCESS(f"Sent reminder for {entry}"))
            print("sms sent", message)

        # 1 day after due
        yesterday = today - timedelta(days=1)
        overdue_entries = ServiceEntry.objects.filter(next_service_due_date=yesterday)

        # for entry in overdue_entries:
        #     customer = entry.customer
        #     message = (
        #         f"Dear {customer.name}, your {entry.vehicle.vehicle_number} "
        #         f"was due for {entry.get_service_type_display()} on {entry.next_service_due_date}. "
        #         "Please visit the service center as soon as possible."
        #     )
        #     SMSService(customer.phone, message)
        #     self.stdout.write(self.style.WARNING(f"Sent overdue reminder for {entry}"))
