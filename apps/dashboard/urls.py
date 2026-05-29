# apps/dashboard/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import DashboardViewSet

router = DefaultRouter()
router.register(r'', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]