from django.shortcuts import render, redirect, get_list_or_404
from django.contrib import messages

# auth jwt token and permissions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import IsAdmin, IsCenterAdmin

# Swagger imports
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Create your views here.
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['id'] = user.id  # This should match 'id'
        token['phone_number'] = user.phone_number
        token['role'] = user.role
        
        if user.service_center:
            token['service_center_id'] = user.service_center.id
        
            
        
        return token

    
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# service center registration 

# views.py

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import ServiceCenter, CustomUser, LicenseKey, Subscription
from .serializers import (
    ServiceCenterRegistrationSerializer,
    ServiceCenterDetailSerializer,
    ServiceCenterUpdateSerializer,
    SubscriptionSerializer,
    UserRegistrationSerializer,
    LicenseKeySerializer,
    SMSFrequencyUpdateSerializer,
)


class ServiceCenterRegistrationView(generics.CreateAPIView):
    """
    API endpoint for registering a new service center with admin user
    """
    queryset = ServiceCenter.objects.all()
    serializer_class = ServiceCenterRegistrationSerializer
    permission_classes = [AllowAny]  # Allow public registration

    @swagger_auto_schema(
        operation_description="Register a new service center with admin user",
        operation_summary="Service Center Registration",
        request_body=ServiceCenterRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="Service center registered successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Service center registered successfully",
                        "data": {
                            "service_center": {
                                "id": 1,
                                "name": "ABC Service Center",
                                "email": "abc@service.com",
                                "license_key": "ABCD1234567890123456",
                                "trial_ends_at": "2024-08-16T10:30:00Z"
                            },
                            "trial_days_remaining": 15
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Registration failed",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Registration failed",
                        "error": "Service center with this email already exists"
                    }
                }
            )
        },
        tags=['Service Centers']
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            service_center = serializer.save()
            
            response_data = {
                'success': True,
                'message': 'Service center registered successfully',
                'data': {
                    'service_center': ServiceCenterDetailSerializer(service_center).data,
                    'trial_days_remaining': (service_center.trial_ends_at - timezone.now()).days
                }
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Registration failed',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ServiceCenterListView(generics.ListAPIView):
    """
    API endpoint for listing service centers (role-based access)
    """
    queryset = ServiceCenter.objects.all()
    serializer_class = ServiceCenterDetailSerializer
    permission_classes = [IsAuthenticated, IsCenterAdmin]

    @swagger_auto_schema(
        operation_description="List service centers based on user role",
        operation_summary="List Service Centers",
        responses={
            200: ServiceCenterDetailSerializer(many=True),
            403: openapi.Response(
                description="Permission denied",
                examples={
                    "application/json": {
                        "detail": "You do not have permission to perform this action."
                    }
                }
            )
        },
        tags=['Service Centers']
    )
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return ServiceCenter.objects.all()
        elif user.role == 'centeradmin':
            return ServiceCenter.objects.filter(id=user.service_center.id)
        else:
            return ServiceCenter.objects.none()


class ServiceCenterDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating, and deleting service centers
    """
    queryset = ServiceCenter.objects.all()
    permission_classes = [IsAuthenticated ]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ServiceCenterUpdateSerializer
        return ServiceCenterDetailSerializer

    @swagger_auto_schema(
        operation_description="Retrieve service center details",
        operation_summary="Get Service Center Details",
        responses={
            200: ServiceCenterDetailSerializer,
            404: openapi.Response(description="Service center not found"),
            403: openapi.Response(description="Permission denied")
        },
        tags=['Service Centers']
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update service center information",
        operation_summary="Update Service Center",
        request_body=ServiceCenterUpdateSerializer,
        responses={
            200: ServiceCenterDetailSerializer,
            400: openapi.Response(description="Bad request"),
            403: openapi.Response(description="Permission denied"),
            404: openapi.Response(description="Service center not found")
        },
        tags=['Service Centers']
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update service center information",
        operation_summary="Partial Update Service Center",
        request_body=ServiceCenterUpdateSerializer,
        responses={
            200: ServiceCenterDetailSerializer,
            400: openapi.Response(description="Bad request"),
            403: openapi.Response(description="Permission denied"),
            404: openapi.Response(description="Service center not found")
        },
        tags=['Service Centers']
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete service center",
        operation_summary="Delete Service Center",
        responses={
            204: openapi.Response(description="Service center deleted successfully"),
            403: openapi.Response(description="Permission denied"),
            404: openapi.Response(description="Service center not found")
        },
        tags=['Service Centers']
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_object(self):
        user = self.request.user
        service_center_id = self.kwargs.get('pk')
        
        if user.role == 'admin':
            return get_object_or_404(ServiceCenter, id=service_center_id)
        elif user.role == 'centeradmin':
            return get_object_or_404(ServiceCenter,id=user.service_center.id)
        else:
            # Staff can only view their own service center
            return get_object_or_404(ServiceCenter, id=user.service_center.id)



class SMSFrequencyUpdateView(generics.UpdateAPIView):
    """
    API endpoint for updating SMS frequency settings of a service center
    """
    serializer_class = SMSFrequencyUpdateSerializer
    permission_classes = [IsAuthenticated, IsCenterAdmin]
    http_method_names = ['patch', 'put']  # Allow both partial and full updates

    @swagger_auto_schema(
        operation_description="Update SMS frequency settings for a service center",
        operation_summary="Update SMS Frequency Settings",
        request_body=SMSFrequencyUpdateSerializer,
        responses={
            200: openapi.Response(
                description="SMS frequency updated successfully",
                schema=SMSFrequencyUpdateSerializer
            ),
            400: openapi.Response(
                description="Bad request - Invalid frequency values",
                examples={
                    "application/json": {
                        "sms_frequency_for_private_vehicles": [
                            "SMS frequency for private vehicles must be between 1 and 12 months"
                        ]
                    }
                }
            ),
            403: openapi.Response(
                description="Permission denied",
                examples={
                    "application/json": {
                        "detail": "You do not have permission to perform this action."
                    }
                }
            ),
            404: openapi.Response(
                description="Service center not found",
                examples={
                    "application/json": {
                        "detail": "Not found."
                    }
                }
            )
        },
        tags=['Service Centers']
    )
    def update(self, request, *args, **kwargs):
        """Handle full update"""
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update SMS frequency settings for a service center",
        operation_summary="Partial Update SMS Frequency Settings",
        request_body=SMSFrequencyUpdateSerializer,
        responses={
            200: openapi.Response(
                description="SMS frequency updated successfully",
                schema=SMSFrequencyUpdateSerializer
            ),
            400: openapi.Response(description="Bad request"),
            403: openapi.Response(description="Permission denied"),
            404: openapi.Response(description="Service center not found")
        },
        tags=['Service Centers']
    )
    def partial_update(self, request, *args, **kwargs):
        """Handle partial update"""
        return super().partial_update(request, *args, **kwargs)

    def get_object(self):
        """Get the service center object based on user role"""
        user = self.request.user
        service_center_id = self.kwargs.get('pk')
        
        if user.role == 'admin':
            # Super admin can update any service center
            return get_object_or_404(ServiceCenter, id=service_center_id)
        elif user.role == 'centeradmin':
            # Center admin can only update their own service center
            if service_center_id and int(service_center_id) != user.service_center.id:
                # If trying to update different service center, deny access
                return get_object_or_404(ServiceCenter, id=0)  # Force 404
            return get_object_or_404(ServiceCenter, id=user.service_center.id)
        else:
            # Staff cannot update SMS frequency settings
            return get_object_or_404(ServiceCenter, id=0)  # Force 404

    def perform_update(self, serializer):
        """Custom update logic if needed"""
        serializer.save()
        # You can add logging or additional logic here if needed



@swagger_auto_schema(
    method='post',
    operation_description="Activate subscription for a service center",
    operation_summary="Activate Subscription",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'duration_months': openapi.Schema(type=openapi.TYPE_INTEGER, description='Subscription duration in months', default=12),
            'amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Payment amount'),
            'razorpay_payment_id': openapi.Schema(type=openapi.TYPE_STRING, description='Razorpay payment ID'),
            'razorpay_order_id': openapi.Schema(type=openapi.TYPE_STRING, description='Razorpay order ID'),
            'razorpay_signature': openapi.Schema(type=openapi.TYPE_STRING, description='Razorpay signature'),
        },
        required=['amount', 'razorpay_payment_id', 'razorpay_order_id', 'razorpay_signature']
    ),
    responses={
        200: openapi.Response(
            description="Subscription activated successfully",
            examples={
                "application/json": {
                    "success": True,
                    "message": "Subscription activated successfully",
                    "data": {
                        "subscription": {
                            "id": 1,
                            "status": "active",
                            "started_at": "2024-08-01T10:30:00Z",
                            "expires_at": "2025-08-01T10:30:00Z",
                            "amount": "1200.00"
                        }
                    }
                }
            }
        ),
        400: openapi.Response(description="Subscription activation failed"),
        403: openapi.Response(description="Permission denied")
    },
    tags=['Subscriptions']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activate_subscription(request, service_center_id):
    """
    API endpoint to activate subscription for a service center
    """
    try:
        user = request.user
        
        # Permission check
        if user.role not in ['admin', 'centeradmin']:
            return Response({
                'success': False,
                'message': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get service center
        if user.role == 'admin':
            service_center = get_object_or_404(ServiceCenter, id=service_center_id)
        else:
            service_center = get_object_or_404(ServiceCenter, id=user.service_center.id)
        
        # Get subscription data from request
        duration_months = request.data.get('duration_months', 12)
        amount = request.data.get('amount', 0)
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_signature = request.data.get('razorpay_signature')
        
        with transaction.atomic():
            # Update service center subscription dates
            service_center.subscription_started_at = timezone.now()
            service_center.subscription_valid_until = (
                timezone.now().date() + timedelta(days=duration_months * 30)
            )
            service_center.save()
            
            # Create new subscription record
            subscription = Subscription.objects.create(
                service_center=service_center,
                status='active',
                started_at=timezone.now(),
                expires_at=timezone.now() + timedelta(days=duration_months * 30),
                amount=amount,
                currency='INR',
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=razorpay_order_id,
                razorpay_signature=razorpay_signature
            )
            
            # Mark trial subscriptions as expired
            Subscription.objects.filter(
                service_center=service_center,
                status='trial'
            ).update(status='expired')
        
        return Response({
            'success': True,
            'message': 'Subscription activated successfully',
            'data': {
                'subscription': SubscriptionSerializer(subscription).data,
                'service_center': ServiceCenterDetailSerializer(service_center).data
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Subscription activation failed',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_description="Check subscription status for a service center",
    operation_summary="Get Subscription Status",
    responses={
        200: openapi.Response(
            description="Subscription status retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "data": {
                        "service_center_id": 1,
                        "service_center_name": "ABC Service Center",
                        "can_access_service": True,
                        "is_trial_active": False,
                        "is_subscription_active": True,
                        "trial_ends_at": "2024-08-16T10:30:00Z",
                        "subscription_valid_until": "2025-08-01",
                        "current_subscription": {
                            "id": 1,
                            "status": "active",
                            "started_at": "2024-08-01T10:30:00Z",
                            "expires_at": "2025-08-01T10:30:00Z"
                        }
                    }
                }
            }
        ),
        403: openapi.Response(description="Permission denied"),
        404: openapi.Response(description="Service center not found")
    },
    tags=['Subscriptions']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_status(request, service_center_id):
    """
    API endpoint to check subscription status
    """
    try:
        user = request.user
        
        # Permission check
        if user.role == 'admin':
            service_center = get_object_or_404(ServiceCenter, id=service_center_id)
        elif user.role in ['centeradmin', 'staff']:
            service_center = get_object_or_404(ServiceCenter, id=user.service_center.id)
        else:
            return Response({
                'success': False,
                'message': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        current_subscription = service_center.subscriptions.filter(
            status__in=['trial', 'active']
        ).first()
        
        response_data = {
            'success': True,
            'data': {
                'service_center_id': service_center.id,
                'service_center_name': service_center.name,
                'can_access_service': service_center.can_access_service(),
                'is_trial_active': service_center.is_trial_active(),
                'is_subscription_active': service_center.is_subscription_active(),
                'trial_ends_at': service_center.trial_ends_at,
                'subscription_valid_until': service_center.subscription_valid_until,
                'current_subscription': SubscriptionSerializer(current_subscription).data if current_subscription else None
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to fetch subscription status',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionListView(generics.ListAPIView):
    """
    API endpoint for listing subscriptions
    """
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List subscriptions based on user role and optional service center filter",
        operation_summary="List Subscriptions",
        manual_parameters=[
            openapi.Parameter(
                'service_center_id',
                openapi.IN_QUERY,
                description="Filter by service center ID (admin only)",
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        responses={
            200: SubscriptionSerializer(many=True),
            403: openapi.Response(description="Permission denied")
        },
        tags=['Subscriptions']
    )
    def get_queryset(self):
        user = self.request.user
        service_center_id = self.request.query_params.get('service_center_id')
        
        if user.role == 'admin':
            queryset = Subscription.objects.all()
            if service_center_id:
                queryset = queryset.filter(service_center_id=service_center_id)
            return queryset
        elif user.role in ['centeradmin', 'staff']:
            return Subscription.objects.filter(service_center=user.service_center)
        else:
            return Subscription.objects.none()


class UserRegistrationView(generics.CreateAPIView):
    """
    API endpoint for adding new users to a service center
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Add a new user to a service center",
        operation_summary="Register New User",
        request_body=UserRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="User created successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "User created successfully",
                        "data": {
                            "user_id": 1,
                            "email": "user@example.com",
                            "role": "staff",
                            "service_center": "ABC Service Center"
                        }
                    }
                }
            ),
            400: openapi.Response(description="User creation failed"),
            403: openapi.Response(description="Permission denied")
        },
        tags=['Users']
    )
    def create(self, request, *args, **kwargs):
        # Add service center validation based on user role
        user = request.user
        service_center_id = request.data.get('service_center_id')
        
        if user.role == 'centeradmin':
            if int(service_center_id) != user.service_center.id:
                return Response({
                    'success': False,
                    'message': 'You can only add users to your own service center'
                }, status=status.HTTP_403_FORBIDDEN)
        elif user.role != 'admin':
            return Response({
                'success': False,
                'message': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user_obj = serializer.save()
            return Response({
                'success': True,
                'message': 'User created successfully',
                'data': {
                    'user_id': user_obj.id,
                    'email': user_obj.email,
                    'role': user_obj.role,
                    'service_center': user_obj.service_center.name
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': 'User creation failed',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_description="Get license key information and status",
    operation_summary="Get License Key Info",
    responses={
        200: openapi.Response(
            description="License key information retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "data": {
                        "license_key": "ABCD1234567890123456",
                        "is_used": True,
                        "valid_until": "2024-08-16",
                        "assigned_to": "ABC Service Center",
                        "service_center_active": True
                    }
                }
            }
        ),
        404: openapi.Response(
            description="License key not found",
            examples={
                "application/json": {
                    "success": False,
                    "message": "License key not found",
                    "error": "No LicenseKey matches the given query."
                }
            }
        )
    },
    tags=['License Keys']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCenterAdmin])
