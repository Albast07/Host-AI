# backend/users/permissions.py

from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Permiso que solo permite acceso a usuarios con rol 'admin'.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin


class IsAdminOrTeacher(BasePermission):
    """
    Permiso que permite acceso a usuarios con rol 'admin' o 'teacher'.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_admin or request.user.is_teacher)
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Permiso que permite acceso al propietario del objeto o a un admin.
    """
    def has_object_permission(self, request, view, obj):
        # Admin puede acceder a cualquier objeto
        if request.user.is_admin:
            return True
        
        # Verificar si el objeto tiene un atributo 'user' o si es el propio usuario
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Si el objeto es un usuario, verificar si es el mismo
        if hasattr(obj, 'id') and hasattr(request.user, 'id'):
            return obj.id == request.user.id
        
        return False
