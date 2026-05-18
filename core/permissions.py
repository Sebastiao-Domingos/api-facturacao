# apps/core/permissions.py

from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """
    Permissão para verificar se o usuário é SUPERADMIN
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verifica se é superuser do Django
        if request.user.is_superuser:
            return True
        
        # Verifica se tem perfil de funcionário e papel SUPERADMIN
        if hasattr(request.user, 'funcionario'):
            return request.user.funcionario.papel == 'SUPERADMIN'
        
        return False
    
    def has_object_permission(self, request, view, obj):
        # Mesma lógica para objetos específicos
        return self.has_permission(request, view)


class IsAdminOrSuperAdmin(BasePermission):
    """
    Permissão para ADMIN ou SUPERADMIN
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if hasattr(request.user, 'funcionario'):
            papel = request.user.funcionario.papel
            return papel in ['SUPERADMIN', 'ADMIN']
        
        return False