# serializers.py

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, date
from .models import ServiceCenter, CustomUser, LicenseKey, Subscription
from .utils import generate_license_key  # Assuming you have this utility function


class ServiceCenterRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering a new service center with admin user
    
    This endpoint creates a new service center along with its admin user account.
    The service center will have a 15-day trial period by default.
    """
    
    # Service Center fields
    name = serializers.CharField(
        max_length=255,
        help_text="Name of the service center",
        style={'placeholder': 'ABC Service Center'}
    )
    address = serializers.CharField(
        help_text="Complete address of the service center",
        style={'placeholder': '123 Main Street, City, State, ZIP'}
    )
    email = serializers.EmailField(
        help_text="Official email address of the service center",
        style={'placeholder': 'contact@servicecenter.com'}
    )
    phone = serializers.CharField(
        max_length=17, 
        required=False, 
        allow_blank=True,
        help_text="Phone number in international format",
        style={'placeholder': '+1234567890'}
    )
    
    # Admin User fields
    # admin_first_name = serializers.CharField(
    #     max_length=30, 
    #     write_only=True,
    #     help_text="First name of the admin user",
    #     style={'placeholder': 'John'}
    # )
    # admin_last_name = serializers.CharField(
    #     max_length=30, 
    #     write_only=True,
    #     help_text="Last name of the admin user",
    #     style={'placeholder': 'Doe'}
    # )
    # admin_email = serializers.EmailField(
    #     write_only=True,
    #     help_text="Email address for the admin user account",
    #     style={'placeholder': 'admin@servicecenter.com'}
    # )
    # admin_phone = serializers.CharField(
    #     max_length=17, 
    #     write_only=True,
    #     help_text="Phone number of the admin user",
    #     style={'placeholder': '+1234567890'}
    # )
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        help_text="Password for the admin user (minimum 8 characters)",
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True, 
        min_length=8,
        help_text="Confirm the admin password",
        style={'input_type': 'password'}
    )
    
    # Read-only fields that will be returned
    license_key = serializers.CharField(
        read_only=True,
        help_text="Unique license key for the service center"
    )
    trial_ends_at = serializers.DateTimeField(
        read_only=True,
        help_text="When the trial period ends"
    )
    subscription_status = serializers.CharField(
        read_only=True,
        help_text="Current subscription status"
    )
    admin_user_id = serializers.IntegerField(
        read_only=True,
        help_text="ID of the created admin user"
    )

    class Meta:
        model = ServiceCenter
        fields = [
            # Service Center fields
            'id', 'name', 'address', 'email', 'phone',
            # Admin user fields (write-only)
            # 'admin_first_name', 'admin_last_name', 'admin_email', 
            # 'admin_phone', 
            'password', 'confirm_password',
            # Read-only response fields
            'license_key', 'trial_ends_at', 'subscription_status', 'admin_user_id',
            'created_at', 'is_active'
        ]
        read_only_fields = ['id', 'license_key', 'trial_ends_at', 'created_at', 'is_active']

    def validate(self, attrs):
        """Custom validation"""
        # Check if passwords match
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        
        # Validate password strength
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})
        
        # Check if service center email already exists
        if ServiceCenter.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError("Service center with this email already exists")
        
        # # Check if admin email already exists
        # if CustomUser.objects.filter(email=attrs['admin_email']).exists():
        #     raise serializers.ValidationError("User with this admin email already exists")
        
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create service center, admin user, license key, and subscription"""
        
        # Extract admin user data
        admin_data = {
            # 'first_name': validated_data.pop('admin_first_name'),
            # 'last_name': validated_data.pop('admin_last_name'),
            'email': validated_data['email'],
            'phone_number': validated_data['phone'],
            'password': validated_data.pop('password'),
        }
        validated_data.pop('confirm_password')  # Remove confirm password
        
        # Create Service Center
        service_center = ServiceCenter.objects.create(**validated_data)
        
        # Create Admin User
        admin_user = CustomUser.objects.create_user(
            email=admin_data['email'],
            password=admin_data['password'],
            phone_number=admin_data['phone_number'],
            role='centeradmin',
            service_center=service_center
        )
        
        # Create License Key (if using separate LicenseKey model)
        license_key = LicenseKey.objects.create(
            assigned_to=service_center,
            is_used=True
        )
        
        # Create Trial Subscription
        trial_subscription = Subscription.objects.create(
            service_center=service_center,
            status='trial',
            started_at=timezone.now(),
            expires_at=service_center.trial_ends_at,
            amount=0.00,
            currency='INR'
        )
        
        # Add additional data to the instance for serialization
        service_center.subscription_status = trial_subscription.status
        service_center.admin_user_id = admin_user.id
        
        return service_center


class ServiceCenterDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for service center with related information
    
    Provides comprehensive information about a service center including
    subscription details, user information, and access status.
    """
    
    current_subscription = serializers.SerializerMethodField(
        help_text="Current active subscription details"
    )
    admin_users = serializers.SerializerMethodField(
        help_text="List of admin users for this service center"
    )
    total_users = serializers.SerializerMethodField(
        help_text="Total number of users in this service center"
    )
    can_access_service = serializers.ReadOnlyField(
        help_text="Whether the service center can access the application"
    )
    is_trial_active = serializers.ReadOnlyField(
        help_text="Whether the trial period is currently active"
    )
    is_subscription_active = serializers.ReadOnlyField(
        help_text="Whether the paid subscription is currently active"
    )

    class Meta:
        model = ServiceCenter
        fields = [
            'id', 'name', 'address', 'email', 'phone', 'license_key',
            'is_active', 'trial_started_at', 'trial_ends_at',
            'subscription_started_at', 'subscription_valid_until',
            'razorpay_customer_id', 'razorpay_subscription_id',
            'current_subscription', 'admin_users', 'total_users',
            'can_access_service', 'is_trial_active', 'is_subscription_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['license_key', 'created_at', 'updated_at']

    def get_current_subscription(self, obj):
        """Get current active subscription"""
        current_sub = obj.subscriptions.filter(
            status__in=['trial', 'active']
        ).first()
        if current_sub:
            return {
                'id': current_sub.id,
                'status': current_sub.status,
                'started_at': current_sub.started_at,
                'expires_at': current_sub.expires_at,
                'amount': current_sub.amount
            }
        return None

    def get_admin_users(self, obj):
        """Get admin users for this service center"""
        admins = obj.users.filter(role='centeradmin')
        return [{
            'id': user.id,
            'email': user.email,
            'is_active': user.is_active
        } for user in admins]

    def get_total_users(self, obj):
        """Get total user count"""
        return obj.users.count()


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for subscription management
    
    Handles subscription data including payment information and status tracking.
    """
    
    service_center_name = serializers.CharField(
        source='service_center.name', 
        read_only=True,
        help_text="Name of the associated service center"
    )

    class Meta:
        model = Subscription
        fields = [
            'id', 'service_center', 'service_center_name', 'status',
            'started_at', 'expires_at', 'razorpay_payment_id',
            'razorpay_order_id', 'razorpay_signature', 'amount',
            'currency', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'status': {
                'help_text': 'Current status of the subscription (trial, active, expired, cancelled)'
            },
            'started_at': {
                'help_text': 'When the subscription started'
            },
            'expires_at': {
                'help_text': 'When the subscription expires'
            },
            'amount': {
                'help_text': 'Subscription amount paid'
            },
            'currency': {
                'help_text': 'Currency code (e.g., INR, USD)'
            }
        }


class ServiceCenterUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating service center information
    
    Allows updating basic service center details while maintaining data integrity.
    """
    
    class Meta:
        model = ServiceCenter
        fields = [
            'name', 'address', 'email', 'phone', 'is_active'
        ]
        extra_kwargs = {
            'name': {
                'help_text': 'Updated name of the service center'
            },
            'address': {
                'help_text': 'Updated address of the service center'
            },
            'email': {
                'help_text': 'Updated email address (must be unique)'
            },
            'phone': {
                'help_text': 'Updated phone number'
            },
            'is_active': {
                'help_text': 'Whether the service center is active'
            }
        }

    def validate_email(self, value):
        """Ensure email uniqueness during update"""
        if self.instance and self.instance.email != value:
            if ServiceCenter.objects.filter(email=value).exists():
                raise serializers.ValidationError("Service center with this email already exists")
        return value


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for adding new users to a service center
    
    Creates new users with role-based access within a specific service center.
    """
    
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        help_text="Password for the new user (minimum 8 characters)",
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True, 
        min_length=8,
        help_text="Confirm the password",
        style={'input_type': 'password'}
    )
    service_center_id = serializers.IntegerField(
        write_only=True,
        help_text="ID of the service center to assign the user to"
    )

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'phone_number',
            'role', 'service_center_id', 'password', 'confirm_password',
            'is_active', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined', 'role']  # role is now read-only
        extra_kwargs = {
            'email': {
                'help_text': 'Email address for the new user (must be unique)'
            },
            'phone_number': {
                'help_text': 'Phone number in international format'
            },
            'role': {
                'help_text': 'User role (staff)'
            },
            'is_active': {
                'help_text': 'Whether the user account is active'
            }
        }

    def validate(self, attrs):
        """Custom validation for user registration"""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})
        
        # Validate service center exists and user has permission
        try:
            service_center = ServiceCenter.objects.get(id=attrs['service_center_id'])
            if not service_center.can_access_service():
                raise serializers.ValidationError("Service center access is not active")
        except ServiceCenter.DoesNotExist:
            raise serializers.ValidationError("Invalid service center")
        
        return attrs

    def create(self, validated_data):
        """Create new user"""
        service_center_id = validated_data.pop('service_center_id')
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        
        service_center = ServiceCenter.objects.get(id=service_center_id)
        validated_data['role'] = 'staff'

        
        user = CustomUser.objects.create_user(
            password=password,
            service_center=service_center,
            **validated_data
        )
        return user


class LicenseKeySerializer(serializers.ModelSerializer):
    """
    Serializer for license key management
    
    Provides information about license keys and their assignment status.
    """
    
    service_center_name = serializers.CharField(
        source='assigned_to.name', 
        read_only=True,
        help_text="Name of the service center this license is assigned to"
    )

    class Meta:
        model = LicenseKey
        fields = [
            'id', 'key', 'assigned_to', 'service_center_name',
            'valid_until', 'is_used', 'created_at'
        ]
        read_only_fields = ['key', 'valid_until', 'created_at']
        extra_kwargs = {
            'key': {
                'help_text': 'Unique license key string'
            },
            'valid_until': {
                'help_text': 'Date until which the license is valid'
            },
            'is_used': {
                'help_text': 'Whether the license key has been used/activated'
            }
        }


# Additional serializers for Swagger documentation

class ActivateSubscriptionRequestSerializer(serializers.Serializer):
    """
    Serializer for subscription activation request
    """
    duration_months = serializers.IntegerField(
        default=12,
        min_value=1,
        max_value=36,
        help_text="Subscription duration in months (1-36)"
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount"
    )
    razorpay_payment_id = serializers.CharField(
        max_length=100,
        help_text="Razorpay payment ID from successful payment"
    )
    razorpay_order_id = serializers.CharField(
        max_length=100,
        help_text="Razorpay order ID"
    )
    razorpay_signature = serializers.CharField(
        max_length=255,
        help_text="Razorpay signature for payment verification"
    )


class SubscriptionStatusResponseSerializer(serializers.Serializer):
    """
    Serializer for subscription status response
    """
    success = serializers.BooleanField()
    data = serializers.DictField(
        child=serializers.CharField(),
        help_text="Subscription status data"
    )


class DashboardStatsResponseSerializer(serializers.Serializer):
    """
    Serializer for dashboard statistics response
    """
    success = serializers.BooleanField()
    data = serializers.DictField(
        child=serializers.CharField(),
        help_text="Dashboard statistics data"
    )


class ErrorResponseSerializer(serializers.Serializer):
    """
    Standard error response serializer
    """
    success = serializers.BooleanField(default=False)
    message = serializers.CharField(help_text="Error message")
    error = serializers.CharField(
        required=False,
        help_text="Detailed error information"
    )