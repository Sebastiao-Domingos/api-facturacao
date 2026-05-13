from rest_framework import viewsets
from ..models import Produto, Categoria, Stock, TaxaIva, UnidadeMedida
from .serializers import (
    ProdutoSerializer, CategoriaSerializer, StockSerializer, 
    TaxaIvaSerializer, UnidadeMedidaSerializer
)

class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    



class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer


class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer


class TaxaIvaViewSet(viewsets.ModelViewSet):
    queryset = TaxaIva.objects.all()
    serializer_class = TaxaIvaSerializer

class UnidadeMedidaViewSet(viewsets.ModelViewSet):
    queryset = UnidadeMedida.objects.all()
    serializer_class = UnidadeMedidaSerializer

# Cria ViewSets semelhantes para Categoria, TaxaIva e UnidadeMedida