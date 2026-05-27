# apps/faturacao/services.py
from django.db import transaction
from django.utils import timezone
from .models import Documento, Stock, MovimentacaoStock, Compra


class DocumentoService:
    """Serviços para gestão de documentos fiscais"""
    
    @staticmethod
    @transaction.atomic
    def emitir_documento(documento_id, operador):
        """Emite um documento (atribui número e atualiza stock)"""
        documento = Documento.objects.select_for_update().get(id=documento_id)
        
        if documento.estado != 'RASCUNHO':
            raise ValueError(f"Documento não pode ser emitido. Estado atual: {documento.estado}")
        
        # Emite o documento
        documento.estado = 'EMITIDA'
        documento.data_emissao = timezone.now()
        documento.save()
        
        # Atualiza stock (apenas para facturas e saidas)
        if documento.tipo == 'FACTURA':
            DocumentoService._atualizar_stock(documento, operador)
        
        return documento
    
    @staticmethod
    def _atualizar_stock(documento , operador):
        """Atualiza o stock baseado nas linhas do documento"""
        for linha in documento.linhas.all():
            try:
                stock = Stock.objects.get(
                    produto=linha.produto,
                    filial=documento.filial
                )
                
                # Verifica se há stock suficiente
                if stock.quantidade < linha.quantidade:
                    raise ValueError(
                        f"Stock insuficiente para {linha.produto.nome}. "
                        f"Disponível: {stock.quantidade}, Necessário: {linha.quantidade}"
                    )
                
                # Atualiza stock
                stock.quantidade -= linha.quantidade
                stock.save()
                
                # Regista movimentação
                MovimentacaoStock.objects.create(
                    stock_filial=stock,
                    tipo='S',
                    quantidade=linha.quantidade,
                    origem_destino=f"Venda - Documento {documento.numero}",
                    operador=operador
                )
                
            except Stock.DoesNotExist:
                raise ValueError(f"Stock não configurado para {linha.produto.nome} na filial {documento.filial.nome}")
    
    @staticmethod
    @transaction.atomic
    def anular_documento(documento_id):
        """Anula um documento (restaura stock)"""
        documento = Documento.objects.select_for_update().get(id=documento_id)
        
        if documento.estado in ['ANULADA', 'PAGA']:
            raise ValueError(f"Documento não pode ser anulado. Estado atual: {documento.estado}")
        
        # Restaura stock (apenas para facturas)
        if documento.tipo == 'FACTURA' and documento.estado == 'EMITIDA':
            DocumentoService._restaurar_stock(documento)
        
        documento.estado = 'ANULADA'
        documento.save()
        
        return documento
    
    @staticmethod
    def _restaurar_stock(documento, operador):
        """Restaura o stock ao anular um documento"""
        for linha in documento.linhas.all():
            stock = Stock.objects.get(
                produto=linha.produto,
                filial=documento.filial
            )
            
            stock.quantidade += linha.quantidade
            stock.save()
            
            MovimentacaoStock.objects.create(
                stock_filial=stock,
                tipo='E',
                quantidade=linha.quantidade,
                origem_destino=f"Anulação de documento {documento.numero}",
                operador=operador
            )




class CompraService:

    @staticmethod
    @transaction.atomic
    def confirmar_compra(compra_id, user):
        compra = Compra.objects.select_for_update().get(id=compra_id)
        if compra.estado != 'RASCUNHO':
            raise ValueError(f"Compra não pode ser confirmada. Estado atual: {compra.estado}")

        for linha in compra.linhas.all():
            stock, created = Stock.objects.get_or_create(
                produto=linha.produto,
                filial=compra.filial,
                defaults={'quantidade': 0, 'stock_minimo': 5}
            )
            stock.quantidade += linha.quantidade
            stock.save()
            MovimentacaoStock.objects.create(
                stock_filial=stock,
                tipo='E',
                quantidade=linha.quantidade,
                origem_destino=f"Compra {compra.id} - Fornecedor {compra.fornecedor.nome}",
                operador=user
            )
        compra.estado = 'CONFIRMADA'
        compra.save()
        return compra