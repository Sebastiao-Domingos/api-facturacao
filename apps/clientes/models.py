from django.db import models
from django.core.exceptions import ValidationError
from apps.organizacao.models.base import BaseModel
from apps.organizacao.models.localizacao import Endereco


class Cliente(BaseModel):
    TIPO_CLIENTE_CHOICES = [
        ('P', 'Particular (Pessoa Singular)'),
        ('E', 'Empresa (Organização/Pessoa Coletiva)'),
    ]

    tipo = models.CharField(max_length=1, choices=TIPO_CLIENTE_CHOICES, default='P')
    
    # Nome Comercial ou Nome Completo do Particular
    nome = models.CharField(max_length=255)
    
    # Dados fiscais cruciais para a AGT / SAF-T
    nif = models.CharField(max_length=20, unique=True, help_text="NIF do Cliente (9 dígitos para empresas)")
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    
    # Endereço Estruturado (Requisito Fiscal)
    endereco = models.OneToOneField(Endereco, on_delete=models.SET_NULL, null=True, related_name='clientes')


    # Campos Exclusivos para Organizações / Empresas
    razao_social = models.CharField(max_length=255, blank=True, null=True, help_text="Designação Social jurídica")
    website = models.URLField(blank=True, null=True)
    
    # Campos Exclusivos para Particulares
    bilhete_identidade = models.CharField(max_length=15, blank=True, null=True, unique=True, help_text="BI se for diferente do NIF")

    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    def clean(self):
        """
        Validações de integridade de acordo com o tipo de cliente antes de salvar.
        """
        super().clean()
        
        # Normalização de strings
        if self.nif:
            self.nif = self.nif.strip().upper()

        # Validações baseadas no tipo
        if self.tipo == 'E':
            if not self.razao_social:
                # Se for empresa e não introduzirem razão social, assume o nome comercial
                self.razao_social = self.nome
            # NIF de Empresa em Angola geralmente tem 9 dígitos numéricos
            if self.nif and len(self.nif) < 9:
                raise ValidationError({'nif': 'O NIF de uma Organização/Empresa deve conter pelo menos 9 caracteres.'})
        
        elif self.tipo == 'P':
            # Limpa campos de empresa se mudou de tipo
            self.razao_social = None
            self.website = None

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)