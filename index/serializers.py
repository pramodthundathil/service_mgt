# serializers.py

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, date
from .models import ServiceCenter, CustomUser, LicenseKey, Subscription
from .utils import generate_license_key  # Assuming you have this utility function
from django.db import models



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
    all_users = serializers.SerializerMethodField(
        help_text="List of all users in this service center"
    )
    total_users_count = serializers.SerializerMethodField(
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
            'current_subscription', 'admin_users', 'all_users', 'total_users_count',
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
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'role': user.role,
            'is_active': user.is_active,
            'date_joined': user.date_joined,
            'last_login': user.last_login
        } for user in admins]

    def get_all_users(self, obj):
        """Get all users for this service center"""
        users = obj.users.all()
        return [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'role': user.role,
            'role_display': user.get_role_display(),
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined,
            'last_login': user.last_login
        } for user in users]

    def get_total_users_count(self, obj):
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

# serializers.py - Add these to your existing serializers

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import ServiceCenter

User = get_user_model()

class AutoServiceCenterUserRegistrationSerializer(serializers.ModelSerializer):
    """
    Modified registration serializer that automatically assigns service center
    Based on the logged-in user's service center - No need for service_center_id input
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
    service_center_name = serializers.CharField(source='service_center.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'username',
            'password', 'confirm_password', 'is_active', 
            'date_joined', 'service_center', 'service_center_name',
            'role', 'role_display'
        ]
        read_only_fields = [
            'id', 'date_joined', 'service_center', 'service_center_name',
            'role', 'role_display'
        ]
        extra_kwargs = {
            'email': {
                'help_text': 'Email address for the new user (must be unique)'
            },
            'phone_number': {
                'help_text': 'Phone number in international format'
            },
            'username': {
                'help_text': 'Username for the new staff member',
                'required': False
            },
            'is_active': {
                'help_text': 'Whether the user account is active',
                'default': True
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
        
        # Check if the requesting user's service center is valid
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")
        
        request_user = request.user
        
        # Validate based on user role
        if request_user.role == 'centeradmin':
            if not request_user.service_center:
                raise serializers.ValidationError("You are not assigned to any service center")
            
            if not request_user.service_center.can_access_service():
                raise serializers.ValidationError("Your service center access is not active")
        
        elif request_user.role == 'staff':
            raise serializers.ValidationError("Staff members cannot create new users")
        
        return attrs

    def validate_email(self, value):
        """Validate email uniqueness"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value

    def validate_phone_number(self, value):
        """Validate phone number format and uniqueness"""
        # Check if phone number already exists
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("User with this phone number already exists")
        return value

    def create(self, validated_data):
        """Create new user and automatically assign service center"""
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        request = self.context.get('request')
        request_user = request.user if request else None
        
        if not request_user:
            raise serializers.ValidationError("Authentication required")
        
        # Automatically assign service center based on requester
        if request_user.role == 'admin':
            # Admin can create users but service center should be specified separately
            # For this serializer, we don't assign service center for admin
            service_center = None
        else:
            # Center admin - automatically assign their service center
            service_center = request_user.service_center
        
        # Auto-generate username if not provided
        if not validated_data.get('username'):
            email = validated_data['email']
            username = email.split('@')[0]
            
            # Ensure unique username
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
            validated_data['username'] = username
        
        # Validate username uniqueness if provided
        elif User.objects.filter(username=validated_data['username']).exists():
            raise serializers.ValidationError({
                'username': 'User with this username already exists'
            })
        
        # Create the user with staff role
        try:
            user = User.objects.create_user(
                password=password,
                service_center=service_center,
                role='staff',  # Always create staff users
                **validated_data
            )
            return user
        except Exception as e:
            raise serializers.ValidationError(f"Failed to create user: {str(e)}")

