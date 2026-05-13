from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.organizacao.api.auth import MyTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Interface do DRF para navegar na API pelo browser (útil para testes)
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    
    # Rotas de Autenticação JWT
    path('api/v1/auth/login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Módulos do Sistema
    path('api/v1/organizacao/', include('apps.organizacao.urls')),

    path('api/v1/faturacao/', include('apps.faturacao.urls')),
]

# ESTA PARTE É O QUE FALTA: 
# Permite que o Django sirva os logótipos das empresas e fotos dos funcionários em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)