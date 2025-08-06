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
    LicenseKeySerializer
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
    

# webview form templates  ===========================================================
from django.contrib.auth import authenticate, login, logout
from .decorators import admin_only
from django.http import HttpResponseNotFound
from .forms import ServiceCenterForm,ServiceCenterRegistrationForm

def admin_login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = authenticate(request, email=email, password=password)
        if user is not None:
            # Allow only if user is admin role or superuser
            if user.is_superuser or getattr(user, 'role', None) == 'admin':
                login(request, user)
                return redirect("admin_dashboard")
            else:
                messages.error(request, 'You do not have admin access.')
                return redirect('admin_login')
        else:
            messages.error(request, 'Username or password incorrect.')
            return redirect('admin_login')

    return render(request, "login.html")

@admin_only
def admin_dashboard(request):
    return render(request,"index.html")


def admin_servicecenters(request):
    service_centers = ServiceCenter.objects.all().order_by('-id')

    context = {
        "service_centers":service_centers
    }
    return render(request,"service_centers/service_centers.html",context)



@admin_only
def service_center_add(request):
    
    if request.method == 'POST':
        form = ServiceCenterRegistrationForm()
        if form.is_valid():
            form.save()
            messages.success(request, 'Service center added successfully.')
            return redirect('admin_servicecenters')
        else:
            messages.error(request, 'Failed to add service center. Please check the form.')
    else:
        form = ServiceCenterRegistrationForm()

    return render(request, "service_centers/add_service_center.html", {'form': form})


@admin_only
def service_center_delete(request, pk):
    try:
        service_center = ServiceCenter.objects.get(pk=pk)
        service_center.delete()
        messages.success(request, 'Service center deleted successfully.')
    except ServiceCenter.DoesNotExist:
        messages.error(request, 'Service center not found.')
    return redirect('admin_servicecenters')


@admin_only
def service_center_detail(request, pk):
    try:
        center = ServiceCenter.objects.get(pk=pk)
        return render(request, "service_centers/service_center_detail.html", {'center': center})
    except ServiceCenter.DoesNotExist:
        return HttpResponseNotFound("Service center not found.")


@admin_only
def service_center_edit(request, pk):
    try:
        service_center = ServiceCenter.objects.get(pk=pk)
        if request.method == 'POST':
            form = ServiceCenterForm(request.POST,instance = service_center )
            if form.is_valid():
                form.save()
                messages.success(request, 'Service center updated successfully.')
                return redirect('admin_servicecenters')
            else:
                messages.error(request, 'Failed to update service center. Please check the form.')
        else:
            form = ServiceCenterForm(instance=service_center)

        return render(request, "service_centers/edit_service_center.html", {'form': form, 'center': service_center})
    except ServiceCenter.DoesNotExist:
        return HttpResponseNotFound("Service center not found.")


# =================================================================================== 