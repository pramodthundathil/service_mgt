
from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsAuthenticatedForSwagger(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access this view.
    """
    def has_permission(self, request, view):
        # Check if the user is authenticated and has the 'admin' role
        return request.user and request.user.is_authenticated and request.user.role == 'admin' 

 
class IsCenterAdmin(permissions.BasePermission):
    """
    Allows access to users with role 'centeradmin' or 'admin'
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['centeradmin', 'admin']
        ) 
