from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ...models import ServiceEntry
from ...sms_service import SMSService
from whatsapp_service import WhatsAppService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send SMS reminders for vehicle service due dates"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        # Pre-create service objects (optimization)
        whatsapp = WhatsAppService(api_key="f4286546-aa2e-4f3a-8266-d5bf2da00521")

        # -------------------------------
        # 1️⃣  Two days before due date
        # -------------------------------
        two_days_before = today + timedelta(days=2)
        entries_due_soon = ServiceEntry.objects.filter(next_service_due_date=two_days_before)

        for entry in entries_due_soon:
            customer = entry.customer
            customer_phone = customer.phone

            if not customer_phone:
                logger.warning(f"No phone number found for customer {customer.name}")
                continue

            # SMS Reminder
            self.send_service_confirmation_sms(entry, customer_phone)

            # WhatsApp Template Message
            try:
                body_params = [
                    {"type": "text", "text": str(entry.vehicle.vehicle_number)},
                    {"type": "text", "text": str(entry.next_service_due_date)},
                ]

                wa_result = whatsapp.send_template_message(
                    to=f"+91{customer_phone}",
                    template_name="reminder",
                    body_params=body_params
                )

                logger.info(f"WhatsApp reminder sent for entry {entry.id}: {wa_result}")
            except Exception as e:
                logger.error(f"WhatsApp failed for entry {entry.id}: {str(e)}")

        # -------------------------------
        # 2️⃣  One day after due date (future extension)
        # -------------------------------
        # yesterday = today - timedelta(days=1)
        # overdue_entries = ServiceEntry.objects.filter(next_service_due_date=yesterday)
        # (Your overdue logic was commented so kept same)


    def send_service_confirmation_sms(self, service_entry, phone):
        """Send SMS confirmation for service entry"""
        try:
            sms_service = SMSService(
                access_token="B4E2AL68DJFSENJ",
                access_token_key=";Wva|blE+0BMAuY@RPUX*tqzNhHJCF[-"
            )

            message_content = (
                f"Dear Customer, Next wheel alignment for your vehicle "
                f"{service_entry.vehicle.vehicle_number} is due at {service_entry.next_kilometer} km. "
                f"Kindly check and align on time. Wheel Alignment Info- Maharaja Hub"
            )

            sms_result = sms_service.send_sms(
                recipients=[phone],
                message_content=message_content,
                sms_header="MHAHUB",
                entity_id="1701175741468435288",
                template_id="1707175825891756292",
            )

            logger.info(f"SMS sent successfully for service entry {service_entry.id}: {sms_result}")

        except Exception as e:
            logger.error(f"Failed to send SMS for entry {service_entry.id}: {str(e)}")
            raise
