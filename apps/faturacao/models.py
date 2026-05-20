from django.db import models
from apps.organizacao.models.base import BaseModel
import random, os
from PIL import Image
from django.core.files.base import ContentFile
from django.conf import settings
from io import BytesIO
# No topo do arquivo, adicione:
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction



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
    imagem = models.ImageField(upload_to='produtos/%Y/%m/', null=True, blank=True)
    thumbnail = models.ImageField(upload_to='produtos/thumbs/%Y/%m/', editable=False, null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='produtos')
    
    # Chaves Estrangeiras para as novas tabelas
    unidade_medida = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT)
    taxa_iva = models.ForeignKey(TaxaIva, on_delete=models.PROTECT)
    
    # Preços e Códigos
    preco_venda = models.DecimalField(max_digits=12, decimal_places=2)
    codigo_barras = models.CharField(max_length=13, unique=True, blank=True, null=True)
    ref_interna = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    ativo = models.BooleanField(default=True)
    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.codigo_barras:
            self.codigo_barras = gerar_ean13_valido() # Usando a função que criamos antes

        if self.imagem and not self.thumbnail:
            self.thumbnail = self.make_thumbnail(self.imagem)
        
        super().save(*args, **kwargs)



    def make_thumbnail(self, image, size=(300, 300)):
        """Gera uma miniatura proporcional convertendo RGBA para RGB se necessário."""
        img = Image.open(image)
        
        # Se a imagem tiver canal de transparência (RGBA), converte para RGB
        if img.mode in ("RGBA", "P"):
            img = img.convert('RGB')
        else:
            img = img.convert('RGB') # Garante que está em RGB para o JPEG

        img.thumbnail(size)
        
        thumb_io = BytesIO()
        # Agora podemos salvar como JPEG com segurança
        img.save(thumb_io, 'JPEG', quality=85) 
        
        name = os.path.basename(image.name)
        # Garante que a extensão do ficheiro no thumbnail seja .jpg para condizer com o formato
        name = os.path.splitext(name)[0] + ".jpg"
        
        return ContentFile(thumb_io.getvalue(), name=name)




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


class MovimentacaoStock(BaseModel):
    TIPO_MOVIMENTACAO = [
        ('E', 'Entrada (Compra/Ajuste Positivo)'),
        ('S', 'Saída (Venda/Quebra/Ajuste Negativo)'),
    ]

    # Aponta diretamente para o par Produto-Filial (Teu model Stock)
    stock_filial = models.ForeignKey(
        Stock, 
        on_delete=models.CASCADE, 
        related_name='movimentacoes'
    )
    tipo = models.CharField(max_length=1, choices=TIPO_MOVIMENTACAO)
    
    # Herda as 3 casas decimais que definiste no model Stock
    quantidade = models.DecimalField(max_digits=12, decimal_places=3)
    
    # Justificação (Obrigatório para auditoria fiscal da AGT em ajustes manuais)
    origem_destino = models.CharField(
        max_length=255, 
        help_text="Ex: FT-2026/001 (Venda), Entrada de Fornecedor, Ajuste de Inventário"
    )
    
    # Rastreabilidade: Quem fez a movimentação?
    operador = models.ForeignKey(
       settings.AUTH_USER_MODEL, # Ajusta para o teu Custom User Model se tiveres um
        on_delete=models.PROTECT,
        related_name='movimentacoes_stock'
    )

    class Meta:
        verbose_name = "Movimentação de Stock"
        verbose_name_plural = "Movimentações de Stock"
        ordering = ['-created_at'] # As mais recentes aparecem primeiro

    def __str__(self):
        return f"{self.stock_filial.produto.nome} ({self.stock_filial.filial.nome}) - {self.tipo}: {self.quantidade}"
    







# Adicione ao final do arquivo apps/faturacao/models.py

class SerieDocumento(BaseModel):
    """Série numérica para documentos fiscais (por filial e tipo)"""
    TIPO_CHOICES = [
        ('FACTURA', 'Factura'),
        ('PRO_FORMA', 'Pro-Forma'),
        ('NOTA_CREDITO', 'Nota de Crédito'),
        ('NOTA_DEBITO', 'Nota de Débito'),
        ('RECIBO', 'Recibo'),
    ]
    
    filial = models.ForeignKey('organizacao.Filial', on_delete=models.PROTECT, related_name='series')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    prefixo = models.CharField(max_length=10, help_text="Ex: FAT, PRO, NC, ND, REC")
    numero_atual = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('filial', 'tipo')
        verbose_name = "Série de Documento"
        verbose_name_plural = "Séries de Documentos"
    
    def __str__(self):
        return f"{self.filial.nome} - {self.get_tipo_display()} ({self.prefixo})"
    
    def proximo_numero(self):
        """Gera o próximo número sequencial para o documento"""
        with transaction.atomic():
            self.numero_atual += 1
            self.save()
            return self.numero_atual