class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password"""
    old_password = serializers.CharField(
        required=False, 
        write_only=True,
        help_text="Current password (required when changing own password)"
    )
    new_password = serializers.CharField(
        write_only=True, 
        min_length=8,
        help_text="New password (minimum 8 characters)"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Confirm new password"
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def validate_new_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
    
    def validate_old_password(self, value):
        request = self.context.get('request')
        target_user = self.context.get('target_user')
        
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")
        
        user = request.user
        
        # If changing own password, old password is required and must be correct
        if user == target_user:
            if not value:
                raise serializers.ValidationError("Old password is required when changing your own password")
            if not user.check_password(value):
                raise serializers.ValidationError("Old password is incorrect")
        return value

class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users with minimal information"""
    service_center_name = serializers.CharField(source='service_center.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone_number', 'role', 'role_display',
            'service_center', 'service_center_name', 'is_active', 
            'date_joined', 'last_login', 'full_name'
        ]
        read_only_fields = [
            'id', 'date_joined', 'last_login', 'service_center_name', 
            'role_display', 'full_name'
        ]

class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for user profile with more information"""
    service_center_name = serializers.CharField(source='service_center.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    service_center_details = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone_number', 'role', 'role_display',
            'service_center', 'service_center_name', 'service_center_details',
            'is_active', 'is_staff', 'date_joined', 'last_login', 'full_name'
        ]
        read_only_fields = [
            'id', 'date_joined', 'last_login', 'service_center_name', 
            'role_display', 'full_name', 'service_center_details', 'is_staff'
        ]
    
    def get_service_center_details(self, obj):
        """Get detailed service center information"""
        if obj.service_center:
            return {
                'id': obj.service_center.id,
                'name': obj.service_center.name,
                'email': obj.service_center.email,
                'phone': obj.service_center.phone,
                'address': obj.service_center.address,
                'is_active': obj.service_center.is_active,
                'subscription_status': obj.service_center.get_subscription_status()
            }
        return None

class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information (limited fields)"""
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'phone_number', 'is_active'
        ]
    
    def validate_email(self, value):
        """Validate email uniqueness (excluding current user)"""
        if self.instance and self.instance.email != value:
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("User with this email already exists")
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number uniqueness (excluding current user)"""
        if self.instance and self.instance.phone_number != value:
            if User.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError("User with this phone number already exists")
        return value
    
    def validate_username(self, value):
        """Validate username uniqueness (excluding current user)"""
        if self.instance and self.instance.username != value:
            if User.objects.filter(username=value).exists():
                raise serializers.ValidationError("User with this username already exists")
        return value

# Bulk operations serializer (optional)
class BulkUserCreateSerializer(serializers.Serializer):
    """Serializer for bulk user creation"""
    users = serializers.ListField(
        child=AutoServiceCenterUserRegistrationSerializer(),
        min_length=1,
        max_length=50,  # Limit bulk operations
        help_text="List of users to create (max 50 at once)"
    )
    
    def create(self, validated_data):
        """Create multiple users at once"""
        users_data = validated_data['users']
        created_users = []
        errors = []
        
        for i, user_data in enumerate(users_data):
            try:
                serializer = AutoServiceCenterUserRegistrationSerializer(
                    data=user_data,
                    context=self.context
                )
                if serializer.is_valid():
                    user = serializer.save()
                    created_users.append(user)
                else:
                    errors.append({
                        'index': i,
                        'email': user_data.get('email'),
                        'errors': serializer.errors
                    })
            except Exception as e:
                errors.append({
                    'index': i,
                    'email': user_data.get('email'),
                    'errors': str(e)
                })
        
        return {
            'created_users': created_users,
            'errors': errors,
            'success_count': len(created_users),
            'error_count': len(errors)
        }

# Usage example for the serializers
"""
# In your views.py, update the get_serializer_class method:

def get_serializer_class(self):
    if self.action == 'create':
        return AutoServiceCenterUserRegistrationSerializer
    elif self.action == 'change_password':
        return ChangePasswordSerializer
    elif self.action in ['update', 'partial_update']:
        return UserUpdateSerializer
    elif self.action == 'retrieve':
        return UserDetailSerializer
    elif self.action == 'list':
        return UserListSerializer
    return UserListSerializer

