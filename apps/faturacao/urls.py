from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import  viewsets
from apps.clientes.api import viewsets as clientes_viewsets


router = DefaultRouter()

router.register(r'produtos', viewsets.ProdutoViewSet , basename='produtos')
router.register(r'categorias', viewsets.CategoriaViewSet , basename='categorias')
router.register(r'stocks', viewsets.StockViewSet , basename='stocks')
router.register(r'taxa-iva', viewsets.TaxaIvaViewSet , basename='taxa-iva')
router.register(r'unidades-medida', viewsets.UnidadeMedidaViewSet , basename='unidades-medida')
router.register(r'movimentacoes', viewsets.MovimentacaoStockViewSet , basename='movimentacoes')
router.register(r'documentos', viewsets.DocumentoViewSet, basename='documento')
router.register(r'pagamentos', viewsets.PagamentoViewSet, basename='pagamento')
router.register(r'fornecedores', viewsets.FornecedorViewSet , basename='fornecedores')
router.register(r'compras', viewsets.CompraViewSet , basename='compras')
# No teu ficheiro de URLs onde tens os outros routers adiciona:

# Registo no teu router global existente
router.register(r'clientes', clientes_viewsets.ClienteViewSet, basename='clientes')

urlpatterns = [
    path('', include(router.urls)),
]
