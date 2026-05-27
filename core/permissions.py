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
    


class IsAdminOrSameFilial(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        if not hasattr(user, 'funcionario'):
            return False
        funcionario = user.funcionario
        if funcionario.papel == 'ADMIN':
            # ADMIN pode ver qualquer objeto que pertença à sua empresa
            # A lógica depende do objeto: Stock, Produto, Filial, etc.
            return True
        # Para outros papéis, verificar se o objeto pertence à sua filial
        if hasattr(obj, 'filial'):
            return obj.filial == funcionario.filial
        return False
    

# apps/organizacao/permissions.py
class IsAdminOrGestor(BasePermission):
    """
    Permissão para SUPERADMIN, ADMIN ou GESTOR.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if hasattr(request.user, 'funcionario'):
            papel = request.user.funcionario.papel
            return papel in ['SUPERADMIN', 'ADMIN', 'GESTOR']

        return False