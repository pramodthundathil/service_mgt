from django.urls import path
from . import views
from .views import (
    PaymentPlanListView, PaymentTransactionListView, 
    SubscriptionHistoryListView, ServiceCenterPaymentStatusListView,
    PaymentPlanDashboardListView, PaymentPlanDashboardCreateView, 
    PaymentPlanDashboardUpdateView, PaymentPlanDashboardDeleteView
)

# Payment and subscription URL patterns
urlpatterns = [
    # Payment Plans (API)
    path('plans/', PaymentPlanListView.as_view(), name='payment-plans'),

    # Payment Plans (HTML)
    path('admin/plans/', PaymentPlanDashboardListView.as_view(), name='payment-plans-list'),
    path('admin/plans/add/', PaymentPlanDashboardCreateView.as_view(), name='payment-plan-add'),
    path('admin/plans/<int:pk>/edit/', PaymentPlanDashboardUpdateView.as_view(), name='payment-plan-edit'),
    path('admin/plans/<int:pk>/delete/', PaymentPlanDashboardDeleteView.as_view(), name='payment-plan-delete'),
    
    # Payment Operations
    path('create-order/', views.create_payment_order, name='create-payment-order'),
    path('verify-payment/', views.verify_payment_and_extend, name='verify-payment'),
    
    # Subscription Management
    path('subscription/status/', views.get_subscription_status, name='subscription-status'),
    path('subscription/history/', SubscriptionHistoryListView.as_view(), name='subscription-history'),
    
    # Transaction Management
    path('transactions/', PaymentTransactionListView.as_view(), name='payment-transactions'),
    
    # Access Control
    path('check-access/', views.check_access_permission, name='check-access'),
    
    # Admin Operations
    path('admin/dashboard/', views.payment_dashboard_stats, name='payment-dashboard'),
    path('admin/service-centers/', ServiceCenterPaymentStatusListView.as_view(), name='admin-service-centers'),
    path('admin/disable-center/', views.disable_service_center, name='disable-service-center'),
    path('admin/enable-center/', views.enable_service_center, name='enable-service-center'),
]