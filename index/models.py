from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta, date
import uuid
from datetime import timedelta, date



class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


def generate_license_key():
    """Generate a unique 20-character license key"""
    return str(uuid.uuid4()).replace('-', '').upper()[:20]


class ServiceCenter(models.Model):
    """Model representing a service center"""
    name = models.CharField(max_length=255)
    address = models.TextField()
    email = models.EmailField(unique=True)  # Should be unique
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    
    # License and subscription fields
    license_key = models.CharField(max_length=100, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    trial_started_at = models.DateTimeField(auto_now_add=True)
    trial_ends_at = models.DateTimeField(blank=True, null=True)
    subscription_started_at = models.DateTimeField(blank=True, null=True)
    subscription_valid_until = models.DateField(null=True, blank=True)
    
    # Payment tracking
    razorpay_customer_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    sms_frequency_for_private_vehicles = models.IntegerField(default=3, help_text="Sms Frequency for Pvt vehicle Default at 3 months data in months")
    sms_frequency_for_transport_vehicles = models.IntegerField(default=3, help_text="Sms Frequency for Transport vehicle Default at 3 months data in months")

    class Meta:
        verbose_name = "Service Center"
        verbose_name_plural = "Service Centers"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Generate license key if new instance
        if not self.license_key:
            self.license_key = generate_license_key()
        
        # Set trial end date if new instance
        if not self.trial_ends_at:
            self.trial_ends_at = timezone.now() + timedelta(days=15)
        
        super().save(*args, **kwargs)

    def is_trial_active(self):
        """Check if trial period is still active"""
        return timezone.now() < self.trial_ends_at if self.trial_ends_at else False

    def is_subscription_active(self):
        """Check if subscription is active"""
        if not self.subscription_valid_until:
            return False
        return date.today() <= self.subscription_valid_until

    def can_access_service(self):
        """Check if service center can access the application"""
        return self.is_active and (self.is_trial_active() or self.is_subscription_active())

    def __str__(self):
        return self.name
    
    def extend_subscription(self, months=12, payment_transaction=None):
    
        from datetime import date, timedelta
        from dateutil.relativedelta import relativedelta
        
        # Determine the start date for extension
        if self.is_subscription_active():
            # Extend from current subscription end date
            start_date = self.subscription_valid_until
            new_end_date = start_date + relativedelta(months=months)
        elif self.is_trial_active():
            # Extend from trial end date
            start_date = self.trial_ends_at.date()
            new_end_date = start_date + relativedelta(months=months)
        else:
            # Start from today if no active subscription/trial
            start_date = date.today()
            new_end_date = start_date + relativedelta(months=months)
        
        # Update service center subscription
        self.subscription_valid_until = new_end_date
        if not self.subscription_started_at:
            self.subscription_started_at = timezone.now()
        
        self.save()
        SubscriptionHistory.objects.create(
        service_center=self,
        payment_transaction=payment_transaction,
        started_at=timezone.now(),
        expires_at=timezone.datetime.combine(new_end_date, timezone.datetime.min.time()).replace(tzinfo=timezone.get_current_timezone()),
        previous_expires_at=timezone.datetime.combine(start_date, timezone.datetime.min.time()).replace(tzinfo=timezone.get_current_timezone()) if start_date != date.today() else None,
        plan_name="1 Year Extension",
        amount_paid=payment_transaction.amount if payment_transaction else 0,
        is_extension=True
        )
    
        return new_end_date

    def get_subscription_status(self):
        """Get detailed subscription status"""
        status = {
            'can_access': self.can_access_service(),
            'is_trial_active': self.is_trial_active(),
            'is_subscription_active': self.is_subscription_active(),
            'trial_ends_at': self.trial_ends_at,
            'subscription_ends_at': self.subscription_valid_until,
            'days_remaining': None,
            'status_text': 'Inactive'
        }
        
        if self.is_subscription_active():
            days_remaining = (self.subscription_valid_until - date.today()).days
            status['days_remaining'] = days_remaining
            status['status_text'] = f'Active ({days_remaining} days remaining)'
        elif self.is_trial_active():
            days_remaining = (self.trial_ends_at.date() - date.today()).days
            status['days_remaining'] = days_remaining
            status['status_text'] = f'Trial ({days_remaining} days remaining)'
        elif not self.is_active:
            status['status_text'] = 'Account Disabled'
        else:
            status['status_text'] = 'Subscription Expired'
        
        return status


class LicenseKey(models.Model):
    """Model for managing license keys (if you need separate license management)"""
    key = models.CharField(max_length=100, unique=True, editable=False)
    assigned_to = models.OneToOneField(
        'ServiceCenter', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_license'
    )
    valid_until = models.DateField(blank=True, null=True, editable=False)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if is_new:
            self.key = generate_license_key()
            self.valid_until = timezone.now().date() + timedelta(days=15)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.key


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom user model with role-based access"""
    USER_ROLES = (
        ('admin', 'Super Admin'),
        ('centeradmin', 'Service Center Admin'),
        ('staff', 'Staff'),
    )

    username = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(unique=True, verbose_name='Email Address')
    
    #
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.IntegerField(validators=[phone_regex], max_length=17)
    
    # Role and service center
    role = models.CharField(max_length=20, choices=USER_ROLES)
    service_center = models.ForeignKey(
        'ServiceCenter', 
        on_delete=models.CASCADE,  # Changed from SET_NULL to CASCADE
        null=True, 
        blank=True,
        related_name='users'
    )
    
    # Status fields
    is_active = models.BooleanField(default=True, verbose_name='Active')
    is_staff = models.BooleanField(default=False, verbose_name='Staff Status')
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [ 'phone_number']
    
    objects = CustomUserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Super admin shouldn't have service center
        if self.role == 'admin' and self.service_center:
            from django.core.exceptions import ValidationError
            raise ValidationError("Super admin cannot be assigned to a service center")
        
        # Center admin and staff must have service center
        if self.role in ['centeradmin', 'staff'] and not self.service_center:
            from django.core.exceptions import ValidationError
            raise ValidationError("Center admin and staff must be assigned to a service center")

    def save(self, *args, **kwargs):
        # Auto-generate username if not provided
        if not self.username:
            self.username = self.email.split('@')[0]
        
        # Set is_staff for admin and centeradmin
        if self.role in ['admin', 'centeradmin']:
            self.is_staff = True
        
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)

    def get_full_name(self):
        """Return the username plus the last_name, with a space in between."""
        full_name = f'{self.username}'

    def get_short_name(self):
        """Return the short name for the user."""
        return self.username

    def can_manage_service_center(self, service_center=None):
        """Check if user can manage a specific service center"""
        if self.role == 'admin':
            return True
        if self.role == 'centeradmin':
            return self.service_center == service_center if service_center else True
        return False

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"


# Optional: Subscription tracking model
class Subscription(models.Model):
    """Model to track subscription history and payments"""
    SUBSCRIPTION_STATUS = (
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    )
    
    service_center = models.ForeignKey(ServiceCenter, on_delete=models.CASCADE, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default='trial')
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    
    # Razorpay fields
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='INR')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.service_center.name} - {self.get_status_display()}"
    





# models.py - Add these models to your existing models.py file




class PaymentPlan(models.Model):
    """Model to define subscription plans"""
    PLAN_TYPES = (
        ('trial', 'Trial'),
        ('yearly', 'Yearly'),
    )
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    duration_months = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment Plan"
        verbose_name_plural = "Payment Plans"
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - ₹{self.price}"


class PaymentTransaction(models.Model):
    """Model to track all payment transactions"""
    TRANSACTION_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    )
    
    TRANSACTION_TYPE = (
        ('subscription', 'Subscription Payment'),
        ('renewal', 'Renewal Payment'),
        ('extension', 'Extension Payment'),
    )

    transaction_id = models.CharField(max_length=100, unique=True, editable=False)
    service_center = models.ForeignKey(
        'ServiceCenter', 
        on_delete=models.CASCADE, 
        related_name='payment_transactions'
    )
    payment_plan = models.ForeignKey(
        PaymentPlan, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='transactions'
    )
    
    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    
    # Additional tracking
    initiated_by = models.ForeignKey(
        'CustomUser', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='initiated_transactions'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Failure tracking
    failure_reason = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_id} - {self.service_center.name} - ₹{self.amount}"


class SubscriptionHistory(models.Model):
    """Model to track subscription history and changes"""
    service_center = models.ForeignKey(
        'ServiceCenter', 
        on_delete=models.CASCADE, 
        related_name='subscription_history'
    )
    payment_transaction = models.ForeignKey(
        PaymentTransaction, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='subscription_changes'
    )
    
    # Subscription period
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    previous_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Details
    plan_name = models.CharField(max_length=100)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_trial = models.BooleanField(default=False)
    is_extension = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Subscription History"
        verbose_name_plural = "Subscription History"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.service_center.name} - {self.plan_name} ({self.started_at.date()} to {self.expires_at.date()})"


# Update your existing ServiceCenter model with these additional methods:
# Add this method to your ServiceCenter model



# Add these methods to your ServiceCenter model by copying them into the class




# models.py - Add this model to track SMS logs


from interactions.models import VehicleOnService,ServiceEntry, Customer

class SMSLog(models.Model):
    SMS_TYPE_CHOICES = [
        ('service_reminder', 'Service Reminder'),
        ('payment_reminder', 'Payment Reminder'),
        ('promotional', 'Promotional'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sms_logs')
    vehicle = models.ForeignKey(VehicleOnService, on_delete=models.CASCADE, related_name='sms_logs', null=True, blank=True)
    service_center = models.ForeignKey(ServiceCenter, on_delete=models.CASCADE, related_name='sms_logs')
    service_entry = models.ForeignKey(ServiceEntry, on_delete=models.CASCADE, related_name='sms_logs', null=True, blank=True)
    
    phone_number = models.CharField(max_length=15)
    message = models.TextField()
    sms_type = models.CharField(max_length=20, choices=SMS_TYPE_CHOICES, default='service_reminder')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'SMS Log'
        verbose_name_plural = 'SMS Logs'
    
    def __str__(self):
        return f"{self.sms_type} to {self.customer.name} - {self.status}"
    



class PasswordResetOTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        # OTP valid for 10 minutes
        return timezone.now() <= self.created_at + timedelta(minutes=10)



