# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    BrandReadOnlyViewSet, VehicleVariantReadOnlyViewSet, CustomerViewSet,
    VehicleOnServiceViewSet, ServiceEntryViewSet, DashboardViewSet
)

# User router (read-only)
user_router = DefaultRouter()
user_router.register(r'brands', views.BrandUserViewSet, basename='brand')
user_router.register(r'variants', views.VehicleVariantUserViewSet, basename='variant')

user_router.register(r'brands', BrandReadOnlyViewSet, basename='brands')
user_router.register(r'vehicle-variants', VehicleVariantReadOnlyViewSet, basename='vehicle-variant')

# CRUD viewsets for main entities
user_router.register(r'customers', CustomerViewSet, basename='customer')
user_router.register(r'vehicles', VehicleOnServiceViewSet, basename='vehicle')
user_router.register(r'services', ServiceEntryViewSet, basename='service')

# Dashboard and analytics
user_router.register(r'dashboard', DashboardViewSet, basename='dashboard')


# Admin router (full CRUD)
admin_router = DefaultRouter()
admin_router.register(r'brands', views.BrandAdminViewSet, basename='admin-brand')
admin_router.register(r'variants', views.VehicleVariantAdminViewSet, basename='admin-variant')


urlpatterns = [
    # User endpoints (read-only)
    path('user/interactions/', include(user_router.urls)),
    
    # Admin endpoints (full CRUD)
    path('admin/interactions/', include(admin_router.urls)),
]

# This creates the following endpoints:

# USER ENDPOINTS (Read-only):
# GET /api/brands/ - List all brands
# GET /api/brands/{id}/ - Get brand details with variants
# GET /api/brands/{id}/variants/ - Get variants for specific brand
# GET /api/variants/ - List all variants (supports ?brand=id&body_type=sedan filtering)
# GET /api/variants/{id}/ - Get variant details

# ADMIN ENDPOINTS (Full CRUD):
# GET /api/admin/brands/ - List brands (admin view)
# POST /api/admin/brands/ - Create new brand
# GET /api/admin/brands/{id}/ - Get brand details (admin view)
# PUT /api/admin/brands/{id}/ - Update brand
# PATCH /api/admin/brands/{id}/ - Partial update brand
# DELETE /api/admin/brands/{id}/ - Delete brand

# GET /api/admin/variants/ - List variants (admin view)
# POST /api/admin/variants/ - Create new variant
# GET /api/admin/variants/{id}/ - Get variant details (admin view)
# PUT /api/admin/variants/{id}/ - Update variant
# PATCH /api/admin/variants/{id}/ - Partial update variant
# DELETE /api/admin/variants/{id}/ - Delete variant