def license_key_info(request, license_key):
    """
    API endpoint to get license key information
    """
    try:
        license_obj = get_object_or_404(LicenseKey, key=license_key)
        
        response_data = {
            'success': True,
            'data': {
                'license_key': license_obj.key,
                'is_used': license_obj.is_used,
                'valid_until': license_obj.valid_until,
                'assigned_to': license_obj.assigned_to.name if license_obj.assigned_to else None,
                'service_center_active': license_obj.assigned_to.can_access_service() if license_obj.assigned_to else False
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'License key not found',
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='get',
    operation_description="Get dashboard statistics based on user role",
    operation_summary="Get Dashboard Statistics",
    responses={
        200: openapi.Response(
            description="Dashboard statistics retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "data": {
                        "total_service_centers": 10,
                        "active_service_centers": 8,
                        "trial_centers": 3,
                        "subscribed_centers": 5
                    }
                }
            }
        ),
        400: openapi.Response(description="Failed to fetch dashboard stats")
    },
    tags=['Dashboard']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    API endpoint for dashboard statistics
    """
    try:
        user = request.user
        
        if user.role == 'admin':
            # Global stats for super admin
            total_service_centers = ServiceCenter.objects.count()
            active_service_centers = ServiceCenter.objects.filter(is_active=True).count()
            trial_centers = ServiceCenter.objects.filter(
                subscriptions__status='trial'
            ).distinct().count()
            subscribed_centers = ServiceCenter.objects.filter(
                subscriptions__status='active'
            ).distinct().count()
            
            stats = {
                'total_service_centers': total_service_centers,
                'active_service_centers': active_service_centers,
                'trial_centers': trial_centers,
                'subscribed_centers': subscribed_centers,
            }
            
        elif user.role in ['centeradmin', 'staff']:
            # Stats for service center
            service_center = user.service_center
            total_users = service_center.users.count()
            active_users = service_center.users.filter(is_active=True).count()
            
            stats = {
                'service_center_name': service_center.name,
                'total_users': total_users,
                'active_users': active_users,
                'can_access_service': service_center.can_access_service(),
                'is_trial_active': service_center.is_trial_active(),
                'is_subscription_active': service_center.is_subscription_active(),
                'trial_ends_at': service_center.trial_ends_at,
                'subscription_valid_until': service_center.subscription_valid_until,
            }
        
        return Response({
            'success': True,
            'data': stats
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to fetch dashboard stats',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    

# razorpay imlimentation


# payment_views.py - Add these views to your existing views.py file

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import razorpay
from django.conf import settings
import logging

from .models import (
    ServiceCenter, PaymentPlan, PaymentTransaction, 
    SubscriptionHistory, CustomUser
)
from .serializers import (
    PaymentPlanSerializer, CreatePaymentOrderSerializer,
    PaymentVerificationSerializer, PaymentTransactionSerializer,
    SubscriptionStatusSerializer, ExtendSubscriptionResponseSerializer,
    PaymentOrderResponseSerializer, PaymentDashboardSerializer,
    ServiceCenterPaymentStatusSerializer, SubscriptionHistorySerializer
)
from .permissions import IsAdmin, IsCenterAdmin, IsAuthenticatedForSwagger

logger = logging.getLogger(__name__)


# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


class PaymentPlanListView(generics.ListAPIView):
    """
    Get list of available payment plans
    
    Returns all active payment plans available for subscription.
    """
    queryset = PaymentPlan.objects.filter(is_active=True)
    serializer_class = PaymentPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get list of available payment plans",
        responses={
            200: PaymentPlanSerializer(many=True),
            401: "Unauthorized"
        },
        tags=['Payment Management']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@swagger_auto_schema(
    method='post',
    request_body=CreatePaymentOrderSerializer,
    responses={
        200: PaymentOrderResponseSerializer,
        400: "Bad Request",
        401: "Unauthorized",
        403: "Access denied - Service already active or insufficient permissions"
    },
    operation_description="""
    Create Razorpay order for subscription extension
    
    Creates a new payment order for 1-year subscription extension (₹1499).
    Only center admins can initiate payment for their service center.
    """,
    tags=['Payment Management']
)
@api_view(['POST'])
@permission_classes([IsCenterAdmin])
def create_payment_order(request):
    """Create Razorpay payment order for subscription extension"""
    
    serializer = CreatePaymentOrderSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': 'Invalid request data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = request.user
        
        # Get service center
        if user.role == 'admin':
            # Admin can specify service center ID
            service_center_id = request.data.get('service_center_id')
            if not service_center_id:
                return Response({
                    'success': False,
                    'message': 'service_center_id is required for admin users'
                }, status=status.HTTP_400_BAD_REQUEST)
            service_center = get_object_or_404(ServiceCenter, id=service_center_id)
        else:
            service_center = user.service_center
        
        amount = float(serializer.validated_data['amount'])
        
        # Create Razorpay order
        order_data = {
            'amount': int(amount * 100),  # Convert to paise
            'currency': 'INR',
            'receipt': f"extension_{service_center.id}_{timezone.now().timestamp()}",
            'notes': {
                'service_center_id': service_center.id,
                'service_center_name': service_center.name,
                'extension_type': '1_year'
            }
        }
        
        razorpay_order = razorpay_client.order.create(order_data)
        
        # Get or create payment plan
        payment_plan, created = PaymentPlan.objects.get_or_create(
            plan_type='yearly',
            duration_months=12,
            defaults={
                'name': '1 Year Extension',
                'price': 1499.00,
                'currency': 'INR',
                'description': '1 Year subscription extension'
            }
        )
        
        # Create payment transaction record
        payment_transaction = PaymentTransaction.objects.create(
            service_center=service_center,
            payment_plan=payment_plan,
            transaction_type='extension',
            amount=amount,
            currency='INR',
            razorpay_order_id=razorpay_order['id'],
            initiated_by=user,
            status='pending'
        )
        
        response_data = {
            'success': True,
            'data': {
                'transaction_id': payment_transaction.transaction_id,
                'order_id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'key_id': settings.RAZORPAY_KEY_ID,
                'service_center_name': service_center.name
            },
            'order_id': razorpay_order['id'],
            'amount': razorpay_order['amount'],
            'currency': razorpay_order['currency'],
            'key_id': settings.RAZORPAY_KEY_ID
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Payment order creation failed: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to create payment order',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    request_body=PaymentVerificationSerializer,
    responses={
        200: ExtendSubscriptionResponseSerializer,
        400: "Payment verification failed",
        401: "Unauthorized",
        404: "Transaction not found"
    },
    operation_description="""
    Verify payment and extend subscription
    
    Verifies the Razorpay payment signature and extends the service center 
    subscription by 1 year upon successful verification.
    """,
    tags=['Payment Management']
)
@api_view(['POST'])
@permission_classes([IsCenterAdmin])
def verify_payment_and_extend(request):
    """Verify Razorpay payment and extend subscription"""
    
    serializer = PaymentVerificationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': 'Payment verification failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            razorpay_order_id = serializer.validated_data['razorpay_order_id']
            razorpay_payment_id = serializer.validated_data['razorpay_payment_id']
            razorpay_signature = serializer.validated_data['razorpay_signature']
            
            # Find the payment transaction
            payment_transaction = get_object_or_404(
                PaymentTransaction,
                razorpay_order_id=razorpay_order_id,
                status='pending'
            )
            
            # Update transaction with payment details
            payment_transaction.razorpay_payment_id = razorpay_payment_id
            payment_transaction.razorpay_signature = razorpay_signature
            payment_transaction.status = 'completed'
            payment_transaction.completed_at = timezone.now()
            payment_transaction.save()
            
            # Extend subscription
            service_center = payment_transaction.service_center
            new_end_date = service_center.extend_subscription(
                months=12,
                payment_transaction=payment_transaction
            )
            
            # Get updated subscription status
            subscription_status = service_center.get_subscription_status()
            
            response_data = {
                'success': True,
                'message': 'Payment verified and subscription extended successfully',
                'data': {
                    'transaction_id': payment_transaction.transaction_id,
                    'new_subscription_end_date': new_end_date.isoformat(),
                    'amount_paid': str(payment_transaction.amount),
                    'service_center_name': service_center.name
                },
                'subscription_status': subscription_status
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
    except PaymentTransaction.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Transaction not found or already processed'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Payment verification failed: {str(e)}")
        return Response({
            'success': False,
            'message': 'Payment verification failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    responses={
        200: SubscriptionStatusSerializer,
        401: "Unauthorized",
        403: "Access denied"
    },
    operation_description="""
    Get subscription status for current user's service center
    
    Returns detailed subscription information including access status,
    trial/subscription validity, and remaining days.
    """,
    tags=['Subscription Management']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_subscription_status(request):
    """Get subscription status for user's service center"""
    
    user = request.user
    
    if user.role == 'admin':
        # Admin can check any service center
        service_center_id = request.GET.get('service_center_id')
        if service_center_id:
            service_center = get_object_or_404(ServiceCenter, id=service_center_id)
        else:
            return Response({
                'success': False,
                'message': 'service_center_id parameter required for admin users'
            }, status=status.HTTP_400_BAD_REQUEST)
    else:
        if not user.service_center:
            return Response({
                'success': False,
                'message': 'User not associated with any service center'
            }, status=status.HTTP_400_BAD_REQUEST)
        service_center = user.service_center
    
    # Get subscription status
    subscription_status = service_center.get_subscription_status()
    subscription_status['requires_payment'] = not subscription_status['can_access']
    
    # Add payment plan information
    yearly_plan = PaymentPlan.objects.filter(
        plan_type='yearly',
        is_active=True
    ).first()
    
    if yearly_plan:
        subscription_status['extension_plan'] = {
            'price': str(yearly_plan.price),
            'duration_months': yearly_plan.duration_months,
            'description': yearly_plan.description
        }
    
    serializer = SubscriptionStatusSerializer(subscription_status)
    
    return Response({
        'success': True,
        'data': serializer.data,
        'service_center': {
            'id': service_center.id,
            'name': service_center.name,
            'email': service_center.email
        }
    }, status=status.HTTP_200_OK)


