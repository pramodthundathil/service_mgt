# views.py - Fixed version with proper swagger documentation
from django.shortcuts import render, get_object_or_404 
from index.permissions import IsAdmin, IsCenterAdmin
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch, Count, Sum, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Brand, VehicleVariant, Customer, VehicleOnService, ServiceEntry
from .serializers import *


# ============= USER VIEWS =============

class BrandUserViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for users to browse brands"""
    
    queryset = Brand.objects.prefetch_related('brand_variants')
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BrandDetailUserSerializer
        return BrandUserSerializer
        
    @swagger_auto_schema(
        operation_description="Get all variants for a specific brand",
        responses={200: VehicleVariantUserSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def variants(self, request, pk=None):
        """Get all variants for a specific brand"""
        brand = self.get_object()
        variants = VehicleVariant.objects.filter(brand=brand).select_related('brand')
        serializer = VehicleVariantUserSerializer(variants, many=True, context={'request': request})
        return Response(serializer.data)
    

    
class VehicleVariantUserViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for users to browse vehicle variants"""
    
    queryset = VehicleVariant.objects.select_related('brand')
    serializer_class = VehicleVariantUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Allow filtering by brand"""
        queryset = VehicleVariant.objects.select_related('brand')
        brand_id = self.request.query_params.get('brand', None)
        body_type = self.request.query_params.get('body_type', None)
        
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        if body_type:
            queryset = queryset.filter(body_type=body_type)
            
        return queryset


class BrandAdminViewSet(viewsets.ModelViewSet):
    """Full CRUD viewset for admin brand management"""
    
    queryset = Brand.objects.prefetch_related('vehiclevariant_set')
    serializer_class = BrandAdminSerializer
    permission_classes = [IsAdmin]


class VehicleVariantAdminViewSet(viewsets.ModelViewSet):
    """Full CRUD viewset for admin vehicle variant management"""
    
    queryset = VehicleVariant.objects.select_related('brand')
    serializer_class = VehicleVariantAdminSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        """Allow admin filtering"""
        queryset = VehicleVariant.objects.select_related('brand')
        brand_id = self.request.query_params.get('brand', None)
        
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
            
        return queryset


# ============= SERVICE CENTER VIEWS =============

class ServiceCenterPermission(permissions.BasePermission):
    """
    Custom permission to ensure users can only access data from their service center.
    Only centeradmin and staff roles are allowed.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.role not in ['centeradmin', 'staff']:
            return False
        
        if not hasattr(request.user, 'service_center') or not request.user.service_center:
            return False
        
        return True


class BrandReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Brand model - Read Only for mobile app.
    
    Provides list and retrieve operations for vehicle brands.
    Used by mobile app to populate brand selection dropdowns.
    """
    queryset = Brand.objects.all()
    serializer_class = BrandReadOnlySerializer
    permission_classes = [ServiceCenterPermission]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @swagger_auto_schema(
        operation_description="Get list of all available vehicle brands",
        responses={200: BrandReadOnlySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get details of a specific brand",
        responses={200: BrandReadOnlySerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class VehicleVariantReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for VehicleVariant model - Read Only for mobile app.
    """
    queryset = VehicleVariant.objects.select_related('brand').all()
    serializer_class = VehicleVariantReadOnlySerializer
    permission_classes = [ServiceCenterPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['brand', 'body_type']
    search_fields = ['variant_name', 'brand__name']
    ordering_fields = ['variant_name', 'brand__name', 'created_at']
    ordering = ['brand__name', 'variant_name']
    
    @swagger_auto_schema(
        operation_description="Get list of vehicle variants with optional brand filtering",
        manual_parameters=[
            openapi.Parameter('brand', openapi.IN_QUERY, description="Filter by brand ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('body_type', openapi.IN_QUERY, description="Filter by body type", type=openapi.TYPE_STRING),
        ],
        responses={200: VehicleVariantReadOnlySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get details of a specific vehicle variant",
        responses={200: VehicleVariantReadOnlySerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get variants for a specific brand",
        responses={200: VehicleVariantReadOnlySerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='by-brand/(?P<brand_id>[^/.]+)')
    def by_brand(self, request, brand_id=None):
        variants = self.queryset.filter(brand_id=brand_id)
        serializer = self.get_serializer(variants, many=True)
        return Response(serializer.data)


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for Customer model with full CRUD operations."""
    
    serializer_class = CustomerSerializer
    permission_classes = [ServiceCenterPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'phone', 'date_added']
    ordering = ['-date_added']
    
    def get_queryset(self):
        """Filter customers by user's service center"""
        if not self.request.user.is_authenticated or not hasattr(self.request.user, 'service_center'):
            return Customer.objects.none()
        
        return Customer.objects.filter(
            service_center=self.request.user.service_center
        ).select_related('service_center')
    
    @swagger_auto_schema(
        operation_description="Get customer's vehicles",
        responses={200: CustomerVehicleSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def vehicles(self, request, pk=None):
        customer = self.get_object()
        vehicles = customer.customer_vehicles.select_related('vehicle_type__brand')
        serializer = CustomerVehicleSerializer(vehicles, many=True)
        return Response(serializer.data)


class VehicleOnServiceViewSet(viewsets.ModelViewSet):
    """ViewSet for VehicleOnService model with full CRUD operations."""
    
    serializer_class = VehicleOnServiceSerializer
    permission_classes = [ServiceCenterPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'vehicle_type', 'transport_type', 'vehicle_model']
    search_fields = ['vehicle_number', 'customer__name', 'customer__phone']
    ordering_fields = ['vehicle_number', 'vehicle_model', 'date_added']
    ordering = ['-date_added']
    
    def get_queryset(self):
        """Filter vehicles by user's service center"""
        if not self.request.user.is_authenticated or not hasattr(self.request.user, 'service_center'):
            return VehicleOnService.objects.none()
        
        return VehicleOnService.objects.filter(
            service_center=self.request.user.service_center
        ).select_related('customer', 'vehicle_type__brand', 'service_center').prefetch_related('vehicle_services')
    
    @swagger_auto_schema(
        operation_description="Get vehicle's service history",
        responses={200: ServiceEntrySerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def service_history(self, request, pk=None):
        vehicle = self.get_object()
        services = vehicle.vehicle_services.select_related('customer', 'performed_by')
        serializer = ServiceEntrySerializer(services, many=True)
        return Response(serializer.data)


class ServiceEntryViewSet(viewsets.ModelViewSet):
    """ViewSet for ServiceEntry model with full CRUD operations."""
    
    serializer_class = ServiceEntrySerializer
    permission_classes = [ServiceCenterPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'vehicle', 'service_type', 'service_date']
    search_fields = ['customer__name', 'vehicle__vehicle_number', 'description']
    ordering_fields = ['service_date', 'price', 'created_at']
    ordering = ['-service_date', '-created_at']
    
    def get_queryset(self):
        """Filter service entries by user's service center"""
        if not self.request.user.is_authenticated or not hasattr(self.request.user, 'service_center'):
            return ServiceEntry.objects.none()
        
        return ServiceEntry.objects.filter(
            service_center=self.request.user.service_center
        ).select_related('customer', 'vehicle', 'performed_by', 'service_center')
    
    @swagger_auto_schema(
        operation_description="Get overdue services in your service center",
        responses={200: ServiceEntrySerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        today = timezone.now().date()
        overdue_services = self.get_queryset().filter(
            next_service_due_date__lt=today
        )
        serializer = self.get_serializer(overdue_services, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get upcoming services (next 30 days)",
        responses={200: ServiceEntrySerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        today = timezone.now().date()
        upcoming_date = today + timedelta(days=30)
        upcoming_services = self.get_queryset().filter(
            next_service_due_date__range=[today, upcoming_date]
        )
        serializer = self.get_serializer(upcoming_services, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get service statistics for the current month",
        responses={200: openapi.Response(
            description="Monthly service statistics",
            examples={
                "application/json": {
                    "total_services": 150,
                    "total_revenue": "25000.00",
                    "service_types": [
                        {"service_type": "alignment", "count": 60},
                        {"service_type": "balancing", "count": 45}
                    ]
                }
            }
        )}
    )
    @action(detail=False, methods=['get'])
    def monthly_stats(self, request):
        today = timezone.now()
        month_start = today.replace(day=1)
        
        monthly_services = self.get_queryset().filter(
            service_date__gte=month_start.date()
        )
        
        total_services = monthly_services.count()
        total_revenue = monthly_services.aggregate(
            total=Sum('price')
        )['total'] or 0
        
        service_types = monthly_services.values('service_type').annotate(
            count=Count('service_type')
        ).order_by('-count')
        
        return Response({
            'total_services': total_services,
            'total_revenue': total_revenue,
            'service_types': service_types
        })


class DashboardViewSet(viewsets.ViewSet):
    """ViewSet for dashboard summary and statistics."""
    
    permission_classes = [ServiceCenterPermission]
    
    @swagger_auto_schema(
        operation_description="Get dashboard summary for your service center",
        responses={200: ServiceSummarySerializer()}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        service_center = request.user.service_center
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Basic counts
        total_customers = Customer.objects.filter(service_center=service_center).count()
        total_vehicles = VehicleOnService.objects.filter(service_center=service_center).count()
        total_services = ServiceEntry.objects.filter(service_center=service_center).count()
        
        # Monthly statistics
        monthly_services = ServiceEntry.objects.filter(
            service_center=service_center,
            service_date__gte=month_start
        )
        services_this_month = monthly_services.count()
        revenue_this_month = monthly_services.aggregate(
            total=Sum('price')
        )['total'] or 0
        
        # Overdue and upcoming services
        overdue_services = ServiceEntry.objects.filter(
            service_center=service_center,
            next_service_due_date__lt=today
        ).count()
        
        upcoming_date = today + timedelta(days=7)
        upcoming_services = ServiceEntry.objects.filter(
            service_center=service_center,
            next_service_due_date__range=[today, upcoming_date]
        ).count()
        
        # Top service types
        top_service_types = ServiceEntry.objects.filter(
            service_center=service_center,
            service_date__gte=month_start
        ).values('service_type').annotate(
            count=Count('service_type'),
            revenue=Sum('price')
        ).order_by('-count')[:5]
        
        # Recent services
        recent_services = ServiceEntry.objects.filter(
            service_center=service_center
        ).select_related('customer', 'vehicle', 'performed_by')[:10]
        
        summary_data = {
            'total_customers': total_customers,
            'total_vehicles': total_vehicles,
            'total_services': total_services,
            'services_this_month': services_this_month,
            'revenue_this_month': revenue_this_month,
            'overdue_services': overdue_services,
            'upcoming_services': upcoming_services,
            'top_service_types': list(top_service_types),
            'recent_services': ServiceEntrySerializer(recent_services, many=True).data
        }
        
        serializer = ServiceSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get revenue analytics for specified period",
        manual_parameters=[
            openapi.Parameter('period', openapi.IN_QUERY, description="Period: 'week', 'month', 'year'", type=openapi.TYPE_STRING),
        ],
        responses={200: openapi.Response(
            description="Revenue analytics data",
            examples={
                "application/json": {
                    "period": "month",
                    "total_revenue": "50000.00",
                    "service_count": 200,
                    "average_service_price": "250.00",
                    "daily_breakdown": []
                }
            }
        )}
    )
    @action(detail=False, methods=['get'])
    def revenue_analytics(self, request):
        service_center = request.user.service_center
        period = request.query_params.get('period', 'month')
        today = timezone.now().date()
        
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
        else:  # month
            start_date = today.replace(day=1)
        
        services = ServiceEntry.objects.filter(
            service_center=service_center,
            service_date__gte=start_date
        )
        
        total_revenue = services.aggregate(total=Sum('price'))['total'] or 0
        service_count = services.count()
        average_price = total_revenue / service_count if service_count > 0 else 0
        
        # Daily breakdown
        daily_breakdown = services.values('service_date').annotate(
            daily_revenue=Sum('price'),
            daily_count=Count('id')
        ).order_by('service_date')
        
        return Response({
            'period': period,
            'total_revenue': total_revenue,
            'service_count': service_count,
            'average_service_price': average_price,
            'daily_breakdown': list(daily_breakdown)
        })