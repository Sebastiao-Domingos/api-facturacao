from rest_framework import viewsets, permissions
from ..models.localizacao import Provincia, Municipio, Endereco 
from ..models.empresa import Empresa, Filial
from ..models.funcionario import   Funcionario
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    ProvinciaSerializer, MunicipioSerializer, EnderecoSerializer,
    EmpresaSerializer, FilialSerializer, FuncionarioSerializer
)

class LocalizacaoBaseViewSet(viewsets.ModelViewSet):
    """ViewSet Base para evitar repetição de permissões"""
    permission_classes = [permissions.IsAuthenticated]

class ProvinciaViewSet(LocalizacaoBaseViewSet):
    queryset = Provincia.objects.all().order_by('nome')
    serializer_class = ProvinciaSerializer

class MunicipioViewSet(LocalizacaoBaseViewSet):
    queryset = Municipio.objects.all().order_by('nome')
    serializer_class = MunicipioSerializer
    filterset_fields = ['provincia'] # Permite filtrar municípios por província

class EnderecoViewSet(LocalizacaoBaseViewSet):
    queryset = Endereco.objects.all()
    serializer_class = EnderecoSerializer

class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_class = [permissions.IsAdminUser]
    

class FilialViewSet(viewsets.ModelViewSet):
    serializer_class = FilialSerializer
    
    def get_queryset(self):
        # Filtro de segurança: Funcionários só vêem filiais da sua própria empresa
        user = self.request.user
        if user.is_superuser:
            return Filial.objects.all()
        return Filial.objects.filter(empresa=user.funcionario.filial.empresa)



class FuncionarioViewSet(viewsets.ModelViewSet):
    queryset = Funcionario.objects.all()
    serializer_class = FuncionarioSerializer
    filter_fields = ['filial', 'papel', 'ativo', 'created_at', 'updated_at' , 'filial__empresa' , "nome_completo" , "nif"] # Permite filtrar funcionários por filial, papel e status ativo
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """
        Retorna o perfil completo do funcionário logado.
        """
        try:
            # O request.user já é o teu CustomUser com UUID
            funcionario = request.user.funcionario 
            serializer = self.get_serializer(funcionario)
            return Response(serializer.data)
        except Funcionario.DoesNotExist:
            return Response(
                {"error": "Este utilizador não tem um perfil de funcionário associado."}, 
                status=404
            )
        
    
    def get_queryset(self):
        user = self.request.user
        
        # Se for Superuser do Django, vê tudo
        if user.is_superuser:
            return Funcionario.objects.all()
        
        # Se não tiver perfil de funcionário, não vê nada
        if not hasattr(user, 'funcionario'):
            return Funcionario.objects.none()

        # Um funcionário normal só vê os colegas da mesma Empresa
        # (Ou apenas a si próprio, dependendo da tua regra de negócio)
        return Funcionario.objects.filter(
            filial__empresa=user.funcionario.filial.empresa
        )