from rest_framework import viewsets, permissions
from ..models.localizacao import Provincia, Municipio, Endereco 
from ..models.empresa import Empresa, Filial
from ..models.funcionario import   Funcionario
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.faturacao.api.pagination import PadraoPaginacao
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import viewsets, status
from .serializers import (
    ProvinciaSerializer, MunicipioSerializer, EnderecoSerializer,
    EmpresaSerializer, FilialSerializer, FuncionarioSerializer,FuncionarioDetailSerializer,FuncionarioListSerializer,
    FuncionarioResumidoSerializer, FilialDetailSerializer, FilialResumoSerializer,StockProdutoSerializer
)
from rest_framework.exceptions import PermissionDenied
# apps/empresa/serializers/filial_serializer.py

from django.db.models import Count, Sum, F  # ← Adicionar F aqui

# Resto do código...


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
    """
    CRUD para Filiais
    - GET /filiais/ - Listagem resumida
    - GET /filiais/{id}/ - Detalhe completo (com funcionários e stocks opcionais)
    - GET /filiais/{id}/resumo/ - Resumo com métricas
    - GET /filiais/{id}/funcionarios/ - Lista de funcionários
    - GET /filiais/{id}/stocks/ - Lista de stocks
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['empresa', 'e_sede', 'ativo']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Filial.objects.none()
        
        # Base queryset com otimizações
        qs = Filial.objects.select_related('empresa', 'endereco')
        
        # SUPERADMIN vê todas
        if user.is_superuser:
            return qs
        
        if not hasattr(user, 'funcionario'):
            return qs.none()
        
        funcionario = user.funcionario
        
        if funcionario.papel == 'SUPERADMIN':
            return qs
        
        # ADMIN, GESTOR vêem apenas filiais da sua empresa
        if funcionario.papel in ['ADMIN', 'GESTOR']:
            return qs.filter(empresa=funcionario.filial.empresa)
        
        # OPERADOR vê apenas sua filial
        if funcionario.papel == 'OPERADOR':
            return qs.filter(id=funcionario.filial.id)
        
        return qs.none()
    
    def get_serializer_class(self):
        """Retorna o serializer adequado para cada ação"""
        if self.action == 'list':
            return FilialResumoSerializer
        if self.action == 'retrieve':
            return FilialDetailSerializer
        if self.action in ['resumo', 'meus_dados']:
            return FilialResumoSerializer
        return FilialSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /filiais/{id}/
        Suporta query params:
        - ?include_funcionarios=true  (inclui lista de funcionários)
        - ?include_stocks=true        (inclui lista de stocks)
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='resumo')
    def resumo(self, request, pk=None):
        """Retorna um resumo da filial com métricas principais"""
        instance = self.get_object()
        
        data = {
            'id': str(instance.id),
            'nome': instance.nome,
            'codigo_agt': instance.codigo_agt,
            'e_sede': instance.e_sede,
            'ativo': instance.ativo,
            'empresa_nome': instance.empresa.nome_fantasia,
            'total_funcionarios': instance.funcionarios.count(),
            'funcionarios_ativos': instance.funcionarios.filter(ativo=True).count(),
            'total_produtos_stock': instance.stocks.count(),
            'produtos_esgotados': instance.stocks.filter(quantidade=0).count(),
            'produtos_stock_minimo': instance.stocks.filter(
                quantidade__lte=F('stock_minimo'), quantidade__gt=0
            ).count(),
            'created_at': instance.created_at,
        }
        
        return Response(data)
    
    @action(detail=True, methods=['get'], url_path='funcionarios')
    def listar_funcionarios(self, request, pk=None):
        """Retorna a lista de funcionários da filial"""
        instance = self.get_object()
        
        funcionarios = instance.funcionarios.select_related('user').all()
        
        # Paginação opcional
        page = self.paginate_queryset(funcionarios)
        if page is not None:
            serializer = FuncionarioResumidoSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = FuncionarioResumidoSerializer(funcionarios, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='stocks')
    def listar_stocks(self, request, pk=None):
        """Retorna a lista de stocks da filial"""
        instance = self.get_object()
        
        stocks = instance.stocks.select_related('produto', 'produto__categoria').all()
        
        # Filtros opcionais
        categoria = request.query_params.get('categoria')
        if categoria:
            stocks = stocks.filter(produto__categoria_id=categoria)
        
        status_filter = request.query_params.get('status')
        if status_filter == 'esgotado':
            stocks = stocks.filter(quantidade=0)
        elif status_filter == 'minimo':
            stocks = stocks.filter(quantidade__lte=F('stock_minimo'), quantidade__gt=0)
        
        # Paginação
        page = self.paginate_queryset(stocks)
        if page is not None:
            serializer = StockProdutoSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = StockProdutoSerializer(stocks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='meus-dados')
    def meus_dados(self, request):
        """Retorna os dados da filial do funcionário logado"""
        user = request.user
        
        if not hasattr(user, 'funcionario'):
            return Response(
                {"error": "Usuário não tem perfil de funcionário."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        filial = user.funcionario.filial
        serializer = FilialDetailSerializer(filial, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='ativar')
    def ativar(self, request, pk=None):
        """Ativa uma filial"""
        filial = self.get_object()
        filial.ativo = True
        filial.save()
        return Response({"message": "Filial activada com sucesso."})
    
    @action(detail=True, methods=['post'], url_path='desativar')
    def desativar(self, request, pk=None):
        """Desativa uma filial"""
        filial = self.get_object()
        filial.ativo = False
        filial.save()
        return Response({"message": "Filial desactivada com sucesso."})
    
    def perform_create(self, serializer):
        """Criação apenas para SUPERADMIN"""
        user = self.request.user
        
        if not hasattr(user, 'funcionario'):
            raise PermissionDenied("Usuário não tem perfil de funcionário.")
        
        if user.funcionario.papel != 'SUPERADMIN':
            raise PermissionDenied("Apenas SUPERADMIN pode criar filiais.")
        
        # Pega a empresa do funcionário logado
        empresa = user.funcionario.filial.empresa
        serializer.save(empresa=empresa)


class FuncionarioViewSet(viewsets.ModelViewSet):
    """
    CRUD completo para Funcionários
    """
    queryset = Funcionario.objects.select_related(
        'user', 'filial', 'endereco', 'filial__empresa'
    ).all()
    
    permission_classes = [IsAuthenticated]
    pagination_class = PadraoPaginacao
    
    # Filtros corretos (apenas campos do banco)
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['filial', 'papel', 'ativo', 'filial__empresa']
    search_fields = ['user__first_name', 'user__last_name', 'bi', 'user__email', 'telemovel']
    ordering_fields = ['created_at', 'user__first_name', 'papel', 'ativo']
    ordering = ['-created_at']  # Ordem padrão

    def get_serializer_class(self):
        """Usa o mesmo serializer para todas as ações"""
        return FuncionarioSerializer  # ← Remove o FuncionarioDetailSerializer
    
    # Opcional: mantém o list serializer para performance
    def get_serializer_class(self):
        if self.action == 'list':
            return FuncionarioListSerializer
        return FuncionarioSerializer  # ← Para retrieve, create, update

    def get_queryset(self):
        """Aplica regras de permissão baseadas no papel do usuário"""
        user = self.request.user
        
        # SUPERADMIN vê tudo
        if user.is_superuser:
            return self.queryset
        
        # Usuário sem perfil de funcionário
        if not hasattr(user, 'funcionario'):
            return self.queryset.none()
        
        funcionario = user.funcionario
        
        # ADMIN da empresa vê todos da mesma empresa
        if funcionario.papel == 'ADMIN':
            return self.queryset.filter(filial__empresa=funcionario.filial.empresa)
        
        # GESTOR vê apenas funcionários da sua filial
        if funcionario.papel == 'GESTOR':
            return self.queryset.filter(filial=funcionario.filial)
        
        # OPERADOR e CONTABILISTA vêem apenas o próprio
        return self.queryset.filter(id=funcionario.id)

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Retorna o perfil do funcionário logado"""
        try:
            funcionario = self.queryset.get(user=request.user)
            serializer = FuncionarioDetailSerializer(funcionario)
            return Response(serializer.data)
        except Funcionario.DoesNotExist:
            return Response(
                {"error": "Perfil de funcionário não encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='ativar')
    def ativar(self, request, pk=None):
        """Reativa um funcionário"""
        funcionario = self.get_object()
        funcionario.ativo = True
        
        # Reativa o User também
        if funcionario.user:
            funcionario.user.is_active = True
            funcionario.user.save()
        
        funcionario.save()
        return Response({"message": "Funcionário activado com sucesso."})

    @action(detail=True, methods=['post'], url_path='desativar')
    def desativar(self, request, pk=None):
        """Desativa um funcionário (soft delete)"""
        funcionario = self.get_object()
        funcionario.ativo = False
        
        # Desativa o User também
        if funcionario.user:
            funcionario.user.is_active = False
            funcionario.user.save()
        
        funcionario.save()
        return Response({"message": "Funcionário desactivado com sucesso."})

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