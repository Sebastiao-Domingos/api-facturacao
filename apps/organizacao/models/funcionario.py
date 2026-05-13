from django.db import models
from .empresa import Filial
from .localizacao import Endereco
from .base import BaseModel
from django.conf import settings

class Funcionario(BaseModel):
    ROLES = (
        ('SUPERADMIN', 'Administrador'),
        ('GESTOR', 'Gestor de Filial'),
        ('OPERADOR', 'Operador de Caixa'),
        ('CONTABILISTA', 'Contabilista'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='funcionario')
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='funcionarios')
    endereco = models.OneToOneField(Endereco, on_delete=models.SET_NULL, null=True, related_name='funcionario_perfil')
    bi = models.CharField(max_length=20, unique=True)
    cargo = models.CharField(max_length=100)
    telemovel = models.CharField(max_length=15, unique=True)
    papel = models.CharField(max_length=20, choices=ROLES, default='OPERADOR')
    ativo = models.BooleanField(default=True)

    def __str__(self): return self.user.get_full_name()

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'