from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from .pagination import PadraoPaginacao
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


from ..models import Produto, Categoria, Stock, TaxaIva, UnidadeMedida,MovimentacaoStock
from .serializers import (
    ProdutoSerializer, CategoriaSerializer, StockSerializer, 
    TaxaIvaSerializer, UnidadeMedidaSerializer, MovimentacaoStockSerializer,ExecutarMovimentacaoSerializer
)


class BaseViewSet(viewsets.ModelViewSet):
    """Classe base para evitar repetição de permissões"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

class ProdutoViewSet(BaseViewSet):
    queryset = Produto.objects.select_related('categoria', 'taxa_iva', 'unidade_medida').all()
    serializer_class = ProdutoSerializer
    search_fields = ['nome', 'codigo_barras', 'ref_interna']
    filterset_fields = ['categoria', 'tipo', 'ativo']
    ordering_fields = ['nome']
    pagination_class = PadraoPaginacao

class StockViewSet(viewsets.ReadOnlyModelViewSet): # Geralmente stock não se apaga, apenas se consulta ou ajusta
    queryset = Stock.objects.select_related('produto', 'filial').all()
    serializer_class = StockSerializer
    filterset_fields = ['filial', 'produto']
    ordering_fields = ['quantidade']
    pagination_class = PadraoPaginacao


    @action(detail=True, methods=['post'], url_path='movimentar')
    def movimentar_stock(self, request, pk=None):
        stock_filial = self.get_object()
        
        # 1. Passamos os dados recebidos para o Serializer de Execução/Validação
        serializer = ExecutarMovimentacaoSerializer(
            data=request.data, 
            context={'stock_filial': stock_filial}
        )
        
        if serializer.is_valid():
            # 2. O método .save() agora retorna a instância da MovimentacaoStock criada
            movimentacao = serializer.save(
                stock_filial=stock_filial,
                operador=request.user
            )
            
            # 3. Passamos essa instância pelo Serializer de Leitura para devolver o JSON perfeito
            response_serializer = MovimentacaoStockSerializer(movimentacao)
            
            # 4. Retornamos os dados serializados da movimentação com tipo, quantidade e operador
            return Response(
                response_serializer.data, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class CategoriaViewSet(BaseViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    search_fields = ['nome']
    ordering_fields = ['nome']
    pagination_class = PadraoPaginacao

class TaxaIvaViewSet(BaseViewSet):
    queryset = TaxaIva.objects.all()
    serializer_class = TaxaIvaSerializer
    search_fields = ['codigo']
    ordering_fields = ['codigo']
    pagination_class = None

class UnidadeMedidaViewSet(BaseViewSet):
    queryset = UnidadeMedida.objects.all()
    serializer_class = UnidadeMedidaSerializer
    search_fields = ['sigla', 'nome']
    ordering_fields = ['sigla', 'nome']
    pagination_class = None




class MovimentacaoStockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint apenas de leitura para o histórico de auditoria.
    As movimentações devem ser geradas por Triggers ou Services no Back-end.
    """
    queryset = MovimentacaoStock.objects.all()
    serializer_class = MovimentacaoStockSerializer
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['stock_filial'] # Crucial para o Next.js filtrar: /api/movimentacoes/?stock_filial=id_aqui
    ordering_fields = ['created_at']
    pagination_class = PadraoPaginacao

