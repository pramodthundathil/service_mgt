from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ...models import ServiceEntry
from ...sms_service import SMSService   # replace with your actual SMS function/provider
import logging

# Assuming you've imported your SMSService
# from your_app.services import SMSService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send SMS reminders for vehicle service due dates"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        # 2 days before due
        two_days_before = today + timedelta(days=2)
        entries_due_soon = ServiceEntry.objects.filter(next_service_due_date=two_days_before)

        for entry in entries_due_soon:
            customer = entry.customer
            customer_phone = customer.phone
            message = (
                f"Dear {customer.name}, your {entry.vehicle.vehicle_number} "
                f"is due for {entry.get_service_type_display()} on {entry.next_service_due_date}. "
                "Please book your service in advance."
            )
            if customer_phone:
                    self.send_service_confirmation_sms(entry, customer_phone)
            else:
                logger.warning(f"No phone number found for customer {entry.customer.name}")
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
    def send_service_confirmation_sms(self, service_entry, phone):
        """Send SMS confirmation for service entry"""
        try:
            sms_service = SMSService(
                access_token="B4E2AL68DJFSENJ",
                access_token_key=";Wva|blE+0BMAuY@RPUX*tqzNhHJCF[-"
            )
            
            # Create a more appropriate message for service confirmation
            message_content = (

                f"Dear Customer, Next wheel alignment for your vehicle {service_entry.vehicle.vehicle_number} is due at {service_entry.next_kilometer} km. Kindly check and align on time. Wheel Alignment Info- Maharaja Hub"
                
            )
            
            # You'll need to update these template IDs for service confirmation
            sms_result = sms_service.send_sms(
                recipients=[phone],
                message_content=message_content,
                sms_header="MHAHUB",
                entity_id="1701175741468435288",
                template_id="1707175825891756292",  # Update this for service confirmation template
            )
            
            logger.info(f"SMS sent successfully for service entry {service_entry.id}: {sms_result}")
            
        except Exception as e:
            logger.error(f"Failed to send SMS for service entry {service_entry.id}: {str(e)}")
            raise
