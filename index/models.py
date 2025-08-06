from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta, date
import uuid


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
    phone_number = models.CharField(validators=[phone_regex], max_length=17)
    
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