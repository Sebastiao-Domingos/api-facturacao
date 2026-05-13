# apps/organizacao/models/base.py (ou dentro de cada ficheiro de model)
from django.db import models
import uuid

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        abstract = True  # Isto diz ao Django para não criar uma tabela para este modelo
        ordering = ['-created_at']  # Ordena por data de criação decrescente por padrão