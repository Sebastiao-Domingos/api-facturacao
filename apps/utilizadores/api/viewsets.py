# apps/organizacao/viewsets.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import UserListSerializer, UserPasswordResetSerializer

User = get_user_model()

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        if not hasattr(user, 'funcionario'):
            return User.objects.none()
        funcionario = user.funcionario
        # ADMIN/SUPERADMIN vêem todos da sua empresa
        if funcionario.papel in ['ADMIN', 'SUPERADMIN']:
            empresa = funcionario.filial.empresa
            return User.objects.filter(funcionario__filial__empresa=empresa).distinct()
        # Outros papéis vêem apenas a si próprios
        return User.objects.filter(id=user.id)

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        try:
            target_user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"error": "Utilizador não encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        requesting_user = request.user

        # Verificar permissão: SUPERADMIN/ADMIN ou o próprio utilizador
        is_self = requesting_user == target_user
        can_change = (
            requesting_user.is_superuser or
            (hasattr(requesting_user, 'funcionario') and
             requesting_user.funcionario.papel in ['ADMIN', 'SUPERADMIN']) or
            is_self
        )

        if not can_change:
            return Response(
                {"error": "Não tem permissão para alterar a palavra-passe deste utilizador."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UserPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user.set_password(serializer.validated_data['new_password'])
        target_user.save()
        return Response(
            {"message": "Palavra-passe alterada com sucesso."},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        user = request.user
        serializer = UserPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"message": "Palavra-passe alterada com sucesso."})