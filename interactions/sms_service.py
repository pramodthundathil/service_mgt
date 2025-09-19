import hashlib
import time
import requests
from typing import List, Dict, Any

class SMSService:
    def __init__(self, access_token: str, access_token_key: str):
        """
        Initialize SMS service with access token and key
        
        Args:
            access_token (str): Access token from the panel
            access_token_key (str): Access token key from the panel
        """
        self.access_token = access_token
        self.access_token_key = access_token_key
        self.base_url = "https://sms.byteboot.in/api/sms/v1.0"
    
    def create_signature(self, request_for: str = "send-sms") -> tuple:
        """
        Create authentication signature for SMS API
        
        Args:
            request_for (str): Type of request (e.g., 'send-sms', 'send-sms-array')
        
        Returns:
            tuple: (expire_timestamp, signature)
        """
        # Unix timestamp for 1 minute from now
        expire = int(time.time()) + 60
        
        # Create signature using MD5 hashing (following the original algorithm)
        time_key = hashlib.md5(f"{request_for}sms@rits-v1.0{expire}".encode()).hexdigest()
        time_access_token_key = hashlib.md5(f"{self.access_token}{time_key}".encode()).hexdigest()
        signature = hashlib.md5(f"{time_access_token_key}{self.access_token_key}".encode()).hexdigest()
        
        return expire, signature
    
    def send_sms(self, 
                 recipients: List[str],
                 message_content: str,
                 sms_header: str,
                 entity_id: str,
                 template_id: str,
                 route: str = "transactional",
                 content_type: str = "text",
                 remove_duplicate_numbers: str = "1",
                 webhook_id: str = None) -> Dict[str, Any]:
        """
        Send SMS to multiple recipients
        
        Args:
            recipients (List[str]): List of phone numbers
            message_content (str): SMS message content
            sms_header (str): SMS header/sender ID
            entity_id (str): Entity ID from telecom provider
            template_id (str): Template ID from telecom provider
            route (str): SMS route type
            content_type (str): Content type (text/unicode)
            remove_duplicate_numbers (str): Remove duplicate numbers flag
            webhook_id (str): Webhook ID for delivery reports
        
        Returns:
            Dict: API response
        """
        # Create signature
        expire, signature = self.create_signature()
        
        # Prepare request parameters
        request_params = {
            'accessToken': self.access_token,
            'expire': str(expire),
            'authSignature': signature,
            'route': route,
            'smsHeader': sms_header,
            'messageContent': message_content,
            'recipients': recipients,
            'contentType': content_type,
            'entityId': entity_id,
            'templateId': template_id,
            'removeDuplicateNumbers': remove_duplicate_numbers
        }
        
        # Add webhook ID if provided
        if webhook_id:
            request_params['webHookId'] = webhook_id
        
        try:
            # Send POST request
            response = requests.post(
                f"{self.base_url}/send-sms",
                headers={'accept': 'application/json'},
                data=request_params,
                timeout=30
            )
            
            # Return JSON response
            return {
                'status_code': response.status_code,
                'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                'success': response.status_code == 200
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'status_code': None,
                'response': f"Request Error: {str(e)}",
                'success': False
            }
        except Exception as e:
            return {
                'status_code': None,
                'response': f"Error: {str(e)}",
                'success': False
            }

# Example usage
# def main():
#     # Initialize SMS service
#     sms_service = SMSService(
#         access_token="WT8X0A685134IC2",
#         access_token_key="=5,BYKFea*[7MUnmbIh&_kfATzdoD;G8"
#     )
    
#     # Example: Send SMS
#     recipients = [
#         "919141109785",
      
#     ]
#     number = 123456
    
#     result = sms_service.send_sms(
#         recipients=recipients,
#         message_content=f'Dear Customer, Your OTP for Neo Tokyo account login is {number} . Please use this OTP within 10 minutes to access your account.',
#         sms_header="NEOTOK",
#         entity_id="1701175222455815989",
#         template_id="1707175430049563666",
       
#     )
    
#     if result['success']:
#         print("SMS sent successfully!")
#         print("Response:", result['response'])
#     else:
#         print("Failed to send SMS:")
#         print("Error:", result['response'])

# if __name__ == "__main__":
#     main()