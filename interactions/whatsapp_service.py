import requests

class WhatsAppService:
    BASE_URL = "https://api.telinfy.net/gaca/whatsapp/templates/message/"

    def __init__(self, api_key):
        self.api_key = api_key
        print("WhatsAppService initialized with API key.", self.api_key)
    
    def send_template_message(self, to, template_name, body_params, language="en"):
        print("Sending WhatsApp message...", to, template_name, body_params, language)
        payload = {
            "to": to,
            "templateName": template_name,
            "language": language,
            "header": None,
            "body": {
                "parameters": body_params
            },
            "button": None
        }

        headers = {
            "Api-Key": "f4286546-aa2e-4f3a-8266-d5bf2da00521",  # Use self.api_key instead of hardcoded value
            "Content-Type": "application/json"
        }

        response = requests.post(self.BASE_URL, json=payload, headers=headers)
        print("WhatsApp API payload:", payload)
        print(response.text,"WhatsApp API response status:")
        return response.json()