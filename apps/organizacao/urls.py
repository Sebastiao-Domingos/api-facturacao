from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import viewsets

router = DefaultRouter()
router.register(r'provincias', viewsets.ProvinciaViewSet , basename='provincias')
router.register(r'municipios', viewsets.MunicipioViewSet , basename='municipios')
router.register(r'enderecos', viewsets.EnderecoViewSet , basename='enderecos')
router.register(r'empresas', viewsets.EmpresaViewSet , basename='empresas')
router.register(r'filiais', viewsets.FilialViewSet , basename='filiais')
router.register(r'funcionarios', viewsets.FuncionarioViewSet , basename='funcionarios')
router.register(r'funcionario/me', viewsets.FuncionarioViewSet , basename='funcionario-me')

urlpatterns = [
    path('', include(router.urls)),
]