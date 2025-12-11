# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework.routers import DefaultRouter
from .views import UserManagementViewSet, AdminServiceCenterUserViewSet


router = DefaultRouter()
router.register('users', UserManagementViewSet, basename='user-management')

# Create router for admin management  
admin_router = DefaultRouter()
admin_router.register('users', AdminServiceCenterUserViewSet, basename='admin-user-management')

# Define URL patterns
urlpatterns = [
    # Authentication
    path('auth/login/', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),

    # Service Center Management
    path('service-centers/register/', views.ServiceCenterRegistrationView.as_view(), name='service-center-register'),
    path('service-centers/', views.ServiceCenterListView.as_view(), name='service-center-list'),
    path('service-centers/<int:pk>/', views.ServiceCenterDetailView.as_view(), name='service-center-detail'),
    
    # Subscription Management
    path('service-centers/<int:service_center_id>/activate-subscription/', views.activate_subscription, name='activate-subscription'),
    path('service-centers/<int:service_center_id>/subscription-status/', views.subscription_status, name='subscription-status'),
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscription-list'),
    
    # User Management
    path('users/register/', views.UserRegistrationView.as_view(), name='user-register'),
    
    # License Keys
    path('license-keys/<str:license_key>/', views.license_key_info, name='license-key-info'),
        
    # Dashboard
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
     # SMS Frequency Update
    # path(
    #     'service-centers/<int:pk>/sms-frequency/', 
    #     views.SMSFrequencyUpdateView.as_view(), 
    #     name='service-center-sms-frequency-update'
    # ),
    
    # Alternative URL pattern if you want to update current user's service center SMS frequency
    path(
        'my-service-center/sms-frequency/', 
        views.SMSFrequencyUpdateView.as_view(), 
        {'pk': None},  # Will be handled in get_object method
        name='my-service-center-sms-frequency-update'
    ),
     path('users/', include(router.urls)),
    
    # Admin-only endpoints (for Super Admin)
    path('users/admin/', include(admin_router.urls)),
    path('auth/forgot-password/', views.forgot_password, name='forgot_password'),
    path('auth/reset_password/', views.reset_password, name='reset_password'),
]



"""
COMPLETE ENDPOINT DOCUMENTATION:

FOR CENTER ADMINS AND STAFF:
===========================
GET    /api/users/                           # List users in service center (with filtering)
POST   /api/users/                           # Create new staff (auto-assigns service center)
GET    /api/users/{id}/                      # Get specific user details
PUT    /api/users/{id}/                      # Update user information
PATCH  /api/users/{id}/                      # Partial update user
DELETE /api/users/{id}/                      # Delete staff user
POST   /api/users/{id}/change-password/      # Change user password
GET    /api/users/my_profile/                # Get current user profile
POST   /api/users/{id}/toggle_active/        # Toggle user active/inactive status
GET    /api/users/stats/                     # Get service center user statistics
GET    /api/users/my_service_center_users/   # Get all users in service center

Query Parameters for /api/users/:
- is_active=true/false  # Filter by active status
- role=staff/centeradmin  # Filter by role

FOR SUPER ADMIN ONLY:
====================
GET    /api/admin/users/                              # List all users (all service centers)
POST   /api/admin/users/                              # Create user (can specify any service center)
GET    /api/admin/users/{id}/                         # Get any user details
PUT    /api/admin/users/{id}/                         # Update any user
DELETE /api/admin/users/{id}/                         # Delete any user
POST   /api/admin/users/create_for_service_center/    # Create user for specific service center
GET    /api/admin/users/by_service_center/            # Get users grouped by service center
GET    /api/admin/users/all_stats/                    # Get comprehensive system statistics

ERROR HANDLING:
==============
All endpoints return proper HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request (validation errors)
- 403: Forbidden (permission denied)
- 404: Not Found
- 500: Internal Server Error

Example Error Response:
{
    "error": "You do not have permission to perform this action"
}

Example Success Response:
{
    "message": "User created successfully",
    "user": { ... user data ... }
}
"""