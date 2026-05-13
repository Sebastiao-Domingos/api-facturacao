from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import  viewsets

router = DefaultRouter()

router.register(r'produtos', viewsets.ProdutoViewSet , basename='produtos')
router.register(r'categorias', viewsets.CategoriaViewSet , basename='categorias')
router.register(r'stocks', viewsets.StockViewSet , basename='stocks')
router.register(r'taxa-iva', viewsets.TaxaIvaViewSet , basename='taxa-iva')
router.register(r'unidades-medida', viewsets.UnidadeMedidaViewSet , basename='unidades-medida')

urlpatterns = [
    path('', include(router.urls)),
]