# For bulk operations, you can add this action to your viewset:
@action(detail=False, methods=['post'])
def bulk_create(self, request):
    serializer = BulkUserCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        result = serializer.save()
        return Response({
            'message': f'Bulk creation completed. {result["success_count"]} users created, {result["error_count"]} errors.',
            'created_users': UserListSerializer(result['created_users'], many=True).data,
            'errors': result['errors']
        }, status=status.HTTP_201_CREATED if result['created_users'] else status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
"""


# serializers.py
from rest_framework import serializers
from .models import ServiceCenter

class SMSFrequencyUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating SMS frequency settings of a service center
    """
    
    class Meta:
        model = ServiceCenter
        fields = [
            'sms_frequency_for_private_vehicles',
            'sms_frequency_for_transport_vehicles'
        ]
    
    def validate_sms_frequency_for_private_vehicles(self, value):
        """Validate private vehicle SMS frequency"""
        if value < 1 or value > 12:
            raise serializers.ValidationError(
                "SMS frequency for private vehicles must be between 1 and 12 months"
            )
        return value
    
    def validate_sms_frequency_for_transport_vehicles(self, value):
        """Validate transport vehicle SMS frequency"""
        if value < 1 or value > 12:
            raise serializers.ValidationError(
                "SMS frequency for transport vehicles must be between 1 and 12 months"
            )
        return value










# payment_serializers.py - Add these to your existing serializers.py file

from rest_framework import serializers
from django.utils import timezone
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from .models import PaymentPlan, PaymentTransaction, SubscriptionHistory, ServiceCenter
import razorpay
from django.conf import settings


class PaymentPlanSerializer(serializers.ModelSerializer):
    """Serializer for payment plans"""
    
    class Meta:
        model = PaymentPlan
        fields = [
            'id', 'name', 'plan_type', 'duration_months', 'price', 
            'currency', 'is_active', 'description', 'created_at'
        ]
        read_only_fields = ['created_at']


class CreatePaymentOrderSerializer(serializers.Serializer):
    """Serializer for creating Razorpay order"""
    
    amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Amount to be paid (₹1499 for 1 year extension)"
    )
    currency = serializers.CharField(
        default='INR',
        help_text="Payment currency (INR)"
    )
    
    def validate_amount(self, value):
        """Validate payment amount"""
        if value != 1499.00:
            raise serializers.ValidationError("Invalid amount. 1 year extension costs ₹1499")
        return value
    
    def validate(self, attrs):
        """Validate user's service center access"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("User must be authenticated")
        
        user = request.user
        if user.role not in ['centeradmin', 'admin']:
            raise serializers.ValidationError("Only center admin can initiate payments")
        
        if user.role == 'centeradmin' and not user.service_center:
            raise serializers.ValidationError("User must be associated with a service center")
        
        return attrs


class PaymentVerificationSerializer(serializers.Serializer):
    """Serializer for Razorpay payment verification"""
    
    razorpay_payment_id = serializers.CharField(
        max_length=100,
        help_text="Razorpay payment ID received after successful payment"
    )
    razorpay_order_id = serializers.CharField(
        max_length=100,
        help_text="Razorpay order ID"
    )
    razorpay_signature = serializers.CharField(
        max_length=255,
        help_text="Razorpay signature for payment verification"
    )
    
    def validate(self, attrs):
        """Verify Razorpay payment signature"""
        try:
            # Initialize Razorpay client
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            
            # Verify payment signature
            params = {
                'razorpay_payment_id': attrs['razorpay_payment_id'],
                'razorpay_order_id': attrs['razorpay_order_id'],
                'razorpay_signature': attrs['razorpay_signature']
            }
            
            client.utility.verify_payment_signature(params)
            
        except Exception as e:
            raise serializers.ValidationError(f"Payment verification failed: {str(e)}")
        
        return attrs


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for payment transactions"""
    
    service_center_name = serializers.CharField(
        source='service_center.name',
        read_only=True
    )
    payment_plan_name = serializers.CharField(
        source='payment_plan.name',
        read_only=True
    )
    initiated_by_email = serializers.EmailField(
        source='initiated_by.email',
        read_only=True
    )
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'transaction_id', 'service_center', 'service_center_name',
            'payment_plan', 'payment_plan_name', 'transaction_type', 'status',
            'amount', 'currency', 'razorpay_order_id', 'razorpay_payment_id',
            'razorpay_signature', 'initiated_by_email', 'created_at',
            'updated_at', 'completed_at', 'failure_reason'
        ]
        read_only_fields = [
            'transaction_id', 'service_center_name', 'payment_plan_name',
            'initiated_by_email', 'created_at', 'updated_at', 'completed_at'
        ]


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    """Serializer for subscription history"""
    
    service_center_name = serializers.CharField(
        source='service_center.name',
        read_only=True
    )
    transaction_id = serializers.CharField(
        source='payment_transaction.transaction_id',
        read_only=True
    )
    
    class Meta:
        model = SubscriptionHistory
        fields = [
            'id', 'service_center_name', 'transaction_id', 'started_at',
            'expires_at', 'previous_expires_at', 'plan_name', 'amount_paid',
            'is_trial', 'is_extension', 'created_at'
        ]
        read_only_fields = ['created_at']


