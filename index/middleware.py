# middleware.py - Create this file in your app directory
"""
Middleware to check subscription status and control access
"""

from django.http import JsonResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
import json


class SubscriptionAccessMiddleware(MiddlewareMixin):
    """
    Middleware to check subscription status and control API access
    """
    
    # URLs that should always be accessible
    EXEMPT_URLS = [
        '/api/auth/login/',
        '/subscription/payment/plans/',
        '/subscription/payment/create-order/',
        '/subscription/payment/verify-payment/',
        '/subscription/payment/check-access/',
        '/subscription/payment/subscription/status/',
        '/admin/',
        '/swagger/',
        '/redoc/',
        '/subscription/schema/',
    ]
    
    # URLs that require payment if subscription expired
    PAYMENT_REQUIRED_URLS = [
        '/subscription/service/',  # Add your main service URLs here
        '/subscription/customers/',
        '/subscription/inventory/',
        '/subscription/reports/',
    ]

    def process_request(self, request):
        # Skip non-API requests
        if not request.path.startswith('/subscription/'):
            return None
            
        # Skip exempt URLs
        if any(request.path.startswith(url) for url in self.EXEMPT_URLS):
            return None
            
        # Skip if user is not authenticated
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
            
        # Admin users have unlimited access
        if request.user.role == 'admin':
            return None
            
        # Check if URL requires subscription
        requires_subscription = any(
            request.path.startswith(url) for url in self.PAYMENT_REQUIRED_URLS
        )
        
        if not requires_subscription:
            return None
            
        # Check user's service center subscription
        if not request.user.service_center:
            return JsonResponse({
                'success': False,
                'message': 'User not associated with any service center',
                'error_code': 'NO_SERVICE_CENTER'
            }, status=403)
            
        service_center = request.user.service_center
        
        # Check if service center can access
        if not service_center.can_access_service():
            if request.user.role == 'centeradmin':
                return JsonResponse({
                    'success': False,
                    'message': 'Subscription expired. Please renew to continue accessing the service.',
                    'error_code': 'SUBSCRIPTION_EXPIRED',
                    'requires_payment': True,
                    'subscription_status': service_center.get_subscription_status()
                }, status=402)  # Payment Required
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Access denied. Your service center subscription has expired. Please contact your center admin.',
                    'error_code': 'ACCESS_DENIED',
                    'requires_payment': False
                }, status=403)
        
        return None


