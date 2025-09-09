# services/sms_service.py - SMS sending service
import requests
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class SMSService:
    """Service class for sending SMS notifications"""
    
    def __init__(self):
        # Configure your SMS provider settings
        self.api_key = getattr(settings, 'SMS_API_KEY', '')
        self.sender_id = getattr(settings, 'SMS_SENDER_ID', 'ServiceCenter')
        self.api_url = getattr(settings, 'SMS_API_URL', '')
    
    def send_service_reminder(self, phone, message, service_entry=None):
        """Send service reminder SMS"""
        try:
            return self.send_sms(phone, message, sms_type='service_reminder')
        except Exception as e:
            logger.error(f"Failed to send service reminder SMS: {str(e)}")
            return False
    
    def send_sms(self, phone, message, sms_type='service_reminder'):
        """Generic SMS sending method"""
        try:
            # Format phone number (remove any non-digits)
            clean_phone = ''.join(filter(str.isdigit, phone))
            
            # Add country code if not present
            if not clean_phone.startswith('91') and len(clean_phone) == 10:
                clean_phone = '91' + clean_phone
            
            # Prepare SMS data
            sms_data = {
                'api_key': self.api_key,
                'sender': self.sender_id,
                'number': clean_phone,
                'message': message,
                'format': 'json'
            }
            
            # Send SMS via your provider's API
            response = requests.post(self.api_url, data=sms_data, timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                # Check provider-specific success response
                if response_data.get('status') == 'success':
                    logger.info(f"SMS sent successfully to {clean_phone}")
                    return True
                else:
                    logger.error(f"SMS failed: {response_data.get('message', 'Unknown error')}")
                    return False
            else:
                logger.error(f"SMS API error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"SMS sending error: {str(e)}")
            return False
    
    def send_bulk_sms(self, sms_list):
        """Send bulk SMS messages"""
        results = []
        for sms_data in sms_list:
            result = self.send_sms(
                phone=sms_data['phone'],
                message=sms_data['message'],
                sms_type=sms_data.get('type', 'service_reminder')
            )
            results.append({
                'phone': sms_data['phone'],
                'success': result
            })
        return results
