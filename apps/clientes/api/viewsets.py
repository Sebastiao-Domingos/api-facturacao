from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from ..models import Cliente
from .serializers import ClienteSerializer

from rest_framework.permissions import IsAuthenticated
from apps.faturacao.api.pagination import PadraoPaginacao

class BaseViewSet(viewsets.ModelViewSet):
    """Classe base para evitar repetição de permissões"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

class ClienteViewSet(BaseViewSet):
    """
    CRUD Completo para Gestão de Clientes (Particulares e Organizações).
    Suporta paginação, ordenação e filtros de auditoria fiscal.
    """
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    pagination_class = PadraoPaginacao

    
    # Motores de filtragem corporativa
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Permite filtrar na URL exatamente por: ?tipo=P ou ?ativo=true
    filterset_fields = ['tipo', 'ativo',"endereco"]
    
    # Permite pesquisar na barra global por Nome, NIF ou BI
    search_fields = ['nome', 'nif', 'bilhete_identidade', 'razao_social']
    
    # Ordenação padrão
    ordering_fields = ['nome', 'created_at']
    ordering = ['nome']


    def destroy(self, request, *args, **kwargs):
        """
        Sobrescreve a remoção física. Num ERP de Faturação, se o cliente 
        já tiver uma fatura emitida, a remoção física corrompe o SAF-T.
        Fazemos Soft Delete (Inativar) ou validação de segurança.
        """
        cliente = self.get_object()
        
        # Regra de Segurança: Em vez de apagar do banco, inativamos para preservar histórico fiscal
        cliente.ativo = False
        cliente.save()
        
        return Response(
            {"detail": f"O cliente '{cliente.nome}' foi desativado com sucesso para preservar o histórico de transações."},
            status=status.HTTP_200_OK
        )