from django.db import models
from .base import BaseModel

class Provincia(BaseModel):
    # Definimos o ID manualmente como UUID
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self): return self.nome

class Municipio(BaseModel):
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE, related_name='municipios')
    nome = models.CharField(max_length=100)

    def __str__(self): return f"{self.nome} ({self.provincia.nome})"

class Endereco(BaseModel):
    bairro = models.CharField(max_length=255)
    rua = models.CharField(max_length=255)
    ponto_referencia = models.TextField(blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.rua}, {self.bairro} - {self.municipio.nome}"