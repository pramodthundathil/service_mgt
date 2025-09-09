from celery import shared_task
from django.core.management import call_command

@shared_task
def send_daily_service_reminders():
    """Celery task to send daily service reminders"""
    call_command('send_service_reminders')

@shared_task
def send_service_center_reminders(service_center_id):
    """Send reminders for specific service center"""
    call_command('send_service_reminders', service_center_id=service_center_id)

