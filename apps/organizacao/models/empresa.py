from django.db import models
from .localizacao import Endereco
from .base import BaseModel


class Empresa(BaseModel):
    REGIME_CHOICES = [
        ('GERAL', 'Regime Geral'),
        ('SIMPLIFICADO', 'Regime Simplificado'),
        ('EXCLUSAO', 'Regime de Exclusão'),
    ]

    nome_fantasia = models.CharField(max_length=200)
    nif = models.CharField(max_length=20, unique=True)
    regime_tributario = models.CharField(max_length=20, choices=REGIME_CHOICES, default='GERAL')
    moeda_padrao = models.CharField(max_length=3, default='AOA')
    razao_social = models.CharField(max_length=200)
    logotipo = models.ImageField(upload_to='logos/', null=True, blank=True)
    endereco = models.OneToOneField(Endereco, on_delete=models.PROTECT, related_name='empresa')

    def __str__(self): return f"{self.nome_fantasia} ({self.nif})"

class Filial(BaseModel):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='filiais')
    nome = models.CharField(max_length=100)
    codigo_agt = models.CharField(max_length=50)
    e_sede = models.BooleanField(default=False)
    serie_documentos = models.CharField(max_length=10, default='A', help_text="Série de faturação (ex: A, B, 2026A)")  # Ex: Se a série for 'A', as faturas serão A/001, A/002...
    endereco = models.OneToOneField(Endereco, on_delete=models.SET_NULL, null=True, related_name='filial')

    def __str__(self): return f"{self.nome} ({self.empresa.nome_fantasia})"

    class Meta:
        unique_together = ('empresa', 'codigo_agt')