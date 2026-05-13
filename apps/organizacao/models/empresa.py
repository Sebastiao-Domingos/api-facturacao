from django.db import models
from .localizacao import Endereco
from .base import BaseModel


class Empresa(BaseModel):
    nome_fantasia = models.CharField(max_length=200)
    razao_social = models.CharField(max_length=200)
    nif = models.CharField(max_length=20, unique=True)
    logotipo = models.ImageField(upload_to='logos/', null=True, blank=True)
    endereco = models.OneToOneField(Endereco, on_delete=models.SET_NULL, null=True, related_name='empresa')

    def __str__(self): return self.nome_fantasia

class Filial(BaseModel):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='filiais')
    nome = models.CharField(max_length=100)
    codigo_agt = models.CharField(max_length=50)
    e_sede = models.BooleanField(default=False)
    endereco = models.OneToOneField(Endereco, on_delete=models.SET_NULL, null=True, related_name='filial')

    def __str__(self): return f"{self.nome} ({self.empresa.nome_fantasia})"

    class Meta:
        unique_together = ('empresa', 'codigo_agt')