class Documento(BaseModel):
    """Documento Fiscal (Factura, Pro-Forma, Nota de Crédito, Recibo)"""
    TIPO_CHOICES = [
        ('FACTURA', 'Factura'),
        ('PRO_FORMA', 'Pro-Forma'),
        ('NOTA_CREDITO', 'Nota de Crédito'),
        ('NOTA_DEBITO', 'Nota de Débito'),
        ('RECIBO', 'Recibo'),
    ]
    
    ESTADO_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('EMITIDA', 'Emitida'),
        ('PARCIALMENTE_PAGA', 'Parcialmente Paga'),
        ('PAGA', 'Paga'),
        ('ANULADA', 'Anulada'),
        ('VENCIDA', 'Vencida'),
    ]
    
    # Identificação
    serie = models.ForeignKey(SerieDocumento, on_delete=models.PROTECT, related_name='documentos')
    numero = models.CharField(max_length=30, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='RASCUNHO')
    
    # Relacionamentos
    filial = models.ForeignKey('organizacao.Filial', on_delete=models.PROTECT, related_name='documentos')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, related_name='documentos', null=True, blank=True)
    
    # Datas
    data_emissao = models.DateTimeField(auto_now_add=True)
    data_vencimento = models.DateField(null=True, blank=True)
    
    # Valores
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_iva = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_pago = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Observações
    observacao = models.TextField(blank=True, null=True)
    
    # Documento de origem (para notas de crédito/debito)
    documento_origem = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_relacionados')
    
    class Meta:
        verbose_name = "Documento Fiscal"
        verbose_name_plural = "Documentos Fiscais"
        ordering = ['-data_emissao']
        indexes = [
            models.Index(fields=['filial', 'estado']),
            models.Index(fields=['cliente']),
            models.Index(fields=['numero']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} #{self.numero}"
    
    @property
    def saldo_pendente(self):
        return self.total - self.total_pago
    
    @property
    def esta_paga(self):
        return self.total_pago >= self.total
    
    def atualizar_estado(self):
        """Atualiza o estado do documento baseado nos pagamentos"""
        if self.estado == 'ANULADA':
            return
        
        if self.esta_paga:
            self.estado = 'PAGA'
        elif self.total_pago > 0:
            self.estado = 'PARCIALMENTE_PAGA'
        else:
            self.estado = 'EMITIDA'
        
        # Verificar vencimento
        if self.data_vencimento and self.data_vencimento < timezone.now().date() and not self.esta_paga:
            self.estado = 'VENCIDA'
        
        self.save(update_fields=['estado'])


class LinhaDocumento(BaseModel):
    """Linha de um documento fiscal (item/produto)"""
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='linhas')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='linhas_documento')
    
    # Dados do produto no momento da venda (cópia)
    descricao = models.CharField(max_length=255)
    codigo_barras = models.CharField(max_length=13, blank=True, null=True)
    
    # Quantidades e preços
    quantidade = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    desconto_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    taxa_iva = models.DecimalField(max_digits=5, decimal_places=2)  # Cópia da taxa de IVA
    
    # Valores calculados
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_iva = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Linha de Documento"
        verbose_name_plural = "Linhas de Documento"
    
    def __str__(self):
        return f"{self.documento.numero} - {self.descricao}"
    
    def save(self, *args, **kwargs):
        """Calcula os valores da linha antes de salvar"""
        # Subtotal = quantidade * preco_unitario * (1 - desconto%)
        desconto = self.desconto_pct / 100
        self.subtotal = self.quantidade * self.preco_unitario * (1 - desconto)
        
        # IVA = subtotal * (taxa_iva / 100)
        taxa = self.taxa_iva / 100
        self.valor_iva = self.subtotal * taxa
        
        # Total = subtotal + IVA
        self.total = self.subtotal + self.valor_iva
        
        super().save(*args, **kwargs)


class Pagamento(BaseModel):
    """Pagamento de um documento fiscal"""
    METODO_CHOICES = [
        ('DINHEIRO', 'Dinheiro'),
        ('MULTICAIXA', 'Multicaixa'),
        ('TRANSFERENCIA', 'Transferência Bancária'),
        ('CHEQUE', 'Cheque'),
        ('OUTRO', 'Outro'),
    ]
    
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='pagamentos')
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    metodo = models.CharField(max_length=20, choices=METODO_CHOICES)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    data_pagamento = models.DateTimeField(auto_now_add=True)
    
    # Para débito automático da conta do cliente
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='pagamentos_registados'
    )
    
    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"
    
    def __str__(self):
        return f"Pagamento de {self.valor} para {self.documento.numero}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Atualizar o total_pago do documento
        total_pago = self.documento.pagamentos.aggregate(Sum('valor'))['valor__sum'] or 0
        self.documento.total_pago = total_pago
        self.documento.atualizar_estado()