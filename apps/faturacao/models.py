from django.db import models
from apps.organizacao.models.base import BaseModel
import random

def gerar_ean13_valido():
    """Gera um código EAN-13 interno com prefixo 27."""
    base = f"27{random.randint(1000000000, 9999999999)}"
    soma = sum(int(digit) * (3 if i % 2 else 1) for i, digit in enumerate(base))
    check_digit = (10 - (soma % 10)) % 10
    return f"{base}{check_digit}"

class Categoria(BaseModel):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome

class UnidadeMedida(BaseModel):
    sigla = models.CharField(max_length=5, unique=True) # Ex: UN, KG, LT
    nome = models.CharField(max_length=50) # Ex: Unidade, Quilograma, Litro

    class Meta:
        verbose_name = "Unidade de Medida"
        verbose_name_plural = "Unidades de Medida"

    def __str__(self):
        return f"{self.nome} ({self.sigla})"

class TaxaIva(BaseModel):
    codigo = models.CharField(max_length=10, unique=True) # Ex: IVA-14, IVA-0
    valor = models.DecimalField(max_digits=5, decimal_places=2) # Ex: 14.00
    descricao = models.CharField(max_length=100) # Ex: Taxa Padrão
    
    # Para conformidade AGT (Obrigatório para SAF-T em caso de isenção)
    motivo_isencao = models.CharField(max_length=255, blank=True, null=True)
    codigo_isencao_agt = models.CharField(max_length=10, blank=True, null=True) # Ex: M02

    class Meta:
        verbose_name = "Taxa de IVA"
        verbose_name_plural = "Taxas de IVA"

    def __str__(self):
        return f"{self.descricao} ({self.valor}%)"


class Produto(BaseModel):
    TIPO_CHOICES = [
        ('P', 'Produto'),
        ('S', 'Serviço'),
    ]

    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, default='P')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='produtos')
    
    # Chaves Estrangeiras para as novas tabelas
    unidade_medida = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT)
    taxa_iva = models.ForeignKey(TaxaIva, on_delete=models.PROTECT)
    
    # Preços e Códigos
    preco_venda = models.DecimalField(max_digits=12, decimal_places=2)
    codigo_barras = models.CharField(max_length=13, unique=True, blank=True, null=True)
    ref_interna = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    ativo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.codigo_barras:
            self.codigo_barras = gerar_ean13_valido() # Usando a função que criamos antes
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.nome




class Stock(BaseModel):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='stocks')
    filial = models.ForeignKey('organizacao.Filial', on_delete=models.CASCADE, related_name='stocks')
    
    quantidade = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=5.000)
    
    # Localização física dentro do armazém (opcional)
    corredor = models.CharField(max_length=50, blank=True, null=True)
    prateleira = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        # Um produto só pode ter um registo de stock por filial
        unique_together = ('produto', 'filial')
        verbose_name = "Stock por Filial"
        verbose_name_plural = "Stocks por Filial"

    def __str__(self):
        return f"{self.produto.nome} na {self.filial.nome}: {self.quantidade}"