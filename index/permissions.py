
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


class CanManageServiceCenterUsers(permissions.BasePermission):
    """
    Custom permission for managing users within service centers
    - Admin: Can manage all users
    - Center Admin: Can manage users in their service center only
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'centeradmin']
        )
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if user.role == 'admin':
            return True
        
        if user.role == 'centeradmin':
            # Center admin can manage users in their service center
            # But cannot delete other center admins
            if view.action == 'destroy' and obj.role == 'centeradmin':
                return False
            return obj.service_center == user.service_center
        
        return False

class CanChangeUserPassword(permissions.BasePermission):
    """
    Permission for changing user passwords
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Users can always change their own password
        if user == obj:
            return True
        
        # Admin can change anyone's password
        if user.role == 'admin':
            return True
        
        # Center admin can change passwords for staff in their service center
        if user.role == 'centeradmin':
            return (obj.service_center == user.service_center and obj.role == 'staff')
        
        return False