# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

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
]