from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from .pagination import PadraoPaginacao



from ..models import Produto, Categoria, Stock, TaxaIva, UnidadeMedida
from .serializers import (
    ProdutoSerializer, CategoriaSerializer, StockSerializer, 
    TaxaIvaSerializer, UnidadeMedidaSerializer
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
    pagination_class = PadraoPaginacao

class UnidadeMedidaViewSet(BaseViewSet):
    queryset = UnidadeMedida.objects.all()
    serializer_class = UnidadeMedidaSerializer
    search_fields = ['sigla', 'nome']
    ordering_fields = ['sigla', 'nome']
    pagination_class = PadraoPaginacao