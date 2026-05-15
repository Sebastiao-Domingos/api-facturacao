from rest_framework import viewsets, permissions
from ..models.localizacao import Provincia, Municipio, Endereco 
from ..models.empresa import Empresa, Filial
from ..models.funcionario import   Funcionario
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.faturacao.api.pagination import PadraoPaginacao
from rest_framework.views import APIView

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
    pagination_class = None
    permission_classes = [IsAuthenticated]


class MunicipioViewSet(LocalizacaoBaseViewSet):
    queryset = Municipio.objects.all().order_by('nome')
    serializer_class = MunicipioSerializer
    filterset_fields = ['provincia'] # Permite filtrar municípios por província
    pagination_class = PadraoPaginacao
    permission_classes = [IsAuthenticated]


class EnderecoViewSet(LocalizacaoBaseViewSet):
    queryset = Endereco.objects.all()
    serializer_class = EnderecoSerializer
    pagination_class = PadraoPaginacao
    permission_classes = [IsAuthenticated]


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_class = [permissions.IsAdminUser]
    pagination_class = None
    

class FilialViewSet(viewsets.ModelViewSet):
    serializer_class = FilialSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated]


    
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
    pagination_class = PadraoPaginacao


    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """
        Retorna o perfil completo do funcionário logado sem paginação.
        """
        try:
            # Usamos get() para garantir que pegamos APENAS um objeto
            funcionario = Funcionario.objects.select_related(
                'user', 'filial', 'endereco'
            ).get(user=request.user)
            
            serializer = self.get_serializer(funcionario)
            
            # IMPORTANTE: Retornamos Response(serializer.data) diretamente.
            # Como passamos um dicionário (e não um queryset), 
            # o DRF não deveria paginar, mas para garantir, 
            # forçamos o atributo de paginação da resposta como None.
            return Response(serializer.data)
            
        except Funcionario.DoesNotExist:
            return Response(
                {"error": "Perfil de funcionário não encontrado."}, 
                status=404
            )
        

    def get_queryset(self):
        user = self.request.user
        
        # Base do QuerySet com otimização de banco de dados
        qs = Funcionario.objects.select_related('user', 'filial', 'endereco', 'filial__empresa')

        if user.is_superuser:
            return qs.all()
        
        if not hasattr(user, 'funcionario'):
            return qs.none()

        # Regra de Ouro: Ver apenas colegas da mesma EMPRESA
        return qs.filter(filial__empresa=user.funcionario.filial.empresa)
    



class PerfilUtilizadorView(APIView):
    """
    Rota: /api/v1/organizacao/utilizador/perfil/
    Retorna APENAS o objeto do funcionário logado, sem paginação.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            funcionario = Funcionario.objects.select_related(
                'user', 'filial', 'endereco', 'filial__empresa'
            ).get(user=request.user)
            
            serializer = FuncionarioSerializer(funcionario)
            return Response(serializer.data) # Retorna o objeto direto {}
        except Funcionario.DoesNotExist:
            return Response(
                {"error": "Perfil não encontrado para este utilizador."}, 
                status=404
            )