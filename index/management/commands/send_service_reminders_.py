# management/commands/send_service_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from interactions.models import ServiceEntry, ServiceCenter
from ...services.sms_service import SMSService
import logging
from django.db import models

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send SMS reminders for vehicle services'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually sending SMS',
        )
        parser.add_argument(
            '--service-center-id',
            type=int,
            help='Send reminders for specific service center only',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        service_center_id = options.get('service_center_id')
        
        self.stdout.write("Starting SMS reminder process...")
        
        # Get active service centers
        service_centers = ServiceCenter.objects.filter(is_active=True)
        if service_center_id:
            service_centers = service_centers.filter(id=service_center_id)
        
        total_sent = 0
        
        for service_center in service_centers:
            if not service_center.can_access_service():
                self.stdout.write(f"Skipping {service_center.name} - subscription expired")
                continue
                
            sent_count = self.send_reminders_for_service_center(service_center, dry_run)
            total_sent += sent_count
            
        self.stdout.write(
            self.style.SUCCESS(f'Successfully processed {total_sent} SMS reminders')
        )

    def send_reminders_for_service_center(self, service_center, dry_run=False):
        """Send reminders for a specific service center"""
        today = date.today()
        sent_count = 0
        
        # Get the latest service entry for each vehicle
        latest_services = ServiceEntry.objects.filter(
            service_center=service_center
        ).values('vehicle').annotate(
            latest_service_date=models.Max('service_date')
        )
        
        for service_info in latest_services:
            try:
                # Get the actual service entry
                service_entry = ServiceEntry.objects.filter(
                    vehicle_id=service_info['vehicle'],
                    service_date=service_info['latest_service_date']
                ).first()
                
                if not service_entry or not service_entry.customer.phone:
                    continue
                
                # Determine frequency based on vehicle transport type
                if service_entry.vehicle.transport_type == 'private':
                    frequency_months = service_center.sms_frequency_for_private_vehicles
                else:
                    frequency_months = service_center.sms_frequency_for_transport_vehicles
                
                # Calculate next reminder date
                next_reminder_date = service_entry.service_date + timedelta(
                    days=frequency_months * 30  # Approximate months to days
                )
                
                # Check if it's time to send reminder (within 7 days of due date)
                days_until_reminder = (next_reminder_date - today).days
                
                if -7 <= days_until_reminder <= 7:  # Send reminder within 7 days window
                    # Check if we haven't sent a reminder recently
                    if not self.was_reminder_sent_recently(service_entry, days=7):
                        if self.send_sms_reminder(service_entry, dry_run):
                            sent_count += 1
                            
            except Exception as e:
                logger.error(f"Error processing service entry {service_info['vehicle']}: {str(e)}")
                continue
        
        return sent_count
    
    def was_reminder_sent_recently(self, service_entry, days=7):
        """Check if a reminder was sent recently to avoid spam"""
        from ...models import SMSLog
        recent_date = timezone.now() - timedelta(days=days)
        
        return SMSLog.objects.filter(
            customer=service_entry.customer,
            vehicle=service_entry.vehicle,
            sms_type='service_reminder',
            sent_at__gte=recent_date,
            status='sent'
        ).exists()
    
    def send_sms_reminder(self, service_entry, dry_run=False):
        """Send SMS reminder for a specific service entry"""
        try:
            message = self.generate_sms_message(service_entry)
            
            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would send SMS to {service_entry.customer.phone}: {message}"
                )
                return True
            
            # Send actual SMS
            sms_service = SMSService()
            success = sms_service.send_service_reminder(
                phone=service_entry.customer.phone,
                message=message,
                service_entry=service_entry
            )
            
            if success:
                self.stdout.write(
                    f"SMS sent to {service_entry.customer.name} - {service_entry.customer.phone}"
                )
                # Log the SMS
                self.log_sms(service_entry, message, 'sent')
            else:
                self.log_sms(service_entry, message, 'failed')
                
            return success
            
        except Exception as e:
            logger.error(f"Error sending SMS to {service_entry.customer.phone}: {str(e)}")
            self.log_sms(service_entry, "", 'failed', str(e))
            return False
    
    def generate_sms_message(self, service_entry):
        """Generate SMS message content"""
        service_center_name = service_entry.service_center.name
        customer_name = service_entry.customer.name
        vehicle_number = service_entry.vehicle.vehicle_number
        last_service_date = service_entry.service_date.strftime('%d/%m/%Y')
        
        # Determine frequency
        if service_entry.vehicle.transport_type == 'private':
            frequency = service_entry.service_center.sms_frequency_for_private_vehicles
        else:
            frequency = service_entry.service_center.sms_frequency_for_transport_vehicles
        
        message = f"""
Dear {customer_name},

Your vehicle {vehicle_number} is due for service. 

Last Service: {last_service_date}
Service Frequency: Every {frequency} months

Please visit {service_center_name} for your next service.

Contact: {service_entry.service_center.phone}
        """.strip()
        
        return message
    
    def log_sms(self, service_entry, message, status, error_message=None):
        """Log SMS sending attempt"""
        from ...models import SMSLog
        
        SMSLog.objects.create(
            customer=service_entry.customer,
            vehicle=service_entry.vehicle,
            service_center=service_entry.service_center,
            service_entry=service_entry,
            phone_number=service_entry.customer.phone,
            message=message,
            sms_type='service_reminder',
            status=status,
            error_message=error_message,
            sent_at=timezone.now()
        )





# views.py - Admin interface for manual SMS sending
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse

@staff_member_required
def send_manual_reminder(request, service_center_id):
    """Manual SMS reminder sending view"""
    service_center = get_object_or_404(ServiceCenter, id=service_center_id)
    
    if request.method == 'POST':
        from django.core.management import call_command
        from io import StringIO
        
        try:
            # Capture command output
            out = StringIO()
            call_command(
                'send_service_reminders',
                service_center_id=service_center_id,
                stdout=out
            )
            
            messages.success(request, f"SMS reminders sent successfully for {service_center.name}")
            return JsonResponse({'status': 'success', 'output': out.getvalue()})
            
        except Exception as e:
            messages.error(request, f"Error sending reminders: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


# settings.py additions
# Add these to your Django settings



# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'sms_logs.log',
        },
    },
    'loggers': {
        'myapp.management.commands.send_service_reminders': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}