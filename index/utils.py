# utils.py

import random
import string
from django.utils.crypto import get_random_string


def generate_license_key(length=20):
    """
    Generate a unique license key
    Format: XXXX-XXXX-XXXX-XXXX-XXXX (20 characters with dashes)
    """
    # Generate random alphanumeric string
    chars = string.ascii_uppercase + string.digits
    key_parts = []
    
    # Create 4-character segments
    for _ in range(5):
        segment = ''.join(random.choices(chars, k=4))
        key_parts.append(segment)
    
    return '-'.join(key_parts)


def generate_unique_license_key():
    """
    Generate a unique license key that doesn't already exist in database
    """
    from .models import LicenseKey, ServiceCenter
    
    max_attempts = 100
    for _ in range(max_attempts):
        key = generate_license_key()
        
        # Check if key exists in either model
        if not (LicenseKey.objects.filter(key=key).exists() or 
                ServiceCenter.objects.filter(license_key=key).exists()):
            return key
    
    # Fallback to crypto-based generation if random generation fails
    return get_random_string(20).upper()


def calculate_subscription_end_date(start_date, duration_months):
    """
    Calculate subscription end date based on duration in months
    """
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta
    
    try:
        # Use relativedelta for accurate month calculation
        return start_date + relativedelta(months=duration_months)
    except ImportError:
        # Fallback to approximation if dateutil is not available
        return start_date + timedelta(days=duration_months * 30)


def format_phone_number(phone):
    """
    Format phone number to standard format
    """
    # Remove all non-numeric characters
    phone_digits = ''.join(filter(str.isdigit, phone))
    
    # Add country code if missing
    if len(phone_digits) == 10:
        phone_digits = '91' + phone_digits  # India country code
    elif len(phone_digits) == 11 and phone_digits.startswith('0'):
        phone_digits = '91' + phone_digits[1:]
    
    return '+' + phone_digits


def validate_license_key_format(license_key):
    """
    Validate license key format
    Returns True if format is valid, False otherwise
    """
    import re
    
    # Expected format: XXXX-XXXX-XXXX-XXXX-XXXX
    pattern = r'^[A-Z0-9]{4}-[A-Z0-9]{4}-'