class PaymentTransactionListView(generics.ListAPIView):
    """
    Get payment transaction history
    
    Returns paginated list of payment transactions for the service center.
    Center admins see only their transactions, super admins see all.
    """
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsCenterAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return PaymentTransaction.objects.all().order_by('-created_at')
        else:
            return PaymentTransaction.objects.filter(
                service_center=user.service_center
            ).order_by('-created_at')

    @swagger_auto_schema(
        operation_description="Get payment transaction history",
        responses={
            200: PaymentTransactionSerializer(many=True),
            401: "Unauthorized",
            403: "Access denied"
        },
        tags=['Payment Management']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SubscriptionHistoryListView(generics.ListAPIView):
    """
    Get subscription history
    
    Returns paginated list of subscription history for the service center.
    """
    serializer_class = SubscriptionHistorySerializer
    permission_classes = [IsCenterAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return SubscriptionHistory.objects.all().order_by('-created_at')
        else:
            return SubscriptionHistory.objects.filter(
                service_center=user.service_center
            ).order_by('-created_at')

    @swagger_auto_schema(
        operation_description="Get subscription history",
        responses={
            200: SubscriptionHistorySerializer(many=True),
            401: "Unauthorized",
            403: "Access denied"
        },
        tags=['Subscription Management']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@swagger_auto_schema(
    method='get',
    responses={
        200: PaymentDashboardSerializer,
        401: "Unauthorized",
        403: "Admin access required"
    },
    operation_description="""
    Get payment dashboard statistics (Admin only)
    
    Returns comprehensive payment and subscription statistics including
    revenue data, transaction counts, and service center status breakdown.
    """,
    tags=['Admin Dashboard']
)
@api_view(['GET'])
@permission_classes([IsAdmin])
def payment_dashboard_stats(request):
    """Get payment dashboard statistics for admin"""
    
    from datetime import datetime, timedelta
    from django.db.models import Sum, Count
    
    # Calculate date range for monthly revenue
    today = timezone.now().date()
    first_day_of_month = today.replace(day=1)
    
    # Revenue statistics
    total_revenue = PaymentTransaction.objects.filter(
        status='completed'
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    monthly_revenue = PaymentTransaction.objects.filter(
        status='completed',
        completed_at__date__gte=first_day_of_month
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Transaction statistics
    transaction_stats = PaymentTransaction.objects.aggregate(
        total=Count('id'),
        successful=Count('id', filter=Q(status='completed')),
        failed=Count('id', filter=Q(status='failed'))
    )
    
    # Service center statistics
    active_subscriptions = ServiceCenter.objects.filter(
        subscription_valid_until__gte=today,
        is_active=True
    ).count()
    
    trial_centers = ServiceCenter.objects.filter(
        trial_ends_at__gte=timezone.now(),
        subscription_valid_until__isnull=True,
        is_active=True
    ).count()
    
    expired_centers = ServiceCenter.objects.filter(
        Q(subscription_valid_until__lt=today) | Q(trial_ends_at__lt=timezone.now()),
        is_active=True
    ).count()
    
    # Recent transactions
    recent_transactions = PaymentTransaction.objects.filter(
        status='completed'
    ).order_by('-completed_at')[:10]
    
    dashboard_data = {
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'total_transactions': transaction_stats['total'],
        'successful_transactions': transaction_stats['successful'],
        'failed_transactions': transaction_stats['failed'],
        'active_subscriptions': active_subscriptions,
        'trial_centers': trial_centers,
        'expired_centers': expired_centers,
        'recent_transactions': PaymentTransactionSerializer(
            recent_transactions, many=True
        ).data
    }
    
    return Response({
        'success': True,
        'data': dashboard_data
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'service_center_id': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description='Service center ID to disable'
            )
        },
        required=['service_center_id']
    ),
    responses={
        200: "Service center disabled successfully",
        400: "Bad request",
        401: "Unauthorized",
        403: "Admin access required",
        404: "Service center not found"
    },
    operation_description="""
    Disable service center access (Admin only)
    
    Disables access for a service center when subscription expires.
    All users of the service center will be unable to access the application.
    """,
    tags=['Admin Management']
)
@api_view(['POST'])
@permission_classes([IsAdmin])
def disable_service_center(request):
    """Disable service center access (Admin only)"""
    
    service_center_id = request.data.get('service_center_id')
    if not service_center_id:
        return Response({
            'success': False,
            'message': 'service_center_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service_center = get_object_or_404(ServiceCenter, id=service_center_id)
        service_center.is_active = False
        service_center.save()
        
        return Response({
            'success': True,
            'message': f'Service center "{service_center.name}" has been disabled',
            'data': {
                'service_center_id': service_center.id,
                'name': service_center.name,
                'is_active': service_center.is_active
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to disable service center',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'service_center_id': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description='Service center ID to enable'
            )
        },
        required=['service_center_id']
    ),
    responses={
        200: "Service center enabled successfully",
        400: "Bad request",
        401: "Unauthorized",
        403: "Admin access required",
        404: "Service center not found"
    },
    operation_description="""
    Enable service center access (Admin only)
    
    Re-enables access for a disabled service center.
    """,
    tags=['Admin Management']
)
@api_view(['POST'])
@permission_classes([IsAdmin])
def enable_service_center(request):
    """Enable service center access (Admin only)"""
    
    service_center_id = request.data.get('service_center_id')
    if not service_center_id:
        return Response({
            'success': False,
            'message': 'service_center_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service_center = get_object_or_404(ServiceCenter, id=service_center_id)
        service_center.is_active = True
        service_center.save()
        
        return Response({
            'success': True,
            'message': f'Service center "{service_center.name}" has been enabled',
            'data': {
                'service_center_id': service_center.id,
                'name': service_center.name,
                'is_active': service_center.is_active
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to enable service center',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServiceCenterPaymentStatusListView(generics.ListAPIView):
    """
    Get all service centers with payment status (Admin only)
    
    Returns paginated list of all service centers with their payment
    and subscription status information.
    """
    serializer_class = ServiceCenterPaymentStatusSerializer
    permission_classes = [IsAdmin]
    queryset = ServiceCenter.objects.all().order_by('-created_at')

    @swagger_auto_schema(
        operation_description="Get all service centers with payment status",
        responses={
            200: ServiceCenterPaymentStatusSerializer(many=True),
            401: "Unauthorized",
            403: "Admin access required"
        },
        tags=['Admin Dashboard']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# Custom permission class for payment access
class HasActiveSubscriptionOrTrial(permissions.BasePermission):
    """
    Custom permission to check if service center has active subscription or trial
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin always has access
        if request.user.role == 'admin':
            return True
            
        # Check if user has service center
        if not request.user.service_center:
            return False
            
        # Check if service center can access service
        return request.user.service_center.can_access_service()


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description="Access status",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'can_access': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'redirect_to_payment': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                }
            )
        ),
        401: "Unauthorized"
    },
    operation_description="""
    Check if user can access the application
    
    Returns whether the user's service center has active subscription/trial.
    If access is denied, indicates whether payment is required.
    """,
    tags=['Access Control']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_access_permission(request):
    """Check if user can access the application"""
    
    user = request.user
    
    # Admin always has access
    if user.role == 'admin':
        return Response({
            'success': True,
            'can_access': True,
            'message': 'Admin access granted',
            'redirect_to_payment': False
        }, status=status.HTTP_200_OK)
    
    # Check service center
    if not user.service_center:
        return Response({
            'success': True,
            'can_access': False,
            'message': 'User not associated with any service center',
            'redirect_to_payment': False
        }, status=status.HTTP_200_OK)
    
    service_center = user.service_center
    can_access = service_center.can_access_service()
    
    if can_access:
        message = 'Access granted'
        redirect_to_payment = False
    else:
        if user.role == 'centeradmin':
            message = 'Subscription expired. Please renew to continue.'
            redirect_to_payment = True
        else:
            message = 'Access denied. Please contact your center admin.'
            redirect_to_payment = False
    
    return Response({
        'success': True,
        'can_access': can_access,
        'message': message,
        'redirect_to_payment': redirect_to_payment,
        'user_role': user.role,
        'subscription_status': service_center.get_subscription_status()
    }, status=status.HTTP_200_OK)
        