class SubscriptionStatusSerializer(serializers.Serializer):
    """Serializer for subscription status response"""
    
    can_access = serializers.BooleanField(
        help_text="Whether the service center can access the application"
    )
    is_trial_active = serializers.BooleanField(
        help_text="Whether trial period is active"
    )
    is_subscription_active = serializers.BooleanField(
        help_text="Whether paid subscription is active"
    )
    trial_ends_at = serializers.DateTimeField(
        help_text="When trial period ends"
    )
    subscription_ends_at = serializers.DateField(
        help_text="When subscription ends"
    )
    days_remaining = serializers.IntegerField(
        help_text="Days remaining in current subscription/trial"
    )
    status_text = serializers.CharField(
        help_text="Human readable status text"
    )
    requires_payment = serializers.BooleanField(
        help_text="Whether payment is required to continue service"
    )


class ExtendSubscriptionResponseSerializer(serializers.Serializer):
    """Serializer for subscription extension response"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.DictField(
        child=serializers.CharField(),
        help_text="Extended subscription details"
    )
    subscription_status = SubscriptionStatusSerializer()


class PaymentOrderResponseSerializer(serializers.Serializer):
    """Serializer for payment order creation response"""
    
    success = serializers.BooleanField()
    data = serializers.DictField(
        child=serializers.CharField(),
        help_text="Razorpay order details"
    )
    order_id = serializers.CharField(
        help_text="Razorpay order ID"
    )
    amount = serializers.IntegerField(
        help_text="Amount in smallest currency unit (paise)"
    )
    currency = serializers.CharField(
        help_text="Currency code"
    )
    key_id = serializers.CharField(
        help_text="Razorpay key ID for frontend integration"
    )


class PaymentDashboardSerializer(serializers.Serializer):
    """Serializer for payment dashboard statistics"""
    
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_transactions = serializers.IntegerField()
    successful_transactions = serializers.IntegerField()
    failed_transactions = serializers.IntegerField()
    active_subscriptions = serializers.IntegerField()
    trial_centers = serializers.IntegerField()
    expired_centers = serializers.IntegerField()
    recent_transactions = PaymentTransactionSerializer(many=True)


class ServiceCenterPaymentStatusSerializer(serializers.ModelSerializer):
    """Enhanced service center serializer with payment status"""
    
    subscription_status = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceCenter
        fields = [
            'id', 'name', 'email', 'license_key', 'is_active',
            'trial_ends_at', 'subscription_valid_until',
            'subscription_status', 'recent_transactions', 'total_paid'
        ]
    
    def get_subscription_status(self, obj):
        """Get subscription status"""
        return obj.get_subscription_status()
    
    def get_recent_transactions(self, obj):
        """Get recent payment transactions"""
        transactions = obj.payment_transactions.filter(
            status='completed'
        ).order_by('-completed_at')[:3]
        return PaymentTransactionSerializer(transactions, many=True).data
    
    def get_total_paid(self, obj):
        """Get total amount paid by service center"""
        return obj.payment_transactions.filter(
            status='completed'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or 0