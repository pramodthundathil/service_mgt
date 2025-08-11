from django.shortcuts import render, get_object_or_404 
from index.permissions import IsAdmin, IsCenterAdmin






# ============= VIEWS =============

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch
from .serializers import *
from index.permissions import IsAdmin, IsCenterAdmin


class BrandUserViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for users to browse brands"""
    
    queryset = Brand.objects.prefetch_related('vehiclevariant_set')
    permission_classes = [permissions.IsAuthenticated]  # Or your user permission
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BrandDetailUserSerializer
        return BrandUserSerializer
        
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
    permission_classes = [permissions.IsAuthenticated]  # Or your user permission
    
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
    permission_classes = [IsAdmin]  # Admin only


class VehicleVariantAdminViewSet(viewsets.ModelViewSet):
    """Full CRUD viewset for admin vehicle variant management"""
    
    queryset = VehicleVariant.objects.select_related('brand')
    serializer_class = VehicleVariantAdminSerializer
    permission_classes = [IsAdmin]  # Admin only
    
    def get_queryset(self):
        """Allow admin filtering"""
        queryset = VehicleVariant.objects.select_related('brand')
        brand_id = self.request.query_params.get('brand', None)
        
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
            
        return queryset